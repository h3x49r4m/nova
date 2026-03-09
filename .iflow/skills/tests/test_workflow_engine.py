#!/usr/bin/env python3
"""Test suite for workflow execution engine.

Tests workflow parsing and execution functionality.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

# Import workflow classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.workflow_parser import WorkflowParser, Workflow, WorkflowStep, StepStatus, WorkflowStatus
from utils.workflow_executor import WorkflowExecutor
from utils.skill_invoker import SkillInvocationResult


class TestWorkflowParser(unittest.TestCase):
    """Test workflow parser functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = WorkflowParser()
        self.temp_dir = tempfile.mkdtemp()
        self.workflow_file = Path(self.temp_dir) / "test-workflow.md"
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_parse_simple_workflow(self):
        """Test parsing a simple workflow."""
        workflow_content = """# Test Workflow

## Objective
Test objective

## Steps

1. **First Step**
   First step description

2. **Second Step**
   Second step description

## Output
Test output
"""
        
        self.workflow_file.write_text(workflow_content)
        workflow = self.parser.parse(self.workflow_file)
        
        self.assertEqual(workflow.name, "test-workflow")
        self.assertEqual(workflow.objective, "Test objective")
        self.assertEqual(len(workflow.steps), 2)
        self.assertEqual(workflow.steps[0].title, "First Step")
        self.assertEqual(workflow.steps[1].title, "Second Step")
        self.assertEqual(workflow.output, "Test output")
    
    def test_parse_workflow_with_substeps(self):
        """Test parsing a workflow with substeps."""
        workflow_content = """# Test Workflow

## Objective
Test objective

## Steps

1. **First Step**
   First step description
   - Substep 1
   - Substep 2

2. **Second Step**
   Second step description
   - Substep 3

## Output
Test output
"""
        
        self.workflow_file.write_text(workflow_content)
        workflow = self.parser.parse(self.workflow_file)
        
        self.assertEqual(len(workflow.steps), 2)
        self.assertEqual(len(workflow.steps[0].substeps), 2)
        self.assertEqual(len(workflow.steps[1].substeps), 1)
    
    def test_workflow_serialization(self):
        """Test workflow serialization to/from dict."""
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(
                    step_number=1,
                    title="First Step",
                    description="Description"
                )
            ]
        )
        
        workflow_dict = workflow.to_dict()
        restored_workflow = Workflow.from_dict(workflow_dict)
        
        self.assertEqual(restored_workflow.name, workflow.name)
        self.assertEqual(restored_workflow.objective, workflow.objective)
        self.assertEqual(len(restored_workflow.steps), len(workflow.steps))
        self.assertEqual(restored_workflow.steps[0].title, workflow.steps[0].title)
    
    def test_get_next_step(self):
        """Test getting the next step to execute."""
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(step_number=1, title="Step 1", description=""),
                WorkflowStep(step_number=2, title="Step 2", description=""),
                WorkflowStep(step_number=3, title="Step 3", description="")
            ]
        )
        
        # First step should be returned
        next_step = workflow.get_next_step()
        self.assertIsNotNone(next_step)
        self.assertEqual(next_step.step_number, 1)
        
        # Mark first step as completed
        workflow.steps[0].status = StepStatus.COMPLETED
        next_step = workflow.get_next_step()
        self.assertEqual(next_step.step_number, 2)
        
        # Mark all steps as completed
        for step in workflow.steps:
            step.status = StepStatus.COMPLETED
        
        next_step = workflow.get_next_step()
        self.assertIsNone(next_step)
    
    def test_get_progress(self):
        """Test calculating workflow progress."""
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(step_number=1, title="Step 1", description=""),
                WorkflowStep(step_number=2, title="Step 2", description=""),
                WorkflowStep(step_number=3, title="Step 3", description=""),
                WorkflowStep(step_number=4, title="Step 4", description="")
            ]
        )
        
        # Initial progress should be 0%
        self.assertEqual(workflow.get_progress(), 0.0)
        
        # Complete 2 steps
        workflow.steps[0].status = StepStatus.COMPLETED
        workflow.steps[1].status = StepStatus.COMPLETED
        self.assertEqual(workflow.get_progress(), 50.0)
        
        # Complete all steps
        for step in workflow.steps:
            step.status = StepStatus.COMPLETED
        self.assertEqual(workflow.get_progress(), 100.0)


class TestWorkflowExecutor(unittest.TestCase):
    """Test workflow executor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)
        self.skills_dir = self.repo_root / '.iflow' / 'skills'
        self.skills_dir.mkdir(parents=True)
        
        # Create mock skill invoker
        self.mock_invoker = Mock()
        self.mock_invoker.invoke_skill.return_value = SkillInvocationResult(
            success=True,
            output="Skill executed successfully",
            exit_code=0
        )
        
        # Create mock skill registry
        self.mock_registry = Mock()
        mock_skill = Mock()
        mock_skill.current_version = "1.0.0"
        self.mock_registry.get_skill.return_value = mock_skill
        self.mock_registry.get_skill_capabilities.return_value = {}
        
        self.executor = WorkflowExecutor(
            repo_root=self.repo_root,
            skill_invoker=self.mock_invoker,
            dry_run=False
        )
        
        # Replace the skill registry with mock
        self.executor.skill_registry = self.mock_registry
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_execute_simple_workflow(self):
        """Test executing a simple workflow."""
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(step_number=1, title="Step 1", description=""),
                WorkflowStep(step_number=2, title="Step 2", description=""),
                WorkflowStep(step_number=3, title="Step 3", description="")
            ]
        )
        
        code, output = self.executor.execute_workflow(workflow)
        
        self.assertEqual(code, 0)
        self.assertEqual(workflow.status, WorkflowStatus.COMPLETED)
        self.assertEqual(workflow.get_progress(), 100.0)
        self.assertEqual(self.mock_invoker.invoke_skill.call_count, 3)
    
    def test_execute_workflow_with_failure(self):
        """Test executing a workflow that fails."""
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(step_number=1, title="Step 1", description=""),
                WorkflowStep(step_number=2, title="Step 2", description=""),
                WorkflowStep(step_number=3, title="Step 3", description="")
            ]
        )
        
        # Make the second step fail
        call_count = [0]
        def mock_invoke(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                return SkillInvocationResult(
                    success=False,
                    output="",
                    error="Step failed",
                    exit_code=1
                )
            return SkillInvocationResult(
                success=True,
                output="Success",
                exit_code=0
            )
        
        self.mock_invoker.invoke_skill.side_effect = mock_invoke
        
        code, output = self.executor.execute_workflow(workflow)
        
        self.assertEqual(code, 1)
        self.assertEqual(workflow.status, WorkflowStatus.FAILED)
        self.assertEqual(workflow.steps[1].status, StepStatus.FAILED)
        self.assertEqual(workflow.steps[1].error, "Step failed")
    
    def test_dry_run_mode(self):
        """Test executing a workflow in dry-run mode."""
        executor = WorkflowExecutor(
            repo_root=self.repo_root,
            dry_run=True
        )
        
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(step_number=1, title="Step 1", description=""),
                WorkflowStep(step_number=2, title="Step 2", description="")
            ]
        )
        
        code, output = executor.execute_workflow(workflow)
        
        self.assertEqual(code, 0)
        self.assertEqual(workflow.status, WorkflowStatus.COMPLETED)
        # In dry-run mode, skills should not be invoked
        # Log entries: workflow_started, step_1_started, step_2_started, workflow_completed
        self.assertEqual(len(executor.execution_log), 4)
    
    def test_execution_log(self):
        """Test execution logging."""
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(step_number=1, title="Step 1", description=""),
                WorkflowStep(step_number=2, title="Step 2", description="")
            ]
        )
        
        self.executor.execute_workflow(workflow)
        
        log = self.executor.get_execution_log()
        
        self.assertGreater(len(log), 0)
        self.assertEqual(log[0]["event_type"], "workflow_started")
        self.assertEqual(log[-1]["event_type"], "workflow_completed")
    
    def test_cancel_workflow(self):
        """Test cancelling a workflow."""
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[
                WorkflowStep(step_number=1, title="Step 1", description=""),
                WorkflowStep(step_number=2, title="Step 2", description="")
            ]
        )
        
        workflow.status = WorkflowStatus.IN_PROGRESS
        
        code, output = self.executor.cancel_workflow(workflow)
        
        self.assertEqual(code, 0)
        self.assertEqual(workflow.status, WorkflowStatus.CANCELLED)
        self.assertIsNotNone(workflow.completed_at)
    
    def test_build_step_prompt(self):
        """Test building a step prompt."""
        step = WorkflowStep(
            step_number=1,
            title="Test Step",
            description="Test description",
            substeps=["Substep 1", "Substep 2"]
        )
        
        workflow = Workflow(
            name="test-workflow",
            objective="Test objective",
            steps=[step]
        )
        
        prompt = self.executor._build_step_prompt(step, workflow, {"context": "value"})
        
        self.assertIn("step 1", prompt)
        self.assertIn("Test Step", prompt)
        self.assertIn("Test objective", prompt)
        self.assertIn("Test description", prompt)
        self.assertIn("Substep 1", prompt)
        self.assertIn("Substep 2", prompt)
        self.assertIn("context: value", prompt)


if __name__ == '__main__':
    unittest.main()