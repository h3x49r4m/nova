"""Workflow Executor - Executes parsed workflows.

This module provides functionality to execute workflows by invoking
the appropriate skills for each step and tracking progress.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from .workflow_parser import Workflow, WorkflowStep, StepStatus, WorkflowStatus
from .exceptions import IFlowError, ErrorCode
from .skill_invoker import SkillInvoker, create_skill_invoker

# Import skill manager from parent directory
import sys
from pathlib import Path
skill_manager_path = Path(__file__).parent.parent
sys.path.insert(0, str(skill_manager_path))
from skill_manager import SkillRegistry, SkillVersionManager


class WorkflowExecutor:
    """Executes workflows step by step."""
    
    def __init__(
        self,
        repo_root: Path,
        skill_invoker: Optional[SkillInvoker] = None,
        dry_run: bool = False
    ):
        """
        Initialize workflow executor.
        
        Args:
            repo_root: Repository root directory
            skill_invoker: Optional skill invoker instance
            dry_run: If True, simulate execution without actual skill calls
        """
        self.repo_root = repo_root
        self.skills_dir = repo_root / '.iflow' / 'skills'
        
        if skill_invoker:
            self.skill_invoker = skill_invoker
        else:
            self.skill_invoker = create_skill_invoker(
                skills_dir=self.skills_dir,
                repo_root=repo_root,
                dry_run=dry_run
            )
        
        # Initialize skill manager for skill discovery and validation
        self.skill_registry = SkillRegistry(self.skills_dir)
        
        self.dry_run = dry_run
        self.current_workflow: Optional[Workflow] = None
        self.execution_log: List[Dict[str, Any]] = []
    
    def execute_workflow(
        self,
        workflow: Workflow,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[int, str]:
        """
        Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            context: Optional context information
            
        Returns:
            Tuple of (exit_code, message)
        """
        self.current_workflow = workflow
        context = context or {}
        
        # Mark workflow as started
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.started_at = datetime.now().isoformat()
        
        self._log_event("workflow_started", {"workflow": workflow.name})
        
        try:
            # Execute each step
            while True:
                next_step = workflow.get_next_step()
                
                if not next_step:
                    # All steps completed
                    workflow.status = WorkflowStatus.COMPLETED
                    workflow.completed_at = datetime.now().isoformat()
                    self._log_event("workflow_completed", {"workflow": workflow.name})
                    return 0, self._get_completion_message()
                
                # Execute the step
                code, output = self._execute_step(next_step, workflow, context)
                
                if code != 0:
                    # Step failed
                    workflow.status = WorkflowStatus.FAILED
                    workflow.completed_at = datetime.now().isoformat()
                    self._log_event("workflow_failed", {
                        "workflow": workflow.name,
                        "step": next_step.step_number,
                        "error": output
                    })
                    return 1, self._get_failure_message(next_step, output)
                
                # Mark step as completed
                next_step.status = StepStatus.COMPLETED
                next_step.completed_at = datetime.now().isoformat()
                workflow.current_step = next_step.step_number
        
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now().isoformat()
            error_msg = f"Workflow execution error: {str(e)}"
            self._log_event("workflow_error", {
                "workflow": workflow.name,
                "error": error_msg
            })
            return 1, error_msg
    
    def _execute_step(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        context: Dict[str, Any]
    ) -> tuple[int, str]:
        """
        Execute a single workflow step.
        
        Args:
            step: Step to execute
            workflow: Parent workflow
            context: Execution context
            
        Returns:
            Tuple of (exit_code, message)
        """
        # Mark step as in progress
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now().isoformat()
        
        self._log_event("step_started", {
            "workflow": workflow.name,
            "step": step.step_number,
            "title": step.title
        })
        
        if self.dry_run:
            print(f"[DRY-RUN] Executing step {step.step_number}: {step.title}")
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now().isoformat()
            return 0, f"Step {step.step_number} completed (dry-run)"
        
        # Build prompt for the skill
        prompt = self._build_step_prompt(step, workflow, context)
        
        # Determine which skill to invoke
        skill_name = self._get_skill_for_step(step, workflow)
        
        if not skill_name:
            step.status = StepStatus.SKIPPED
            step.notes = "No skill mapped for this step"
            return 0, f"Step {step.step_number} skipped (no skill mapped)"
        
        # Invoke the skill
        result = self.skill_invoker.invoke_skill(
            skill_name=skill_name,
            prompt=prompt,
            context={
                **context,
                "workflow_name": workflow.name,
                "step_number": step.step_number,
                "step_title": step.title
            },
            timeout=600,  # 10 minutes
            retry_on_failure=True,
            max_retries=2
        )
        
        if result.success:
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now().isoformat()
            self._log_event("step_completed", {
                "workflow": workflow.name,
                "step": step.step_number,
                "skill": skill_name
            })
            return 0, result.output
        else:
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now().isoformat()
            step.error = result.error
            self._log_event("step_failed", {
                "workflow": workflow.name,
                "step": step.step_number,
                "skill": skill_name,
                "error": result.error
            })
            return 1, result.error or f"Step {step.step_number} failed"
    
    def _build_step_prompt(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt for a workflow step.
        
        Args:
            step: Step to build prompt for
            workflow: Parent workflow
            context: Execution context
            
        Returns:
            Prompt string
        """
        prompt = f"""You are executing step {step.step_number} of the '{workflow.name}' workflow.

Workflow Objective: {workflow.objective}

Current Step: {step.title}
"""
        
        if step.description:
            prompt += f"Description: {step.description}\n"
        
        if step.substeps:
            prompt += "\nSubsteps:\n"
            for i, substep in enumerate(step.substeps, 1):
                prompt += f"  {i}. {substep}\n"
        
        # Add context information
        if context:
            prompt += "\nContext:\n"
            for key, value in context.items():
                prompt += f"  - {key}: {value}\n"
        
        # Add workflow objective
        prompt += f"\nPlease perform the required tasks for this step according to the workflow objective."
        
        return prompt
    
    def _get_skill_for_step(self, step: WorkflowStep, workflow: Workflow) -> Optional[str]:
        """
        Determine which skill to invoke for a step.
        
        Args:
            step: Step to execute
            workflow: Parent workflow
            
        Returns:
            Skill name or None
        """
        # Map workflow names to skills
        workflow_to_skill = {
            "feature-implementation": "software-engineer",
            "bug-fixing": "software-engineer",
            "architecture-design": "tech-lead",
            "test-development": "testing-engineer",
            "test-automation": "testing-engineer",
            "quality-validation": "qa-engineer",
            "uat-execution": "qa-engineer",
            "security-validation": "security-engineer",
            "feature-planning": "product-manager",
            "sprint-management": "project-manager",
            "requirements-gathering": "client",
            "design-creation": "ui-ux-designer",
            "documentation-creation": "documentation-specialist",
            "deployment": "devops-engineer",
            "infrastructure-setup": "devops-engineer",
            "code-review": "team-pipeline-auto-review"
        }
        
        # Get skill name from mapping
        skill_name = workflow_to_skill.get(workflow.name, workflow.name)
        
        # Validate skill exists using skill manager
        skill = self.skill_registry.get_skill(skill_name)
        if not skill:
            self._log_event("skill_not_found", {
                "workflow": workflow.name,
                "skill": skill_name,
                "step": step.step_number
            })
            return None
        
        # Check skill capabilities
        capabilities = self.skill_registry.get_skill_capabilities(skill_name, skill.current_version)
        if not capabilities:
            self._log_event("skill_no_capabilities", {
                "workflow": workflow.name,
                "skill": skill_name,
                "version": skill.current_version,
                "step": step.step_number
            })
        
        return skill_name
    
    def _get_completion_message(self) -> str:
        """Get workflow completion message."""
        workflow = self.current_workflow
        if not workflow:
            return "Workflow completed"
        
        lines = [
            f"✓ Workflow '{workflow.name}' completed successfully!",
            f"Objective: {workflow.objective}",
            f"Progress: {workflow.get_progress():.1f}%",
            f"Steps completed: {sum(1 for s in workflow.steps if s.status == StepStatus.COMPLETED)}/{len(workflow.steps)}",
            f"Duration: {self._calculate_duration()}"
        ]
        
        return "\n".join(lines)
    
    def _get_failure_message(self, step: WorkflowStep, error: str) -> str:
        """Get workflow failure message."""
        workflow = self.current_workflow
        if not workflow:
            return f"Workflow failed: {error}"
        
        lines = [
            f"✗ Workflow '{workflow.name}' failed!",
            f"Failed at step {step.step_number}: {step.title}",
            f"Error: {error}",
            f"Progress: {workflow.get_progress():.1f}%",
            f"Steps completed: {sum(1 for s in workflow.steps if s.status == StepStatus.COMPLETED)}/{len(workflow.steps)}"
        ]
        
        return "\n".join(lines)
    
    def _calculate_duration(self) -> str:
        """Calculate workflow duration."""
        workflow = self.current_workflow
        if not workflow or not workflow.started_at:
            return "Unknown"
        
        start = datetime.fromisoformat(workflow.started_at)
        end = datetime.fromisoformat(workflow.completed_at) if workflow.completed_at else datetime.now()
        
        duration = end - start
        
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an execution event."""
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get the execution log."""
        return self.execution_log
    
    def resume_workflow(
        self,
        workflow: Workflow,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[int, str]:
        """
        Resume a paused workflow.
        
        Args:
            workflow: Workflow to resume
            context: Optional context information
            
        Returns:
            Tuple of (exit_code, message)
        """
        if workflow.status != WorkflowStatus.IN_PROGRESS:
            return 1, f"Cannot resume workflow in {workflow.status.value} state"
        
        return self.execute_workflow(workflow, context)
    
    def cancel_workflow(self, workflow: Workflow) -> tuple[int, str]:
        """
        Cancel a running workflow.
        
        Args:
            workflow: Workflow to cancel
            
        Returns:
            Tuple of (exit_code, message)
        """
        if workflow.status not in [WorkflowStatus.IN_PROGRESS, WorkflowStatus.NOT_STARTED]:
            return 1, f"Cannot cancel workflow in {workflow.status.value} state"
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now().isoformat()
        
        self._log_event("workflow_cancelled", {"workflow": workflow.name})
        
        return 0, f"Workflow '{workflow.name}' cancelled"
