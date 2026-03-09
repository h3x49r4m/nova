"""Pipeline Git-Flow Integration - Integrates team pipelines with git-flow workflow.

This module provides integration between team pipelines and the git-flow
workflow system, allowing pipelines to be triggered at specific phases
and coordinating state between both systems.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    IFlowError,
    PipelineError,
    WorkflowError,
    ErrorCode,
    ErrorCategory
)
from .config_validator import ConfigValidator


class PipelineGitFlowIntegration:
    """Manages integration between pipelines and git-flow workflows."""
    
    def __init__(
        self,
        repo_root: Path,
        git_flow_instance: Any,
        pipeline_dir: Path
    ):
        """
        Initialize the integration.
        
        Args:
            repo_root: Repository root directory
            git_flow_instance: GitFlow instance
            pipeline_dir: Directory containing pipeline configurations
        """
        self.repo_root = repo_root
        self.git_flow = git_flow_instance
        self.pipeline_dir = pipeline_dir
        self.config_validator = ConfigValidator(repo_root / '.iflow' / 'schemas')
        
        # Pipeline to phase mappings
        self.pipeline_phase_mappings: Dict[str, int] = {}
        
        # Phase to pipeline mappings
        self.phase_pipeline_mappings: Dict[int, List[str]] = {}
    
    def configure_pipeline_phase_mapping(
        self,
        pipeline_name: str,
        phase_order: int,
        trigger_on_complete: bool = True
    ) -> Tuple[int, str]:
        """
        Configure a pipeline to run at a specific phase.
        
        Args:
            pipeline_name: Name of the pipeline
            phase_order: Phase order to trigger the pipeline
            trigger_on_complete: Whether to trigger on phase completion
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        # Validate pipeline exists
        pipeline_config = self.pipeline_dir / pipeline_name / 'pipeline.json'
        if not pipeline_config.exists():
            return 1, f"Pipeline configuration not found: {pipeline_name}"
        
        # Validate pipeline configuration
        code, output = self.config_validator.validate_pipeline_config(pipeline_config)
        if code != 0:
            return 1, f"Pipeline validation failed: {output}"
        
        # Store mapping
        self.pipeline_phase_mappings[pipeline_name] = phase_order
        
        if phase_order not in self.phase_pipeline_mappings:
            self.phase_pipeline_mappings[phase_order] = []
        
        if pipeline_name not in self.phase_pipeline_mappings[phase_order]:
            self.phase_pipeline_mappings[phase_order].append(pipeline_name)
        
        return 0, f"Pipeline {pipeline_name} configured for phase {phase_order}"
    
    def trigger_pipelines_for_phase(
        self,
        phase_order: int,
        feature_name: str
    ) -> Tuple[int, str, List[Dict[str, Any]]]:
        """
        Trigger all pipelines configured for a specific phase.
        
        Args:
            phase_order: Phase order
            feature_name: Feature/project name
            
        Returns:
            Tuple of (exit_code, output_message, results_list)
        """
        if phase_order not in self.phase_pipeline_mappings:
            return 0, f"No pipelines configured for phase {phase_order}", []
        
        pipelines = self.phase_pipeline_mappings[phase_order]
        results = []
        
        for pipeline_name in pipelines:
            result = self._trigger_pipeline(pipeline_name, feature_name, phase_order)
            results.append(result)
        
        # Check if all pipelines succeeded
        all_success = all(r["success"] for r in results)
        
        if all_success:
            return 0, f"All {len(pipelines)} pipeline(s) completed successfully for phase {phase_order}", results
        else:
            failed_count = sum(1 for r in results if not r["success"])
            return 1, f"{failed_count} of {len(pipelines)} pipeline(s) failed for phase {phase_order}", results
    
    def _trigger_pipeline(
        self,
        pipeline_name: str,
        feature_name: str,
        phase_order: int
    ) -> Dict[str, Any]:
        """
        Trigger a single pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            feature_name: Feature/project name
            phase_order: Phase order that triggered this pipeline
            
        Returns:
            Pipeline execution result dictionary
        """
        result = {
            "pipeline": pipeline_name,
            "feature": feature_name,
            "phase": phase_order,
            "success": False,
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Load pipeline configuration
            pipeline_config = self.pipeline_dir / pipeline_name / 'pipeline.json'
            
            with open(pipeline_config, 'r') as f:
                config = json.load(f)
            
            # Import pipeline orchestrator
            from .pipeline_orchestrator import create_pipeline_orchestrator
            from .skill_invoker import create_skill_invoker
            from .constants import Timeouts
            
            # Create skill invoker
            skill_invoker = create_skill_invoker(
                skills_dir=self.repo_root / '.iflow' / 'skills',
                repo_root=self.repo_root,
                dry_run=self.git_flow.dry_run if hasattr(self.git_flow, 'dry_run') else False,
                default_timeout=Timeouts.DEFAULT_TIMEOUT
            )
            
            # Create pipeline orchestrator
            orchestrator = create_pipeline_orchestrator(
                pipeline_name=pipeline_name,
                feature_name=feature_name,
                stages_config=config.get("stages", []),
                repo_root=self.repo_root,
                skill_invoker=skill_invoker,
                dry_run=self.git_flow.dry_run if hasattr(self.git_flow, 'dry_run') else False
            )
            
            # Execute pipeline
            code, output = orchestrator.start()
            
            result["success"] = (code == 0)
            result["message"] = output
            result["exit_code"] = code
        
        except Exception as e:
            result["message"] = f"Failed to trigger pipeline: {str(e)}"
            result["error"] = str(e)
        
        return result
    
    def get_pipeline_status_for_phase(
        self,
        phase_order: int
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get the status of all pipelines configured for a phase.
        
        Args:
            phase_order: Phase order
            
        Returns:
            Dictionary mapping pipeline names to their status
        """
        status = {}
        
        if phase_order not in self.phase_pipeline_mappings:
            return status
        
        for pipeline_name in self.phase_pipeline_mappings[phase_order]:
            # Check for pipeline state files
            state_dir = self.repo_root / '.iflow' / 'skills' / '.shared-state' / 'pipelines'
            pipeline_state_files = list(state_dir.glob(f"{pipeline_name}_*.json"))
            
            if pipeline_state_files:
                # Get the most recent state file
                latest_state_file = max(pipeline_state_files, key=lambda p: p.stat().st_mtime)
                
                try:
                    with open(latest_state_file, 'r') as f:
                        state = json.load(f)
                    
                    status[pipeline_name] = {
                        "status": state.get("status"),
                        "progress": state.get("progress", 0),
                        "current_stage": state.get("current_stage", 0),
                        "total_stages": len(state.get("stages", [])),
                        "updated_at": state.get("updated_at")
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to read pipeline state {pipeline_name}: {e}")
                    status[pipeline_name] = {"status": "unknown", "error": f"Failed to read state: {e}"}
            else:
                status[pipeline_name] = {"status": "not_started"}
        
        return status
    
    def sync_pipeline_state_to_git_flow(
        self,
        pipeline_name: str,
        phase_order: int
    ) -> Tuple[int, str]:
        """
        Synchronize pipeline state to git-flow workflow state.
        
        Args:
            pipeline_name: Name of the pipeline
            phase_order: Phase order
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            # Get pipeline status
            pipeline_status = self.get_pipeline_status_for_phase(phase_order)
            
            if pipeline_name not in pipeline_status:
                return 1, f"No pipeline state found for {pipeline_name}"
            
            status = pipeline_status[pipeline_name]
            
            # Map pipeline status to git-flow phase status
            git_flow = self.git_flow
            
            if not git_flow.workflow_state:
                return 1, "No git-flow workflow state found"
            
            # Find the corresponding phase
            if phase_order > len(git_flow.workflow_state.phases):
                return 1, f"Phase {phase_order} not found in git-flow workflow"
            
            phase = git_flow.workflow_state.phases[phase_order - 1]
            
            # Update phase status based on pipeline status
            if status.get("status") == "completed":
                phase.status = "complete"
                phase.completed_at = datetime.now().isoformat()
            elif status.get("status") == "failed":
                phase.status = "failed"
            elif status.get("status") == "running":
                phase.status = "active"
            
            # Save git-flow state
            git_flow.save_workflow_state()
            
            return 0, f"Synchronized {pipeline_name} state to git-flow phase {phase_order}"
        
        except Exception as e:
            return 1, f"Failed to sync pipeline state: {str(e)}"
    
    def list_configured_pipelines(self) -> Dict[int, List[str]]:
        """
        List all configured pipeline-phase mappings.
        
        Returns:
            Dictionary mapping phase orders to pipeline names
        """
        return self.phase_pipeline_mappings.copy()
    
    def remove_pipeline_phase_mapping(
        self,
        pipeline_name: str,
        phase_order: int
    ) -> Tuple[int, str]:
        """
        Remove a pipeline-phase mapping.
        
        Args:
            pipeline_name: Name of the pipeline
            phase_order: Phase order
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        if pipeline_name not in self.pipeline_phase_mappings:
            return 1, f"Pipeline {pipeline_name} not configured for any phase"
        
        if self.pipeline_phase_mappings[pipeline_name] != phase_order:
            return 1, f"Pipeline {pipeline_name} is configured for phase {self.pipeline_phase_mappings[pipeline_order]}, not {phase_order}"
        
        # Remove mapping
        del self.pipeline_phase_mappings[pipeline_name]
        
        if phase_order in self.phase_pipeline_mappings and pipeline_name in self.phase_pipeline_mappings[phase_order]:
            self.phase_pipeline_mappings[phase_order].remove(pipeline_name)
            
            if not self.phase_pipeline_mappings[phase_order]:
                del self.phase_pipeline_mappings[phase_order]
        
        return 0, f"Removed mapping for pipeline {pipeline_name} from phase {phase_order}"


def create_pipeline_git_flow_integration(
    repo_root: Path,
    git_flow_instance: Any,
    pipeline_dir: Path
) -> PipelineGitFlowIntegration:
    """Create a pipeline git-flow integration instance."""
    return PipelineGitFlowIntegration(
        repo_root=repo_root,
        git_flow_instance=git_flow_instance,
        pipeline_dir=pipeline_dir
    )