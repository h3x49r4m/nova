"""Pipeline Orchestrator - Manages execution of team pipelines.

This module provides the core orchestration logic for team pipelines,
including skill invocation, state management, progress tracking, and
error handling.
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    IFlowError
)
from .skill_invoker import SkillInvoker


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(Enum):
    """Stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class Stage:
    """Represents a single stage in a pipeline."""
    
    def __init__(
        self,
        name: str,
        role: str,
        order: int,
        required: bool = True,
        dependencies: Optional[List[int]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        parallel_group: Optional[str] = None,
        skill: Optional[str] = None,
        prompt_template: Optional[str] = None
    ):
        self.name = name
        self.role = role
        self.order = order
        self.required = required
        self.dependencies = dependencies or []
        self.conditions = conditions or {}
        self.parallel_group = parallel_group
        self.skill = skill
        self.prompt_template = prompt_template
        self.status = StageStatus.PENDING
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.retries: int = 0
        self.max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stage to dictionary."""
        return {
            "name": self.name,
            "role": self.role,
            "order": self.order,
            "required": self.required,
            "dependencies": self.dependencies,
            "conditions": self.conditions,
            "parallel_group": self.parallel_group,
            "skill": self.skill,
            "prompt_template": self.prompt_template,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "result": self.result,
            "retries": self.retries,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Stage':
        """Create stage from dictionary."""
        stage = cls(
            data["name"],
            data["role"],
            data["order"],
            data.get("required", True),
            data.get("dependencies", []),
            data.get("conditions", {}),
            data.get("parallel_group"),
            data.get("skill"),
            data.get("prompt_template")
        )
        stage.status = StageStatus(data.get("status", "pending"))
        stage.started_at = data.get("started_at")
        stage.completed_at = data.get("completed_at")
        stage.error = data.get("error")
        stage.result = data.get("result")
        stage.retries = data.get("retries", 0)
        stage.max_retries = data.get("max_retries", 3)
        return stage


class PipelineState:
    """Represents the state of a pipeline execution."""
    
    def __init__(self, pipeline_name: str, feature_name: str):
        self.pipeline_name = pipeline_name
        self.feature_name = feature_name
        self.status = PipelineStatus.PENDING
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.stages: List[Stage] = []
        self.current_stage: int = 0
        self.metadata: Dict[str, Any] = {}
        self.issues: List[Dict[str, Any]] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self._version = "1"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pipeline state to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "feature_name": self.feature_name,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "stages": [stage.to_dict() for stage in self.stages],
            "current_stage": self.current_stage,
            "metadata": self.metadata,
            "issues": self.issues,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "_version": self._version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineState':
        """Create pipeline state from dictionary."""
        state = cls(data["pipeline_name"], data["feature_name"])
        state.status = PipelineStatus(data.get("status", "pending"))
        state.started_at = data.get("started_at")
        state.completed_at = data.get("completed_at")
        state.stages = [Stage.from_dict(s) for s in data.get("stages", [])]
        state.current_stage = data.get("current_stage", 0)
        state.metadata = data.get("metadata", {})
        state.issues = data.get("issues", [])
        state.created_at = data.get("created_at", state.created_at)
        state.updated_at = data.get("updated_at", state.updated_at)
        state._version = data.get("_version", "1")
        return state
    
    def get_progress(self) -> float:
        """Calculate pipeline progress percentage."""
        if not self.stages:
            return 0.0
        
        completed = sum(1 for stage in self.stages if stage.status == StageStatus.COMPLETED)
        return (completed / len(self.stages)) * 100
    
    def get_next_ready_stage(self) -> Optional[Stage]:
        """Get the next stage that's ready to execute."""
        for stage in self.stages:
            if stage.status != StageStatus.PENDING:
                continue
            
            # Check dependencies
            deps_satisfied = True
            for dep_order in stage.dependencies:
                dep_stage = next((s for s in self.stages if s.order == dep_order), None)
                if not dep_stage or dep_stage.status != StageStatus.COMPLETED:
                    deps_satisfied = False
                    break
            
            if deps_satisfied:
                return stage
        
        return None


class PipelineOrchestrator:
    """Orchestrates pipeline execution."""
    
    def __init__(
        self,
        pipeline_name: str,
        feature_name: str,
        stages_config: List[Dict[str, Any]],
        repo_root: Path,
        skill_invoker: SkillInvoker,
        dry_run: bool = False
    ):
        self.pipeline_name = pipeline_name
        self.feature_name = feature_name
        self.repo_root = repo_root
        self.skill_invoker = skill_invoker
        self.dry_run = dry_run
        
        # Initialize pipeline state
        self.state = PipelineState(pipeline_name, feature_name)
        
        # Create stages from config
        for i, stage_config in enumerate(stages_config):
            stage = Stage(
                name=stage_config.get("name", f"stage-{i+1}"),
                role=stage_config.get("role", "unknown"),
                order=i + 1,
                required=stage_config.get("required", True),
                dependencies=stage_config.get("dependencies", []),
                conditions=stage_config.get("conditions", {}),
                parallel_group=stage_config.get("parallel_group"),
                skill=stage_config.get("skill"),
                prompt_template=stage_config.get("prompt_template")
            )
            self.state.stages.append(stage)
        
        # Shared state directory
        self.shared_state_dir = repo_root / '.iflow' / 'skills' / '.shared-state'
        self.pipeline_status_file = self.shared_state_dir / 'pipeline-status.md'
    
    def start(self) -> Tuple[int, str]:
        """Start pipeline execution."""
        if self.state.status == PipelineStatus.RUNNING:
            return 1, "Pipeline is already running."
        
        self.state.status = PipelineStatus.RUNNING
        self.state.started_at = datetime.now().isoformat()
        
        return self.execute()
    
    def resume(self) -> Tuple[int, str]:
        """Resume a paused pipeline."""
        if self.state.status != PipelineStatus.PAUSED:
            return 1, f"Cannot resume pipeline in {self.state.status.value} state."
        
        return self.execute()
    
    def pause(self) -> Tuple[int, str]:
        """Pause pipeline execution."""
        if self.state.status != PipelineStatus.RUNNING:
            return 1, f"Cannot pause pipeline in {self.state.status.value} state."
        
        self.state.status = PipelineStatus.PAUSED
        self.state.updated_at = datetime.now().isoformat()
        
        return 0, "Pipeline paused successfully."
    
    def cancel(self) -> Tuple[int, str]:
        """Cancel pipeline execution."""
        # Cannot cancel if already completed or cancelled
        if self.state.status in [PipelineStatus.COMPLETED, PipelineStatus.CANCELLED]:
            return 1, f"Cannot cancel pipeline in {self.state.status.value} state."
        
        self.state.status = PipelineStatus.CANCELLED
        self.state.completed_at = datetime.now().isoformat()
        self.state.updated_at = datetime.now().isoformat()
        
        return 0, "Pipeline cancelled successfully."
    
    def execute(self) -> Tuple[int, str]:
        """Execute the pipeline."""
        try:
            while True:
                # Get next ready stage
                next_stage = self.state.get_next_ready_stage()
                
                if not next_stage:
                    # Check if we're done
                    if all(s.status in [StageStatus.COMPLETED, StageStatus.SKIPPED] for s in self.state.stages):
                        self.state.status = PipelineStatus.COMPLETED
                        self.state.completed_at = datetime.now().isoformat()
                        self.state.updated_at = datetime.now().isoformat()
                        return 0, self._get_completion_message()
                    elif any(s.status == StageStatus.FAILED for s in self.state.stages):
                        self.state.status = PipelineStatus.FAILED
                        self.state.completed_at = datetime.now().isoformat()
                        self.state.updated_at = datetime.now().isoformat()
                        return 1, self._get_failure_message()
                    else:
                        # Waiting for dependencies or paused
                        return 0, self._get_status_message()
                
                # Check for parallel stages
                parallel_stages = self._get_parallel_stages(next_stage)
                
                if parallel_stages:
                    # Execute parallel stages
                    results = self._execute_parallel_stages(parallel_stages)
                    
                    all_success = all(r[0] == 0 for r in results)
                    
                    if not all_success:
                        # Some stages failed
                        return 1, self._get_parallel_failure_message(results)
                else:
                    # Execute single stage
                    code, output = self._execute_stage(next_stage)
                    
                    if code != 0:
                        if next_stage.retries < next_stage.max_retries:
                            next_stage.retries += 1
                            # Reset stage status to PENDING so it can be retried
                            next_stage.status = StageStatus.PENDING
                            next_stage.started_at = None
                            self.state.issues.append({
                                "severity": "error",
                                "title": f"Stage {next_stage.order} failed",
                                "description": output,
                                "assigned_to": next_stage.role,
                                "status": "retrying",
                                "retry_count": next_stage.retries
                            })
                            continue
                        else:
                            # Max retries exceeded - mark stage as failed
                            next_stage.status = StageStatus.FAILED
                            # Set pipeline status to FAILED before returning
                            self.state.status = PipelineStatus.FAILED
                            self.state.completed_at = datetime.now().isoformat()
                            self.state.updated_at = datetime.now().isoformat()
                            return 1, self._get_stage_failure_message(next_stage, output)
                
                self.state.updated_at = datetime.now().isoformat()
        
        except IFlowError as e:
            self.state.status = PipelineStatus.FAILED
            self.state.completed_at = datetime.now().isoformat()
            self.state.updated_at = datetime.now().isoformat()
            return 1, f"Pipeline failed: {e.message}"
        except Exception as e:
            self.state.status = PipelineStatus.FAILED
            self.state.completed_at = datetime.now().isoformat()
            self.state.updated_at = datetime.now().isoformat()
            return 1, f"Unexpected error: {str(e)}"
    
    def _execute_stage(self, stage: Stage) -> Tuple[int, str]:
        """Execute a single stage."""
        stage.status = StageStatus.RUNNING
        stage.started_at = datetime.now().isoformat()
        self.state.updated_at = datetime.now().isoformat()
        
        try:
            # Check conditions
            if not self._check_conditions(stage):
                stage.status = StageStatus.SKIPPED
                stage.completed_at = datetime.now().isoformat()
                return 0, f"Stage {stage.order} skipped due to conditions."
            
            if self.dry_run:
                print(f"[DRY-RUN] Would execute stage {stage.order}: {stage.name} by {stage.role}")
                stage.status = StageStatus.COMPLETED
                stage.completed_at = datetime.now().isoformat()
                return 0, f"Stage {stage.order} completed (dry-run)."
            
            # Invoke the skill
            code, output = self._invoke_skill(stage)
            
            if code == 0:
                stage.status = StageStatus.COMPLETED
                stage.result = {"output": output}
            else:
                stage.status = StageStatus.FAILED
                stage.error = output
            
            stage.completed_at = datetime.now().isoformat()
            
            return code, output
        
        except Exception as e:
            stage.status = StageStatus.FAILED
            stage.error = str(e)
            stage.completed_at = datetime.now().isoformat()
            return 1, f"Stage execution error: {str(e)}"
    
    def _execute_parallel_stages(self, stages: List[Stage]) -> List[Tuple[int, str]]:
        """Execute multiple stages in parallel."""
        results = []
        
        for stage in stages:
            # Start each stage
            stage.status = StageStatus.RUNNING
            stage.started_at = datetime.now().isoformat()
            
            if self.dry_run:
                print(f"[DRY-RUN] Would execute stage {stage.order}: {stage.name} by {stage.role} (parallel)")
                results.append((0, f"Stage {stage.order} completed (dry-run)."))
                stage.status = StageStatus.COMPLETED
                stage.completed_at = datetime.now().isoformat()
            else:
                # Note: In a real implementation, you'd use threading/asyncio here
                # For now, we'll execute sequentially but mark as parallel conceptually
                code, output = self._invoke_skill(stage)
                results.append((code, output))
                
                if code == 0:
                    stage.status = StageStatus.COMPLETED
                    stage.result = {"output": output}
                else:
                    stage.status = StageStatus.FAILED
                    stage.error = output
                
                stage.completed_at = datetime.now().isoformat()
        
        return results
    
    def _invoke_skill(self, stage: Stage) -> Tuple[int, str]:
        """Invoke the skill for a stage."""
        try:
            # Use the skill from stage config, or fall back to role-based mapping
            skill_name = stage.skill or self._role_to_skill(stage.role)
            
            if not skill_name:
                return 1, f"No skill found for role: {stage.role}"
            
            # Prepare prompt for the skill
            prompt = self._prepare_skill_prompt(stage)
            
            # Prepare context
            context = {
                "pipeline_name": self.pipeline_name,
                "feature_name": self.feature_name,
                "stage_name": stage.name,
                "stage_order": stage.order,
                "role": stage.role
            }
            
            # Invoke the skill using skill_invoker
            result = self.skill_invoker.invoke_skill(
                skill_name=skill_name,
                prompt=prompt,
                context=context,
                timeout=300,  # 5 minutes default timeout
                retry_on_failure=True,
                max_retries=stage.max_retries,
                validate_output=True
            )
            
            if result.success:
                return 0, result.output
            else:
                return 1, result.error or f"Skill execution failed with exit code {result.exit_code}"
        
        except Exception as e:
            return 1, f"Skill invocation error: {str(e)}"
    
    def _prepare_skill_prompt(self, stage: Stage) -> str:
        """Prepare the prompt for a skill based on stage information."""
        # Check if stage has a prompt_template from config
        if hasattr(stage, 'prompt_template') and stage.prompt_template:
            # Format the template with context
            prompt = f"{stage.prompt_template}\n".format(
                pipeline_name=self.pipeline_name,
                feature_name=self.feature_name,
                stage_name=stage.name,
                stage_order=stage.order,
                role=stage.role
            )
        else:
            prompt = f"""
You are acting as {stage.role} in the {self.pipeline_name} pipeline.

Current Task: {stage.name}
Feature: {self.feature_name}
Stage Order: {stage.order}

Please perform the required tasks for this stage and provide a detailed output of your work.
"""
        
        # Add information about dependencies
        if stage.dependencies:
            prompt += "\nDependencies (already completed):\n"
            for dep_order in stage.dependencies:
                dep_stage = next((s for s in self.state.stages if s.order == dep_order), None)
                if dep_stage:
                    prompt += f"  - Stage {dep_stage.order}: {dep_stage.name}\n"
        
        # Add any previous stage results if available
        prev_stages = [s for s in self.state.stages if s.order < stage.order and s.result]
        if prev_stages:
            prompt += "\nPrevious Stage Results:\n"
            for prev_stage in prev_stages[-3:]:  # Last 3 stages
                if prev_stage.result and "output" in prev_stage.result:
                    prompt += f"  - {prev_stage.name}: {prev_stage.result['output'][:200]}...\n"
        
        return prompt.strip()
    
    def _check_conditions(self, stage: Stage) -> bool:
        """Check if stage conditions are met."""
        if not stage.conditions:
            return True
        
        # Implement condition checking logic
        # For now, always return True
        return True
    
    def _get_parallel_stages(self, stage: Stage) -> List[Stage]:
        """Get all stages in the same parallel group."""
        if not stage.parallel_group:
            return []
        
        return [
            s for s in self.state.stages
            if s.parallel_group == stage.parallel_group
            and s.status == StageStatus.PENDING
            and s.order >= stage.order
        ]
    
    def _role_to_skill(self, role: str) -> Optional[str]:
        """Convert role name to skill name."""
        role_mapping = {
            "client": "Client",
            "product-manager": "Product Manager",
            "project-manager": "Project Manager",
            "tech-lead": "Tech Lead",
            "software-engineer": "Software Engineer",
            "software-engineer-frontend": "Software Engineer",
            "software-engineer-backend": "Software Engineer",
            "testing-engineer": "Testing Engineer",
            "qa-engineer": "QA Engineer",
            "security-engineer": "Security Engineer",
            "devops-engineer": "DevOps Engineer",
            "documentation-specialist": "Documentation Specialist",
            "ui-ux-designer": "UI/UX Designer"
        }
        
        return role_mapping.get(role.lower())
    
    def _get_status_message(self) -> str:
        """Get current pipeline status message."""
        lines = [
            f"Pipeline: {self.pipeline_name}",
            f"Feature: {self.feature_name}",
            f"Status: {self.state.status.value}",
            f"Progress: {self.state.get_progress():.1f}%",
            ""
        ]
        
        for stage in self.state.stages:
            icon = {
                StageStatus.PENDING: "⏸",
                StageStatus.RUNNING: "▶",
                StageStatus.COMPLETED: "✓",
                StageStatus.FAILED: "✗",
                StageStatus.SKIPPED: "⊝",
                StageStatus.BLOCKED: "🚫"
            }.get(stage.status, "?")
            
            lines.append(f"  {icon} Stage {stage.order}: {stage.name} ({stage.role})")
        
        return "\n".join(lines)
    
    def _get_completion_message(self) -> str:
        """Get pipeline completion message."""
        lines = [
            f"✓ Pipeline completed successfully!",
            f"Pipeline: {self.pipeline_name}",
            f"Feature: {self.feature_name}",
            f"Duration: {self._calculate_duration()}",
            f"Stages completed: {sum(1 for s in self.state.stages if s.status == StageStatus.COMPLETED)}/{len(self.state.stages)}",
            ""
        ]
        
        if self.state.issues:
            lines.append("Issues encountered:")
            for issue in self.state.issues:
                lines.append(f"  - [{issue['severity']}] {issue['title']}")
        
        return "\n".join(lines)
    
    def _get_failure_message(self) -> str:
        """Get pipeline failure message."""
        failed_stages = [s for s in self.state.stages if s.status == StageStatus.FAILED]
        
        lines = [
            f"✗ Pipeline failed!",
            f"Pipeline: {self.pipeline_name}",
            f"Feature: {self.feature_name}",
            f"Duration: {self._calculate_duration()}",
            f"Failed stages: {len(failed_stages)}",
            ""
        ]
        
        for stage in failed_stages:
            lines.append(f"  ✗ Stage {stage.order}: {stage.name}")
            if stage.error:
                lines.append(f"    Error: {stage.error}")
        
        lines.append("")
        lines.append("Next steps:")
        lines.append("1. Review and fix the failed stage(s)")
        lines.append("2. Resume pipeline with /pipeline resume")
        
        return "\n".join(lines)
    
    def _get_stage_failure_message(self, stage: Stage, error: str) -> str:
        """Get stage failure message."""
        lines = [
            f"✗ Stage {stage.order} failed: {stage.name}",
            f"Role: {stage.role}",
            f"Retries: {stage.retries}/{stage.max_retries}",
            ""
        ]
        
        if error:
            lines.append(f"Error: {error}")
        
        lines.append("")
        lines.append("Next steps:")
        lines.append("1. Review the error above")
        lines.append("2. Fix the issue")
        lines.append("3. Resume pipeline with /pipeline resume")
        
        return "\n".join(lines)
    
    def _get_parallel_failure_message(self, results: List[Tuple[int, str]]) -> str:
        """Get parallel stages failure message."""
        lines = [
            "✗ Some parallel stages failed!",
            ""
        ]
        
        for i, (code, output) in enumerate(results):
            icon = "✓" if code == 0 else "✗"
            lines.append(f"  {icon} Stage {i+1}: {output[:50]}...")
        
        return "\n".join(lines)
    
    def _calculate_duration(self) -> str:
        """Calculate pipeline duration."""
        if not self.state.started_at:
            return "Unknown"
        
        start = datetime.fromisoformat(self.state.started_at)
        end = datetime.fromisoformat(self.state.completed_at) if self.state.completed_at else datetime.now()
        
        duration = end - start
        
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    def save_state(self, file_path: Path) -> None:
        """Save pipeline state to file."""
        self.state.updated_at = datetime.now().isoformat()
        
        if self.dry_run:
            print(f"[DRY-RUN] Would save pipeline state to: {file_path}")
            return
        
        with open(file_path, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)
    
    def load_state(self, file_path: Path) -> Tuple[int, str]:
        """Load pipeline state from file."""
        try:
            if not file_path.exists():
                return 1, f"Pipeline state file not found: {file_path}"
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            self.state = PipelineState.from_dict(data)
            
            return 0, f"Pipeline state loaded from: {file_path}"
        
        except Exception as e:
            return 1, f"Failed to load pipeline state: {str(e)}"


def create_pipeline_orchestrator(
    pipeline_name: str,
    feature_name: str,
    stages_config: List[Dict[str, Any]],
    repo_root: Path,
    skill_invoker: SkillInvoker,
    dry_run: bool = False
) -> PipelineOrchestrator:
    """Create a pipeline orchestrator instance."""
    return PipelineOrchestrator(
        pipeline_name=pipeline_name,
        feature_name=feature_name,
        stages_config=stages_config,
        repo_root=repo_root,
        skill_invoker=skill_invoker,
        dry_run=dry_run
    )