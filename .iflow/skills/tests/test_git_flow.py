#!/usr/bin/env python3
"""
Test suite for git-flow.py
Tests workflow orchestration, branch management, and phase transitions.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import git-flow classes
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from git_flow.git_flow import (
    GitFlow,
    BranchStatus,
    PhaseStatus,
    WorkflowStatus,
    ReviewEvent,
    BranchState,
    Phase,
    WorkflowState,
    DependencyGraph
)
# Import exceptions and constants from utils


class TestBranchStatus(unittest.TestCase):
    """Test BranchStatus enum."""

    def test_branch_status_values(self):
        """Test that branch status enum has correct values."""
        self.assertEqual(BranchStatus.PENDING.value, "pending")
        self.assertEqual(BranchStatus.REVIEWING.value, "reviewing")
        self.assertEqual(BranchStatus.APPROVED.value, "approved")
        self.assertEqual(BranchStatus.MERGED.value, "merged")
        self.assertEqual(BranchStatus.UNAPPROVED.value, "unapproved")
        self.assertEqual(BranchStatus.REVERTED.value, "reverted")
        self.assertEqual(BranchStatus.NEEDS_CHANGES.value, "needs_changes")
        self.assertEqual(BranchStatus.REJECTED.value, "rejected")


class TestPhaseStatus(unittest.TestCase):
    """Test PhaseStatus enum."""

    def test_phase_status_values(self):
        """Test that phase status enum has correct values."""
        self.assertEqual(PhaseStatus.PENDING.value, "pending")
        self.assertEqual(PhaseStatus.ACTIVE.value, "active")
        self.assertEqual(PhaseStatus.COMPLETE.value, "complete")
        self.assertEqual(PhaseStatus.BLOCKED.value, "blocked")


class TestWorkflowStatus(unittest.TestCase):
    """Test WorkflowStatus enum."""

    def test_workflow_status_values(self):
        """Test that workflow status enum has correct values."""
        self.assertEqual(WorkflowStatus.INITIALIZED.value, "initialized")
        self.assertEqual(WorkflowStatus.IN_PROGRESS.value, "in_progress")
        self.assertEqual(WorkflowStatus.COMPLETE.value, "complete")
        self.assertEqual(WorkflowStatus.PAUSED.value, "paused")


class TestReviewEvent(unittest.TestCase):
    """Test ReviewEvent class."""

    def test_review_event_creation(self):
        """Test creating a review event."""
        event = ReviewEvent(
            action="approve",
            actor="user1",
            comment="Looks good",
            reason=None,
            merge_commit="abc123"
        )

        self.assertEqual(event.action, "approve")
        self.assertEqual(event.actor, "user1")
        self.assertEqual(event.comment, "Looks good")
        self.assertIsNone(event.reason)
        self.assertEqual(event.merge_commit, "abc123")
        self.assertIsNotNone(event.timestamp)

    def test_review_event_to_dict(self):
        """Test converting review event to dictionary."""
        event = ReviewEvent("reject", "user2", reason="Needs work")
        event_dict = event.to_dict()

        self.assertIn("action", event_dict)
        self.assertIn("actor", event_dict)
        self.assertIn("timestamp", event_dict)
        self.assertEqual(event_dict["action"], "reject")
        self.assertEqual(event_dict["actor"], "user2")
        self.assertEqual(event_dict["reason"], "Needs work")


class TestBranchState(unittest.TestCase):
    """Test BranchState class."""

    def test_branch_state_creation(self):
        """Test creating a branch state."""
        branch = BranchState("feature/test", "Software Engineer", 1)

        self.assertEqual(branch.name, "feature/test")
        self.assertEqual(branch.role, "Software Engineer")
        self.assertEqual(branch.phase, 1)
        self.assertEqual(branch.status, BranchStatus.PENDING)
        self.assertIsNotNone(branch.created_at)
        self.assertEqual(branch.commits, [])
        self.assertIsNone(branch.merge_commit)
        self.assertEqual(branch.dependencies, [])
        self.assertEqual(branch.dependents, [])

    def test_branch_state_to_dict(self):
        """Test converting branch state to dictionary."""
        branch = BranchState("feature/test", "Software Engineer", 1)
        branch.status = BranchStatus.APPROVED
        branch.approved_by = "user1"

        branch_dict = branch.to_dict()

        self.assertEqual(branch_dict["name"], "feature/test")
        self.assertEqual(branch_dict["role"], "Software Engineer")
        self.assertEqual(branch_dict["status"], "approved")
        self.assertEqual(branch_dict["approved_by"], "user1")

    def test_branch_state_from_dict(self):
        """Test creating branch state from dictionary."""
        data = {
            "name": "feature/test",
            "role": "Software Engineer",
            "status": "approved",
            "phase": 1,
            "created_at": "2024-01-01T00:00:00",
            "commits": [{"hash": "abc123", "message": "test"}],
            "merge_commit": "def456",
            "approved_by": "user1",
            "approved_at": "2024-01-01T01:00:00",
            "dependencies": ["base"],
            "dependents": [],
            "review_history": []
        }

        branch = BranchState.from_dict(data)

        self.assertEqual(branch.name, "feature/test")
        self.assertEqual(branch.role, "Software Engineer")
        self.assertEqual(branch.status, BranchStatus.APPROVED)
        self.assertEqual(branch.commits, [{"hash": "abc123", "message": "test"}])
        self.assertEqual(branch.merge_commit, "def456")
        self.assertEqual(branch.approved_by, "user1")


class TestPhase(unittest.TestCase):
    """Test Phase class."""

    def test_phase_creation(self):
        """Test creating a phase."""
        phase = Phase("Implementation", "Software Engineer", 3, True)

        self.assertEqual(phase.name, "Implementation")
        self.assertEqual(phase.role, "Software Engineer")
        self.assertEqual(phase.order, 3)
        self.assertTrue(phase.required)
        self.assertEqual(phase.status, PhaseStatus.PENDING)
        self.assertIsNone(phase.branch)
        self.assertEqual(phase.dependencies, [])

    def test_phase_to_dict(self):
        """Test converting phase to dictionary."""
        phase = Phase("Implementation", "Software Engineer", 3, True)
        phase.status = PhaseStatus.COMPLETE
        phase.branch = "feature/test"

        phase_dict = phase.to_dict()

        self.assertEqual(phase_dict["name"], "Implementation")
        self.assertEqual(phase_dict["status"], "complete")
        self.assertEqual(phase_dict["branch"], "feature/test")

    def test_phase_from_dict(self):
        """Test creating phase from dictionary."""
        data = {
            "name": "Implementation",
            "role": "Software Engineer",
            "order": 3,
            "required": True,
            "status": "complete",
            "branch": "feature/test",
            "dependencies": [1, 2],
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T02:00:00"
        }

        phase = Phase.from_dict(data)

        self.assertEqual(phase.name, "Implementation")
        self.assertEqual(phase.status, PhaseStatus.COMPLETE)
        self.assertEqual(phase.branch, "feature/test")
        self.assertEqual(phase.dependencies, [1, 2])


class TestWorkflowState(unittest.TestCase):
    """Test WorkflowState class."""

    def test_workflow_state_creation(self):
        """Test creating a workflow state."""
        workflow = WorkflowState("Test Feature")

        self.assertEqual(workflow.feature, "Test Feature")
        self.assertEqual(workflow.status, WorkflowStatus.INITIALIZED)
        self.assertEqual(workflow.current_phase, 0)
        self.assertEqual(workflow.phases, [])
        self.assertEqual(workflow.branches, {})
        self.assertIsNotNone(workflow.created_at)
        self.assertIsNotNone(workflow.updated_at)

    def test_workflow_state_to_dict(self):
        """Test converting workflow state to dictionary."""
        workflow = WorkflowState("Test Feature")
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.current_phase = 1

        workflow_dict = workflow.to_dict()

        self.assertEqual(workflow_dict["feature"], "Test Feature")
        self.assertEqual(workflow_dict["status"], "in_progress")
        self.assertEqual(workflow_dict["current_phase"], 1)

    def test_workflow_state_from_dict(self):
        """Test creating workflow state from dictionary."""
        data = {
            "feature": "Test Feature",
            "status": "in_progress",
            "current_phase": 1,
            "phases": [],
            "branches": {},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00"
        }

        workflow = WorkflowState.from_dict(data)

        self.assertEqual(workflow.feature, "Test Feature")
        self.assertEqual(workflow.status, WorkflowStatus.IN_PROGRESS)
        self.assertEqual(workflow.current_phase, 1)


class TestDependencyGraph(unittest.TestCase):
    """Test DependencyGraph class."""

    def test_dependency_graph_creation(self):
        """Test creating a dependency graph."""
        graph = DependencyGraph()

        self.assertEqual(graph.graph, {})
        self.assertEqual(graph.reverse_graph, {})

    def test_add_dependency(self):
        """Test adding dependencies to graph."""
        graph = DependencyGraph()
        graph.add_dependency("feature", ["base", "common"])

        self.assertIn("feature", graph.graph)
        self.assertEqual(graph.graph["feature"], ["base", "common"])
        self.assertIn("base", graph.reverse_graph)
        self.assertIn("feature", graph.reverse_graph["base"])

    def test_get_dependents(self):
        """Test getting dependents of a branch."""
        graph = DependencyGraph()
        graph.add_dependency("feature1", ["base"])
        graph.add_dependency("feature2", ["base"])

        dependents = graph.get_dependents("base")

        self.assertEqual(sorted(dependents), ["feature1", "feature2"])

    def test_get_all_dependents(self):
        """Test getting all transitive dependents."""
        graph = DependencyGraph()
        graph.add_dependency("feature2", ["feature1"])
        graph.add_dependency("feature1", ["base"])

        all_dependents = graph.get_all_dependents("base")

        self.assertIn("feature1", all_dependents)
        self.assertIn("feature2", all_dependents)


class TestGitFlow(unittest.TestCase):
    """Test GitFlow class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)
        self.skill_dir = self.repo_root / '.iflow' / 'skills' / 'git-flow'
        self.skill_dir.mkdir(parents=True)

        # Create config file
        self.config_file = self.skill_dir / 'config.json'
        self.config_file.write_text(json.dumps({
            "workflow": {
                "auto_detect_role": True,
                "auto_create_branch": True,
                "auto_phase_transition": True
            },
            "merge": {
                "strategy": "rebase-merge",
                "delete_branch_after_merge": True
            }
        }))

        # Create phases file
        self.phases_file = self.skill_dir / 'phases.json'
        self.phases_file.write_text(json.dumps({
            "phases": [
                {"name": "Requirements", "role": "Client", "order": 1, "required": True, "status": "pending"},
                {"name": "Design", "role": "UI/UX Designer", "order": 2, "required": True, "status": "pending"},
                {"name": "Implementation", "role": "Software Engineer", "order": 3, "required": True, "status": "pending"}
            ]
        }))

        # Create schema directory
        self.schema_dir = self.repo_root / '.iflow' / 'schemas'
        self.schema_dir.mkdir(parents=True)

        # Create schema files
        self.workflow_schema = self.schema_dir / 'workflow-state.json'
        self.workflow_schema.write_text(json.dumps({
            "version": "1.0.0",
            "required": ["feature", "status", "current_phase"],
            "fields": {
                "feature": {"type": "string"},
                "status": {"type": "string"},
                "current_phase": {"type": "integer"}
            }
        }))

        self.branch_schema = self.schema_dir / 'branch-state.json'
        self.branch_schema.write_text(json.dumps({
            "version": "1.0.0",
            "required": ["name", "role", "status"],
            "fields": {
                "name": {"type": "string"},
                "role": {"type": "string"},
                "status": {"type": "string"}
            }
        }))

        # Initialize git repo
        import subprocess
        subprocess.run(['git', 'init'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', 'main'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Initial commit'], cwd=self.repo_root, capture_output=True)

        self.git_flow = GitFlow(self.repo_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_git_flow_initialization(self):
        """Test GitFlow initialization."""
        self.assertIsNotNone(self.git_flow)
        self.assertEqual(self.git_flow.repo_root, self.repo_root)
        self.assertIsNotNone(self.git_flow.config)
        self.assertEqual(len(self.git_flow.phases), 3)

    def test_start_workflow(self):
        """Test starting a new workflow."""
        code, output = self.git_flow.start_workflow("Test-Feature")

        self.assertEqual(code, 0)
        self.assertIn("✓ Workflow initialized", output)
        self.assertIn("Test-Feature", output)
        self.assertIsNotNone(self.git_flow.workflow_state)
        self.assertEqual(self.git_flow.workflow_state.feature, "Test-Feature")
        self.assertEqual(self.git_flow.workflow_state.status, WorkflowStatus.IN_PROGRESS)

    def test_start_workflow_already_exists(self):
        """Test starting workflow when one already exists."""
        self.git_flow.start_workflow("Feature-1")
        code, output = self.git_flow.start_workflow("Feature-2")

        self.assertEqual(code, 1)
        self.assertIn("Workflow already exists", output)

    def test_to_slug(self):
        """Test slug generation."""
        self.assertEqual(self.git_flow.to_slug("Feature Name"), "feature-name")
        self.assertEqual(self.git_flow.to_slug("Test 123"), "test-123")
        self.assertEqual(self.git_flow.to_slug("UPPER CASE"), "upper-case")

    def test_generate_branch_name(self):
        """Test branch name generation."""
        branch = self.git_flow.generate_branch_name("Software Engineer", "Test Feature")

        self.assertIn("software-engineer", branch)
        self.assertIn("test-feature", branch)
        self.assertTrue(any(c.isdigit() for c in branch))

    @patch('git_flow.git_flow.run_git_command')
    def test_create_branch(self, mock_run_git):
        """Test creating a branch."""
        mock_run_git.return_value = (0, "Created branch", "")

        code, output = self.git_flow.create_branch("feature/test")

        self.assertEqual(code, 0)
        self.assertIn("Created branch", output)
        mock_run_git.assert_called_once()

    @patch('git_flow.git_flow.run_git_command')
    def test_create_branch_invalid_name(self, mock_run_git):
        """Test creating a branch with invalid name."""
        # Mock validation to fail
        with patch('git_flow.git_flow.validate_branch_name', return_value=(False, "Invalid name")):
            code, output = self.git_flow.create_branch("invalid..name")

            self.assertEqual(code, 1)
            self.assertIn("Invalid branch name", output)

    def test_is_protected_branch(self):
        """Test checking if branch is protected."""
        self.assertTrue(self.git_flow.is_protected_branch("main"))
        self.assertTrue(self.git_flow.is_protected_branch("master"))
        self.assertFalse(self.git_flow.is_protected_branch("feature/test"))

    @patch('git_flow.git_flow.get_current_branch')
    def test_detect_role_from_branch(self, mock_get_branch):
        """Test role detection from branch name."""
        mock_get_branch.return_value = "software-engineer/test-feature"

        role = self.git_flow.detect_role()

        self.assertEqual(role, "Software Engineer")

    @patch('git_flow.git_flow.get_current_branch')
    def test_detect_role_from_phase(self, mock_get_branch):
        """Test role detection from current phase."""
        mock_get_branch.return_value = "test"
        self.git_flow.workflow_state = WorkflowState("Test")
        self.git_flow.workflow_state.phases = [
            Phase("Requirements", "Client", 1, True)
        ]
        self.git_flow.workflow_state.current_phase = 1

        role = self.git_flow.detect_role()

        self.assertEqual(role, "Client")

    def test_save_and_load_workflow_state(self):
        """Test saving and loading workflow state."""
        self.git_flow.start_workflow("Test-Feature")
        original_phase_count = len(self.git_flow.workflow_state.phases)

        # Save
        self.git_flow.save_workflow_state()

        # Create new instance and load
        new_git_flow = GitFlow(self.repo_root)
        self.assertEqual(new_git_flow.workflow_state.feature, "Test-Feature")
        self.assertEqual(len(new_git_flow.workflow_state.phases), original_phase_count)

    def test_save_and_load_branch_states(self):
        """Test saving and loading branch states."""
        self.git_flow.start_workflow("Test-Feature")
        branch = BranchState("feature/test", "Software Engineer", 1)
        self.git_flow.workflow_state.branches["feature/test"] = branch

        # Save
        self.git_flow.save_branch_states()

        # Create new instance and load
        new_git_flow = GitFlow(self.repo_root)
        self.assertIn("feature/test", new_git_flow.workflow_state.branches)
        self.assertEqual(new_git_flow.workflow_state.branches["feature/test"].role, "Software Engineer")


class TestGitFlowAdvanced(unittest.TestCase):
    """Test advanced GitFlow functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)
        self._setup_git_repo()
        self.git_flow = GitFlow(self.repo_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _setup_git_repo(self):
        """Set up a git repository for testing."""
        import subprocess
        self.skill_dir = self.repo_root / '.iflow' / 'skills' / 'git-flow'
        self.skill_dir.mkdir(parents=True)

        # Create minimal config
        (self.skill_dir / 'config.json').write_text(json.dumps({
            "workflow": {"auto_detect_role": True, "auto_create_branch": True, "auto_phase_transition": True},
            "merge": {"strategy": "rebase-merge", "delete_branch_after_merge": True}
        }))

        # Create phases
        (self.skill_dir / 'phases.json').write_text(json.dumps({
            "phases": [
                {"name": "Requirements", "role": "Client", "order": 1, "required": True, "status": "pending"},
                {"name": "Implementation", "role": "Software Engineer", "order": 2, "required": True, "status": "pending"}
            ]
        }))

        # Create schemas
        self.schema_dir = self.repo_root / '.iflow' / 'schemas'
        self.schema_dir.mkdir(parents=True)
        (self.schema_dir / 'workflow-state.json').write_text(json.dumps({
            "version": "1.0.0", "required": ["feature", "status"],
            "fields": {"feature": {"type": "string"}, "status": {"type": "string"}}
        }))
        (self.schema_dir / 'branch-state.json').write_text(json.dumps({
            "version": "1.0.0", "required": ["name", "role", "status"],
            "fields": {"name": {"type": "string"}, "role": {"type": "string"}, "status": {"type": "string"}}
        }))

        # Initialize git
        subprocess.run(['git', 'init'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', 'main'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Initial'], cwd=self.repo_root, capture_output=True)

    @patch('git_flow.git_flow.run_git_command')
    def test_merge_branch_dependencies_check(self, mock_run_git):
        """Test that merge checks for dependencies."""
        self.git_flow.start_workflow("Test")
        self.git_flow.workflow_state.current_phase = 1

        # Create branch with dependency
        branch = BranchState("feature/test", "Software Engineer", 2)
        branch.dependencies = ["base"]
        self.git_flow.workflow_state.branches["feature/test"] = branch

        # Base branch exists but not merged
        base_branch = BranchState("base", "Tech Lead", 1)
        base_branch.status = BranchStatus.PENDING
        self.git_flow.workflow_state.branches["base"] = base_branch

        # Mock git commands
        mock_run_git.return_value = (0, "", "")

        code, output = self.git_flow.merge_branch("feature/test")

        # Should fail because dependency not merged
        self.assertEqual(code, 1)
        self.assertIn("not merged yet", output)

    def test_config_merging(self):
        """Test that user config merges with defaults."""
        # Add custom config
        custom_config = {
            "workflow": {
                "require_all_phases": True
            }
        }
        self.config_file = self.skill_dir / 'config.json'
        with open(self.config_file, 'w') as f:
            json.dump(custom_config, f)

        # Reload git-flow
        git_flow = GitFlow(self.repo_root)

        # Should have custom config merged with defaults
        self.assertTrue(git_flow.config["workflow"]["require_all_phases"])
        self.assertTrue(git_flow.config["workflow"]["auto_detect_role"])  # Default


if __name__ == '__main__':
    unittest.main()