"""Shared State Coordinator - Coordinates shared state between pipelines.

This module provides functionality for coordinating shared state between
multiple running pipelines, including conflict detection, resolution,
and synchronization.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .file_lock import FileLock
from .audit_logger import AuditLogger
from .state_conflict_resolver import StateConflictResolver


class SharedStateCoordinator:
    """Coordinates shared state between multiple pipelines."""
    
    def __init__(self, shared_state_dir: Path, repo_root: Path):
        """
        Initialize the shared state coordinator.
        
        Args:
            shared_state_dir: Directory for shared state files
            repo_root: Repository root directory
        """
        self.shared_state_dir = shared_state_dir
        self.repo_root = repo_root
        self.shared_state_file = shared_state_dir / "shared-state.json"
        self.lock_file = shared_state_dir / "shared-state.lock"
        self.audit_logger = AuditLogger(shared_state_dir / "audit.log")
        self.conflict_resolver = StateConflictResolver()
        
        # Ensure directory exists
        self.shared_state_dir.mkdir(parents=True, exist_ok=True)
    
    def get_shared_state(self) -> Dict[str, Any]:
        """
        Get the current shared state.
        
        Returns:
            Dictionary containing the shared state
        """
        if not self.shared_state_file.exists():
            return {
                "version": "1.0.0",
                "pipelines": {},
                "shared_resources": {},
                "conflicts": [],
                "updated_at": datetime.now().isoformat()
            }
        
        try:
            with open(self.shared_state_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {
                "version": "1.0.0",
                "pipelines": {},
                "shared_resources": {},
                "conflicts": [],
                "updated_at": datetime.now().isoformat()
            }
    
    def save_shared_state(self, state: Dict[str, Any]) -> Tuple[int, str]:
        """
        Save the shared state with file locking.
        
        Args:
            state: State dictionary to save
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            state["updated_at"] = datetime.now().isoformat()
            
            # Use file lock to prevent concurrent writes
            with FileLock(str(self.lock_file), timeout=30):
                with open(self.shared_state_file, 'w') as f:
                    json.dump(state, f, indent=2)
            
            # Log the save operation
            self.audit_logger.log_event(
                event_type="state_save",
                details={"pipelines": list(state.get("pipelines", {}).keys())}
            )
            
            return 0, "Shared state saved successfully"
        
        except Exception as e:
            return 1, f"Failed to save shared state: {str(e)}"
    
    def register_pipeline(
        self,
        pipeline_name: str,
        feature_name: str,
        stage_order: int
    ) -> Tuple[int, str]:
        """
        Register a pipeline with the shared state coordinator.
        
        Args:
            pipeline_name: Name of the pipeline
            feature_name: Name of the feature/project
            stage_order: Current stage order
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        state = self.get_shared_state()
        
        if pipeline_name in state["pipelines"]:
            return 1, f"Pipeline {pipeline_name} is already registered"
        
        state["pipelines"][pipeline_name] = {
            "feature_name": feature_name,
            "current_stage": stage_order,
            "status": "running",
            "registered_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "resources_used": [],
            "shared_with": []
        }
        
        code, output = self.save_shared_state(state)
        
        if code == 0:
            self.audit_logger.log_event(
                event_type="pipeline_registered",
                details={"pipeline": pipeline_name, "feature": feature_name}
            )
        
        return code, output
    
    def update_pipeline_state(
        self,
        pipeline_name: str,
        stage_order: int,
        status: str,
        resources_used: Optional[List[str]] = None
    ) -> Tuple[int, str]:
        """
        Update the state of a registered pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            stage_order: Current stage order
            status: Pipeline status
            resources_used: List of resources used by the pipeline
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        state = self.get_shared_state()
        
        if pipeline_name not in state["pipelines"]:
            return 1, f"Pipeline {pipeline_name} is not registered"
        
        pipeline_state = state["pipelines"][pipeline_name]
        pipeline_state["current_stage"] = stage_order
        pipeline_state["status"] = status
        pipeline_state["last_updated"] = datetime.now().isoformat()
        
        if resources_used:
            pipeline_state["resources_used"] = resources_used
        
        code, output = self.save_shared_state(state)
        
        if code == 0:
            self.audit_logger.log_event(
                event_type="pipeline_state_updated",
                details={
                    "pipeline": pipeline_name,
                    "stage": stage_order,
                    "status": status
                }
            )
        
        return code, output
    
    def unregister_pipeline(self, pipeline_name: str) -> Tuple[int, str]:
        """
        Unregister a pipeline from the shared state coordinator.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        state = self.get_shared_state()
        
        if pipeline_name not in state["pipelines"]:
            return 1, f"Pipeline {pipeline_name} is not registered"
        
        # Clean up shared resources
        pipeline_state = state["pipelines"][pipeline_name]
        resources_to_cleanup = pipeline_state.get("resources_used", [])
        
        for resource in resources_to_cleanup:
            if resource in state["shared_resources"]:
                state["shared_resources"][resource]["used_by"].remove(pipeline_name)
                
                if not state["shared_resources"][resource]["used_by"]:
                    del state["shared_resources"][resource]
        
        # Remove pipeline
        del state["pipelines"][pipeline_name]
        
        code, output = self.save_shared_state(state)
        
        if code == 0:
            self.audit_logger.log_event(
                event_type="pipeline_unregistered",
                details={"pipeline": pipeline_name}
            )
        
        return code, output
    
    def claim_shared_resource(
        self,
        pipeline_name: str,
        resource_name: str,
        resource_type: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, str]:
        """
        Claim a shared resource for a pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            resource_name: Name of the resource
            resource_type: Type of the resource (e.g., "file", "branch", "lock")
            details: Additional resource details
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        state = self.get_shared_state()
        
        if pipeline_name not in state["pipelines"]:
            return 1, f"Pipeline {pipeline_name} is not registered"
        
        # Check if resource exists
        if resource_name not in state["shared_resources"]:
            state["shared_resources"][resource_name] = {
                "type": resource_type,
                "used_by": [],
                "created_at": datetime.now().isoformat(),
                "details": details or {}
            }
        
        resource = state["shared_resources"][resource_name]
        
        # Check if resource is already in use by another pipeline
        if resource["used_by"] and pipeline_name not in resource["used_by"]:
            # Check if resource is exclusive
            if details and details.get("exclusive", False):
                return 1, f"Resource {resource_name} is exclusively used by {resource['used_by']}"
        
        # Add pipeline to resource users
        if pipeline_name not in resource["used_by"]:
            resource["used_by"].append(pipeline_name)
        
        # Add resource to pipeline's used resources
        pipeline_state = state["pipelines"][pipeline_name]
        if resource_name not in pipeline_state["resources_used"]:
            pipeline_state["resources_used"].append(resource_name)
        
        code, output = self.save_shared_state(state)
        
        if code == 0:
            self.audit_logger.log_event(
                event_type="resource_claimed",
                details={
                    "pipeline": pipeline_name,
                    "resource": resource_name,
                    "type": resource_type
                }
            )
        
        return code, output
    
    def release_shared_resource(
        self,
        pipeline_name: str,
        resource_name: str
    ) -> Tuple[int, str]:
        """
        Release a shared resource from a pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            resource_name: Name of the resource
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        state = self.get_shared_state()
        
        if pipeline_name not in state["pipelines"]:
            return 1, f"Pipeline {pipeline_name} is not registered"
        
        if resource_name not in state["shared_resources"]:
            return 1, f"Resource {resource_name} does not exist"
        
        resource = state["shared_resources"][resource_name]
        
        if pipeline_name not in resource["used_by"]:
            return 1, f"Pipeline {pipeline_name} is not using resource {resource_name}"
        
        # Remove pipeline from resource users
        resource["used_by"].remove(pipeline_name)
        
        # Remove resource from pipeline's used resources
        pipeline_state = state["pipelines"][pipeline_name]
        if resource_name in pipeline_state["resources_used"]:
            pipeline_state["resources_used"].remove(resource_name)
        
        # Clean up resource if no longer used
        if not resource["used_by"]:
            del state["shared_resources"][resource_name]
        
        code, output = self.save_shared_state(state)
        
        if code == 0:
            self.audit_logger.log_event(
                event_type="resource_released",
                details={
                    "pipeline": pipeline_name,
                    "resource": resource_name
                }
            )
        
        return code, output
    
    def check_for_conflicts(self) -> List[Dict[str, Any]]:
        """
        Check for conflicts between pipelines.
        
        Returns:
            List of conflict dictionaries
        """
        state = self.get_shared_state()
        conflicts = []
        
        pipelines = state.get("pipelines", {})
        shared_resources = state.get("shared_resources", {})
        
        # Check for resource conflicts
        for resource_name, resource in shared_resources.items():
            if len(resource["used_by"]) > 1:
                if resource.get("details", {}).get("exclusive", False):
                    conflicts.append({
                        "type": "exclusive_resource_conflict",
                        "resource": resource_name,
                        "pipelines": resource["used_by"].copy()
                    })
        
        # Check for pipeline conflicts
        pipeline_list = list(pipelines.keys())
        for i, p1 in enumerate(pipeline_list):
            for p2 in pipeline_list[i + 1:]:
                pipeline1 = pipelines[p1]
                pipeline2 = pipelines[p2]
                
                # Check if pipelines are working on the same feature
                if pipeline1["feature_name"] == pipeline2["feature_name"]:
                    # Check if they're at the same stage
                    if pipeline1["current_stage"] == pipeline2["current_stage"]:
                        conflicts.append({
                            "type": "same_stage_conflict",
                            "feature": pipeline1["feature_name"],
                            "stage": pipeline1["current_stage"],
                            "pipelines": [p1, p2]
                        })
        
        # Store conflicts in state
        state["conflicts"] = conflicts
        self.save_shared_state(state)
        
        return conflicts
    
    def get_pipeline_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all registered pipelines.
        
        Returns:
            List of pipeline state dictionaries
        """
        state = self.get_shared_state()
        pipelines = state.get("pipelines", {})
        
        return [
            {
                "name": name,
                **pipeline_state
            }
            for name, pipeline_state in pipelines.items()
        ]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit log entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        return self.audit_logger.get_history(limit=limit)


def create_shared_state_coordinator(
    shared_state_dir: Path,
    repo_root: Path
) -> SharedStateCoordinator:
    """Create a shared state coordinator instance."""
    return SharedStateCoordinator(
        shared_state_dir=shared_state_dir,
        repo_root=repo_root
    )