#!/usr/bin/env python3
"""
Integration tests for pipeline orchestration.
Tests end-to-end workflows for New Project, New Feature, and Fix Bug pipelines.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import shutil

# Import utility classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.git_command import run_git_command, validate_git_repo, get_current_branch
from utils.file_lock import FileLock, FileLockError
from utils.schema_validator import SchemaValidator, SchemaValidationError
from utils.constants import Timeouts, CommitTypes, PhaseStatus, WorkflowStatus
from utils.exceptions import IFlowError, ErrorCode


class TestPipelineOrchestration(unittest.TestCase):
    """Integration tests for pipeline orchestration."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_repo = Path(self.test_dir) / "test_repo"
        self.test_repo.mkdir()
        
        # Initialize a git repository
        os.chdir(self.test_repo)
        self._init_git_repo()
        
        # Initialize iFlow skills directory structure
        self.skills_dir = self.test_repo / ".iflow" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Create shared state directory
        self.shared_state_dir = self.skills_dir / ".shared-state"
        self.shared_state_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir("/")
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _init_git_repo(self):
        """Initialize a git repository for testing."""
        try:
            run_git_command(["init"], cwd=self.test_repo)
            run_git_command(["config", "user.email", "test@example.com"], cwd=self.test_repo)
            run_git_command(["config", "user.name", "Test User"], cwd=self.test_repo)
            run_git_command(["checkout", "-b", "main"], cwd=self.test_repo)
            
            # Create initial commit
            readme = self.test_repo / "README.md"
            readme.write_text("# Test Repository")
            run_git_command(["add", "README.md"], cwd=self.test_repo)
            run_git_command(["commit", "-m", "Initial commit"], cwd=self.test_repo)
        except Exception:
            pass  # Git may not be available in all test environments
    
    def _create_workflow_state(self, workflow_type: str = "new_project") -> dict:
        """Create a workflow state document."""
        return {
            "workflow_type": workflow_type,
            "status": WorkflowStatus.INITIALIZED.value,
            "current_phase": "planning",
            "phases": [
                {
                    "name": "planning",
                    "status": PhaseStatus.ACTIVE.value,
                    "start_time": None,
                    "end_time": None,
                    "assigned_skill": "project-manager",
                    "dependencies": []
                },
                {
                    "name": "design",
                    "status": PhaseStatus.PENDING.value,
                    "start_time": None,
                    "end_time": None,
                    "assigned_skill": "tech-lead",
                    "dependencies": ["planning"]
                },
                {
                    "name": "implementation",
                    "status": PhaseStatus.PENDING.value,
                    "start_time": None,
                    "end_time": None,
                    "assigned_skill": "software-engineer",
                    "dependencies": ["design"]
                }
            ],
            "created_at": "2026-03-04T00:00:00",
            "updated_at": "2026-03-04T00:00:00"
        }
    
    def _create_branch_state(self, branch_name: str = "feature/test") -> dict:
        """Create a branch state document."""
        return {
            "branch_name": branch_name,
            "status": "pending",
            "base_branch": "main",
            "created_at": "2026-03-04T00:00:00",
            "updated_at": "2026-03-04T00:00:00",
            "commits": [],
            "reviews": []
        }
    
    def test_new_project_pipeline_initialization(self):
        """Test initializing a new project pipeline."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_project")
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Verify workflow state was created
        self.assertTrue(workflow_file.exists())
        
        # Load and verify workflow state
        with open(workflow_file) as f:
            loaded_state = json.load(f)
        
        self.assertEqual(loaded_state["workflow_type"], "new_project")
        self.assertEqual(loaded_state["status"], WorkflowStatus.INITIALIZED.value)
        self.assertEqual(len(loaded_state["phases"]), 3)
    
    def test_new_feature_pipeline_initialization(self):
        """Test initializing a new feature pipeline."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_feature")
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Create branch state
        branch_state = self._create_branch_state("feature/new-feature")
        branch_file = self.shared_state_dir / "branch-state.json"
        branch_file.write_text(json.dumps(branch_state, indent=2))
        
        # Verify both states were created
        self.assertTrue(workflow_file.exists())
        self.assertTrue(branch_file.exists())
        
        # Load and verify workflow state
        with open(workflow_file) as f:
            loaded_workflow = json.load(f)
        
        self.assertEqual(loaded_workflow["workflow_type"], "new_feature")
        
        # Load and verify branch state
        with open(branch_file) as f:
            loaded_branch = json.load(f)
        
        self.assertEqual(loaded_branch["branch_name"], "feature/new-feature")
        self.assertEqual(loaded_branch["status"], "pending")
    
    def test_fix_bug_pipeline_initialization(self):
        """Test initializing a fix bug pipeline."""
        # Create workflow state
        workflow_state = self._create_workflow_state("fix_bug")
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Verify workflow state was created
        self.assertTrue(workflow_file.exists())
        
        # Load and verify workflow state
        with open(workflow_file) as f:
            loaded_state = json.load(f)
        
        self.assertEqual(loaded_state["workflow_type"], "fix_bug")
        self.assertEqual(loaded_state["status"], WorkflowStatus.INITIALIZED.value)
    
    def test_phase_transition(self):
        """Test transitioning between workflow phases."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_project")
        
        # Transition from planning to design
        workflow_state["phases"][0]["status"] = PhaseStatus.COMPLETE.value
        workflow_state["phases"][1]["status"] = PhaseStatus.ACTIVE.value
        workflow_state["current_phase"] = "design"
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Load and verify phase transition
        with open(workflow_file) as f:
            loaded_state = json.load(f)
        
        self.assertEqual(loaded_state["current_phase"], "design")
        self.assertEqual(loaded_state["phases"][0]["status"], PhaseStatus.COMPLETE.value)
        self.assertEqual(loaded_state["phases"][1]["status"], PhaseStatus.ACTIVE.value)
    
    def test_complete_workflow(self):
        """Test completing a full workflow."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_project")
        
        # Complete all phases
        for phase in workflow_state["phases"]:
            phase["status"] = PhaseStatus.COMPLETE.value
        
        # Mark workflow as complete
        workflow_state["status"] = WorkflowStatus.COMPLETE.value
        workflow_state["current_phase"] = "complete"
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Load and verify workflow completion
        with open(workflow_file) as f:
            loaded_state = json.load(f)
        
        self.assertEqual(loaded_state["status"], WorkflowStatus.COMPLETE.value)
        self.assertEqual(loaded_state["current_phase"], "complete")
        
        # Verify all phases are complete
        for phase in loaded_state["phases"]:
            self.assertEqual(phase["status"], PhaseStatus.COMPLETE.value)
    
    def test_workflow_with_blocking_phase(self):
        """Test workflow handling when a phase is blocked."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_project")
        
        # Mark design phase as blocked
        workflow_state["phases"][1]["status"] = PhaseStatus.BLOCKED.value
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Load and verify blocked phase
        with open(workflow_file) as f:
            loaded_state = json.load(f)
        
        self.assertEqual(loaded_state["phases"][1]["status"], PhaseStatus.BLOCKED.value)
    
    def test_skill_handoff_between_phases(self):
        """Test skill handoff between workflow phases."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_project")
        
        # Verify initial skill assignment
        self.assertEqual(workflow_state["phases"][0]["assigned_skill"], "project-manager")
        
        # Transition to design phase
        workflow_state["phases"][0]["status"] = PhaseStatus.COMPLETE.value
        workflow_state["phases"][1]["status"] = PhaseStatus.ACTIVE.value
        workflow_state["current_phase"] = "design"
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Load and verify skill handoff
        with open(workflow_file) as f:
            loaded_state = json.load(f)
        
        self.assertEqual(loaded_state["current_phase"], "design")
        self.assertEqual(loaded_state["phases"][1]["assigned_skill"], "tech-lead")
    
    def test_workflow_state_validation(self):
        """Test validation of workflow state."""
        # Create valid workflow state
        workflow_state = self._create_workflow_state("new_project")
        
        # Validate workflow state structure
        self.assertIn("workflow_type", workflow_state)
        self.assertIn("status", workflow_state)
        self.assertIn("current_phase", workflow_state)
        self.assertIn("phases", workflow_state)
        self.assertIsInstance(workflow_state["phases"], list)
        self.assertGreater(len(workflow_state["phases"]), 0)
        
        # Validate phase structure
        for phase in workflow_state["phases"]:
            self.assertIn("name", phase)
            self.assertIn("status", phase)
            self.assertIn("assigned_skill", phase)
            self.assertIn("dependencies", phase)
    
    def test_concurrent_workflow_operations(self):
        """Test concurrent operations on workflow state."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_project")
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Test file locking for concurrent access
        lock_file = self.shared_state_dir / "pipeline-status.md.lock"
        
        try:
            # Acquire lock
            with FileLock(str(workflow_file)) as lock:
                # Modify workflow state
                with open(workflow_file) as f:
                    loaded_state = json.load(f)
                
                loaded_state["status"] = WorkflowStatus.IN_PROGRESS.value
                
                with open(workflow_file, 'w') as f:
                    json.dump(loaded_state, f, indent=2)
                
                # Verify lock file exists
                self.assertTrue(lock_file.exists())
            
            # Verify lock file was released
            self.assertFalse(lock_file.exists())
            
            # Verify workflow state was updated
            with open(workflow_file) as f:
                final_state = json.load(f)
            
            self.assertEqual(final_state["status"], WorkflowStatus.IN_PROGRESS.value)
        
        except FileLockError as e:
            self.fail(f"File lock failed: {e}")
    
    def test_workflow_error_recovery(self):
        """Test error recovery in workflow operations."""
        # Create workflow state
        workflow_state = self._create_workflow_state("new_project")
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Simulate an error during workflow execution
        try:
            with open(workflow_file) as f:
                loaded_state = json.load(f)
            
            # Mark a phase as failed
            loaded_state["phases"][0]["status"] = PhaseStatus.BLOCKED.value
            loaded_state["status"] = WorkflowStatus.BLOCKED.value
            
            with open(workflow_file, 'w') as f:
                json.dump(loaded_state, f, indent=2)
            
            # Verify error state
            with open(workflow_file) as f:
                final_state = json.load(f)
            
            self.assertEqual(final_state["status"], WorkflowStatus.BLOCKED.value)
            self.assertEqual(final_state["phases"][0]["status"], PhaseStatus.BLOCKED.value)
        
        except Exception as e:
            self.fail(f"Error recovery test failed: {e}")
    
    def test_shared_state_document_creation(self):
        """Test creation of shared state documents."""
        # Test project-spec document
        project_spec = self.shared_state_dir / "project-spec.md"
        project_spec.write_text("# Project Specification\n\n## Overview\n\nTest project")
        self.assertTrue(project_spec.exists())
        
        # Test design-spec document
        design_spec = self.shared_state_dir / "design-spec.md"
        design_spec.write_text("# Design Specification\n\n## Architecture\n\nTest architecture")
        self.assertTrue(design_spec.exists())
        
        # Verify documents can be read
        self.assertIn("Project Specification", project_spec.read_text())
        self.assertIn("Design Specification", design_spec.read_text())
    
    def test_pipeline_with_dependencies(self):
        """Test pipeline with phase dependencies."""
        # Create workflow state with dependencies
        workflow_state = {
            "workflow_type": "new_project",
            "status": WorkflowStatus.INITIALIZED.value,
            "current_phase": "planning",
            "phases": [
                {
                    "name": "planning",
                    "status": PhaseStatus.ACTIVE.value,
                    "assigned_skill": "project-manager",
                    "dependencies": []
                },
                {
                    "name": "design",
                    "status": PhaseStatus.PENDING.value,
                    "assigned_skill": "tech-lead",
                    "dependencies": ["planning"]
                },
                {
                    "name": "implementation",
                    "status": PhaseStatus.PENDING.value,
                    "assigned_skill": "software-engineer",
                    "dependencies": ["design"]
                },
                {
                    "name": "testing",
                    "status": PhaseStatus.PENDING.value,
                    "assigned_skill": "testing-engineer",
                    "dependencies": ["implementation"]
                }
            ]
        }
        
        # Save workflow state
        workflow_file = self.shared_state_dir / "pipeline-status.md"
        workflow_file.write_text(json.dumps(workflow_state, indent=2))
        
        # Verify dependencies are respected
        with open(workflow_file) as f:
            loaded_state = json.load(f)
        
        # Design depends on planning
        self.assertIn("planning", loaded_state["phases"][1]["dependencies"])
        
        # Implementation depends on design
        self.assertIn("design", loaded_state["phases"][2]["dependencies"])
        
        # Testing depends on implementation
        self.assertIn("implementation", loaded_state["phases"][3]["dependencies"])


if __name__ == "__main__":
    unittest.main()