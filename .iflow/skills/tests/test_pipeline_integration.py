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
from unittest.mock import Mock
import shutil

# Import utility classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.git_command import run_git_command
from utils.file_lock import FileLock, FileLockError
from utils.constants import PhaseStatus, WorkflowStatus

# Import PipelineOrchestrator and related classes
from utils.pipeline_orchestrator import (
    PipelineState,
    Stage,
    PipelineStatus,
    StageStatus,
    create_pipeline_orchestrator
)
from utils.skill_invoker import SkillInvoker, SkillInvocationResult, create_skill_invoker


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
        except Exception as e:
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
        try:
            # Acquire lock and verify context manager works
            with FileLock(str(workflow_file)) as lock:
                # Simulate some work
                workflow_state["status"] = WorkflowStatus.IN_PROGRESS.value
                pass  # FileLock context manager works
            
            # If we get here without exception, FileLock worked correctly
            self.assertTrue(True)
        
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


class TestPipelineOrchestrator(unittest.TestCase):
    """Comprehensive tests for PipelineOrchestrator functionality."""
    
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
        
        # Create a mock skill invoker
        self.skill_invoker = Mock(spec=SkillInvoker)
        self.skill_invoker.invoke_skill = Mock(return_value=SkillInvocationResult(
            success=True,
            output="Skill executed successfully",
            exit_code=0
        ))
        
        # Simple pipeline configuration
        self.stages_config = [
            {
                "name": "Requirements Gathering",
                "role": "client",
                "order": 1,
                "required": True,
                "skill": "client",
                "prompt_template": "Gather requirements for {feature_name}"
            },
            {
                "name": "Design",
                "role": "tech-lead",
                "order": 2,
                "required": True,
                "dependencies": [1],
                "skill": "tech-lead",
                "prompt_template": "Design architecture for {feature_name}"
            },
            {
                "name": "Implementation",
                "role": "software-engineer",
                "order": 3,
                "required": True,
                "dependencies": [2],
                "skill": "software-engineer",
                "prompt_template": "Implement {feature_name}"
            }
        ]
    
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
        except Exception as e:
            pass  # Git may not be available in all test environments
    
    def test_pipeline_orchestrator_initialization(self):
        """Test PipelineOrchestrator initialization."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Verify orchestrator was created
        self.assertIsNotNone(orchestrator)
        self.assertEqual(orchestrator.pipeline_name, "test-pipeline")
        self.assertEqual(orchestrator.feature_name, "test-feature")
        self.assertEqual(len(orchestrator.state.stages), 3)
        
        # Verify stage initialization
        self.assertEqual(orchestrator.state.stages[0].name, "Requirements Gathering")
        self.assertEqual(orchestrator.state.stages[1].name, "Design")
        self.assertEqual(orchestrator.state.stages[2].name, "Implementation")
        
        # Verify stage dependencies
        self.assertEqual(orchestrator.state.stages[1].dependencies, [1])
        self.assertEqual(orchestrator.state.stages[2].dependencies, [2])
        
        # Verify initial status
        self.assertEqual(orchestrator.state.status, PipelineStatus.PENDING)
        self.assertEqual(orchestrator.state.stages[0].status, StageStatus.PENDING)
    
    def test_pipeline_start_success(self):
        """Test successful pipeline execution."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline completed successfully
        self.assertEqual(code, 0)
        self.assertEqual(orchestrator.state.status, PipelineStatus.COMPLETED)
        
        # Verify all stages completed
        for stage in orchestrator.state.stages:
            self.assertEqual(stage.status, StageStatus.COMPLETED)
        
        # Verify skill invocations
        self.assertEqual(self.skill_invoker.invoke_skill.call_count, 3)
    
    def test_pipeline_with_failed_stage(self):
        """Test pipeline execution with a failed stage."""
        # Make the second stage fail on all attempts
        call_count = [0]
        def mock_invoke(skill_name, prompt, context, **kwargs):
            call_count[0] += 1
            # Fail tech-lead role (second stage) on all attempts
            if context.get("role") == "tech-lead":
                return SkillInvocationResult(
                    success=False,
                    output="",
                    error="Stage execution failed",
                    exit_code=1
                )
            return SkillInvocationResult(
                success=True,
                output="Skill executed successfully",
                exit_code=0
            )
        
        self.skill_invoker.invoke_skill = Mock(side_effect=mock_invoke)
        
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline failed
        self.assertEqual(code, 1)
        self.assertEqual(orchestrator.state.status, PipelineStatus.FAILED)
        
        # Verify first stage completed, second stage failed
        self.assertEqual(orchestrator.state.stages[0].status, StageStatus.COMPLETED)
        self.assertEqual(orchestrator.state.stages[1].status, StageStatus.FAILED)
        self.assertEqual(orchestrator.state.stages[2].status, StageStatus.PENDING)
    
    def test_pipeline_with_retry(self):
        """Test pipeline execution with retry logic."""
        # Make the second stage fail once then succeed
        call_count = [0]
        def mock_invoke(skill_name, prompt, context, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                return SkillInvocationResult(
                    success=False,
                    output="",
                    error="Temporary failure",
                    exit_code=1
                )
            return SkillInvocationResult(
                success=True,
                output="Skill executed successfully",
                exit_code=0
            )
        
        self.skill_invoker.invoke_skill = Mock(side_effect=mock_invoke)
        
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline completed after retry
        self.assertEqual(code, 0)
        self.assertEqual(orchestrator.state.status, PipelineStatus.COMPLETED)
        
        # Verify second stage was retried
        self.assertEqual(orchestrator.state.stages[1].retries, 1)
    
    def test_pipeline_pause_and_resume(self):
        """Test pipeline pause and resume functionality."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Test that we can't pause a PENDING pipeline
        code, output = orchestrator.pause()
        self.assertEqual(code, 1)
        self.assertIn("Cannot pause", output)
        
        # Test that we can't resume a PENDING pipeline
        code, output = orchestrator.resume()
        self.assertEqual(code, 1)
        self.assertIn("Cannot resume", output)
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Test that we can't pause a COMPLETED pipeline
        code, output = orchestrator.pause()
        self.assertEqual(code, 1)
        
        # Test that we can't resume a COMPLETED pipeline
        code, output = orchestrator.resume()
        self.assertEqual(code, 1)
    
    def test_pipeline_cancel(self):
        """Test pipeline cancellation."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Cancel pipeline in PENDING state
        code, output = orchestrator.cancel()
        self.assertEqual(code, 0)
        self.assertEqual(orchestrator.state.status, PipelineStatus.CANCELLED)
        
        # Test that cancelling already cancelled pipeline fails
        code, output = orchestrator.cancel()
        self.assertEqual(code, 1)
    
    def test_pipeline_with_parallel_stages(self):
        """Test pipeline execution with parallel stages."""
        # Create pipeline config with parallel stages
        parallel_config = [
            {
                "name": "Frontend Implementation",
                "role": "software-engineer",
                "order": 1,
                "required": True,
                "parallel_group": "implementation",
                "skill": "software-engineer",
                "prompt_template": "Implement frontend for {feature_name}"
            },
            {
                "name": "Backend Implementation",
                "role": "software-engineer",
                "order": 2,
                "required": True,
                "parallel_group": "implementation",
                "skill": "software-engineer",
                "prompt_template": "Implement backend for {feature_name}"
            },
            {
                "name": "Testing",
                "role": "testing-engineer",
                "order": 3,
                "required": True,
                "dependencies": [1, 2],
                "skill": "testing-engineer",
                "prompt_template": "Test {feature_name}"
            }
        ]
        
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=parallel_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline completed
        self.assertEqual(code, 0)
        self.assertEqual(orchestrator.state.status, PipelineStatus.COMPLETED)
        
        # Verify all stages completed
        for stage in orchestrator.state.stages:
            self.assertEqual(stage.status, StageStatus.COMPLETED)
    
    def test_pipeline_state_persistence(self):
        """Test pipeline state save and load."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline (it will complete)
        orchestrator.start()
        
        # Save state
        state_file = self.test_repo / "pipeline_state.json"
        orchestrator.save_state(state_file)
        
        # Verify state file was created
        self.assertTrue(state_file.exists())
        
        # Create new orchestrator and load state
        new_orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        code, output = new_orchestrator.load_state(state_file)
        self.assertEqual(code, 0)
        
        # Verify state was loaded correctly
        self.assertEqual(new_orchestrator.state.status, PipelineStatus.COMPLETED)
        self.assertEqual(len(new_orchestrator.state.stages), 3)
    
    def test_pipeline_progress_tracking(self):
        """Test pipeline progress calculation."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Initial progress should be 0%
        self.assertEqual(orchestrator.state.get_progress(), 0.0)
        
        # Start pipeline
        orchestrator.start()
        
        # Final progress should be 100%
        self.assertEqual(orchestrator.state.get_progress(), 100.0)
    
    def test_pipeline_with_conditions(self):
        """Test pipeline with stage conditions."""
        # Create pipeline config with conditional stage
        conditional_config = [
            {
                "name": "Requirements",
                "role": "client",
                "order": 1,
                "required": False,
                "conditions": {"skip_if": "requirements_provided"},
                "skill": "client",
                "prompt_template": "Gather requirements for {feature_name}"
            },
            {
                "name": "Design",
                "role": "tech-lead",
                "order": 2,
                "required": True,
                "dependencies": [1],
                "skill": "tech-lead",
                "prompt_template": "Design architecture for {feature_name}"
            }
        ]
        
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=conditional_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline completed
        self.assertEqual(code, 0)
        self.assertEqual(orchestrator.state.status, PipelineStatus.COMPLETED)
    
    def test_pipeline_dry_run(self):
        """Test pipeline in dry-run mode."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=True
        )
        
        # Start pipeline in dry-run mode
        code, output = orchestrator.start()
        
        # Verify pipeline completed
        self.assertEqual(code, 0)
        self.assertEqual(orchestrator.state.status, PipelineStatus.COMPLETED)
        
        # Verify no actual skill invocations occurred
        self.skill_invoker.invoke_skill.assert_not_called()
    
    def test_pipeline_with_optional_stage(self):
        """Test pipeline with optional stages."""
        # Create pipeline config with optional stage
        optional_config = [
            {
                "name": "Requirements",
                "role": "client",
                "order": 1,
                "required": False,
                "skill": "client",
                "prompt_template": "Gather requirements for {feature_name}"
            },
            {
                "name": "Design",
                "role": "tech-lead",
                "order": 2,
                "required": True,
                "dependencies": [1],
                "skill": "tech-lead",
                "prompt_template": "Design architecture for {feature_name}"
            },
            {
                "name": "Implementation",
                "role": "software-engineer",
                "order": 3,
                "required": True,
                "dependencies": [2],
                "skill": "software-engineer",
                "prompt_template": "Implement {feature_name}"
            }
        ]
        
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=optional_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline completed
        self.assertEqual(code, 0)
        self.assertEqual(orchestrator.state.status, PipelineStatus.COMPLETED)
    
    def test_pipeline_next_ready_stage(self):
        """Test getting the next ready stage."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Initially, first stage should be ready
        next_stage = orchestrator.state.get_next_ready_stage()
        self.assertIsNotNone(next_stage)
        self.assertEqual(next_stage.order, 1)
        
        # After completing first stage, second stage should be ready
        orchestrator.state.stages[0].status = StageStatus.COMPLETED
        next_stage = orchestrator.state.get_next_ready_stage()
        self.assertIsNotNone(next_stage)
        self.assertEqual(next_stage.order, 2)
    
    def test_pipeline_state_serialization(self):
        """Test PipelineState serialization and deserialization."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Serialize state
        state_dict = orchestrator.state.to_dict()
        
        # Verify serialization
        self.assertEqual(state_dict["pipeline_name"], "test-pipeline")
        self.assertEqual(state_dict["feature_name"], "test-feature")
        self.assertEqual(len(state_dict["stages"]), 3)
        
        # Deserialize state
        new_state = PipelineState.from_dict(state_dict)
        
        # Verify deserialization
        self.assertEqual(new_state.pipeline_name, "test-pipeline")
        self.assertEqual(new_state.feature_name, "test-feature")
        self.assertEqual(len(new_state.stages), 3)
    
    def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        # Make skill invocation raise an exception
        def mock_invoke_error(skill_name, prompt, context, **kwargs):
            raise Exception("Unexpected error")
        
        self.skill_invoker.invoke_skill = Mock(side_effect=mock_invoke_error)
        
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline failed gracefully
        self.assertEqual(code, 1)
        self.assertEqual(orchestrator.state.status, PipelineStatus.FAILED)
        self.assertIn("Unexpected error", output)
    
    def test_pipeline_with_max_retries_exceeded(self):
        """Test pipeline when max retries are exceeded."""
        # Make stage fail repeatedly
        def mock_invoke_fail(skill_name, prompt, context, **kwargs):
            return SkillInvocationResult(
                success=False,
                output="",
                error="Persistent failure",
                exit_code=1
            )
        
        self.skill_invoker.invoke_skill = Mock(side_effect=mock_invoke_fail)
        
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify pipeline failed after max retries
        self.assertEqual(code, 1)
        self.assertEqual(orchestrator.state.status, PipelineStatus.FAILED)
        
        # Verify first stage tried max retries
        self.assertEqual(orchestrator.state.stages[0].retries, 3)
    
    def test_skill_invocation_with_context(self):
        """Test that skill invocations include proper context."""
        orchestrator = create_pipeline_orchestrator(
            pipeline_name="test-pipeline",
            feature_name="test-feature",
            stages_config=self.stages_config,
            repo_root=self.test_repo,
            skill_invoker=self.skill_invoker,
            dry_run=False
        )
        
        # Start pipeline
        code, output = orchestrator.start()
        
        # Verify skill was invoked with correct context
        calls = self.skill_invoker.invoke_skill.call_args_list
        
        # Check first invocation
        first_call = calls[0]
        self.assertEqual(first_call[1]["skill_name"], "client")
        self.assertIn("pipeline_name", first_call[1]["context"])
        self.assertIn("feature_name", first_call[1]["context"])
        self.assertEqual(first_call[1]["context"]["pipeline_name"], "test-pipeline")
        self.assertEqual(first_call[1]["context"]["feature_name"], "test-feature")


class TestStage(unittest.TestCase):
    """Tests for Stage class."""
    
    def test_stage_initialization(self):
        """Test Stage initialization."""
        stage = Stage(
            name="Test Stage",
            role="software-engineer",
            order=1,
            required=True,
            dependencies=[],
            conditions={},
            parallel_group=None,
            skill="software-engineer",
            prompt_template="Test prompt"
        )
        
        self.assertEqual(stage.name, "Test Stage")
        self.assertEqual(stage.role, "software-engineer")
        self.assertEqual(stage.order, 1)
        self.assertEqual(stage.status, StageStatus.PENDING)
    
    def test_stage_serialization(self):
        """Test Stage serialization and deserialization."""
        stage = Stage(
            name="Test Stage",
            role="software-engineer",
            order=1,
            required=True,
            dependencies=[],
            conditions={},
            parallel_group=None,
            skill="software-engineer",
            prompt_template="Test prompt"
        )
        
        # Serialize
        stage_dict = stage.to_dict()
        
        # Verify serialization
        self.assertEqual(stage_dict["name"], "Test Stage")
        self.assertEqual(stage_dict["role"], "software-engineer")
        self.assertEqual(stage_dict["order"], 1)
        
        # Deserialize
        new_stage = Stage.from_dict(stage_dict)
        
        # Verify deserialization
        self.assertEqual(new_stage.name, "Test Stage")
        self.assertEqual(new_stage.role, "software-engineer")
        self.assertEqual(new_stage.order, 1)


class TestSkillInvoker(unittest.TestCase):
    """Tests for SkillInvoker functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_repo = Path(self.test_dir) / "test_repo"
        self.test_repo.mkdir()
        self.skills_dir = self.test_repo / ".iflow" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a mock skill
        self.mock_skill = self.skills_dir / "test-skill"
        self.mock_skill.mkdir()
        self.mock_skill_config = self.mock_skill / "config.json"
        self.mock_skill_config.write_text('{"name": "test-skill", "version": "1.0.0"}')
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_skill_invoker_initialization(self):
        """Test SkillInvoker initialization."""
        invoker = create_skill_invoker(
            skills_dir=self.skills_dir,
            repo_root=self.test_repo,
            dry_run=False
        )
        
        self.assertIsNotNone(invoker)
        self.assertEqual(invoker.skills_dir, self.skills_dir)
        self.assertEqual(invoker.repo_root, self.test_repo)
    
    def test_skill_invocation_result(self):
        """Test SkillInvocationResult."""
        result = SkillInvocationResult(
            success=True,
            output="Test output",
            error=None,
            exit_code=0,
            execution_time=1.5,
            retries=0
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.output, "Test output")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.execution_time, 1.5)
        
        # Test serialization
        result_dict = result.to_dict()
        self.assertEqual(result_dict["success"], True)
        self.assertEqual(result_dict["output"], "Test output")
    
    def test_skill_invocation_success(self):
        """Test successful skill invocation."""
        invoker = create_skill_invoker(
            skills_dir=self.skills_dir,
            repo_root=self.test_repo,
            dry_run=True
        )
        
        result = invoker.invoke_skill(
            skill_name="test-skill",
            prompt="Test prompt",
            context={}
        )
        
        self.assertTrue(result.success)
        self.assertIn("DRY-RUN", result.output)


if __name__ == "__main__":
    unittest.main()