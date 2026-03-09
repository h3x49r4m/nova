"""Pipeline State Manager - Manages persistence and recovery of pipeline state.

This module provides functionality for persisting pipeline state to disk,
handling state versioning, backup, and recovery.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    IFlowError,
    PipelineError,
    FileError,
    BackupError,
    ErrorCode,
    ErrorCategory
)
from .backup_manager import BackupManager
from .file_lock import FileLock
from .state_validator import StateValidator


class PipelineStateManager:
    """Manages pipeline state persistence and recovery."""
    
    def __init__(
        self,
        repo_root: Path,
        pipeline_name: str,
        feature_name: str
    ):
        """Initialize the pipeline state manager.

        Args:
            repo_root: Path to the repository root
            pipeline_name: Name of the pipeline
            feature_name: Name of the feature/branch
        """
        self.repo_root = repo_root
        self.pipeline_name = pipeline_name
        self.feature_name = feature_name
        
        # State directory
        self.state_dir = repo_root / '.iflow' / 'skills' / '.shared-state' / 'pipelines'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # State file
        safe_feature_name = self._sanitize_name(feature_name)
        self.state_file = self.state_dir / f"{pipeline_name}_{safe_feature_name}.json"
        
        # Backup manager
        self.backup_manager = BackupManager(
            state_dir=self.state_dir,
            max_backups=10
        )
        
        # State validator
        self.validator = StateValidator()
        
        # Current state
        self.current_state: Optional[Dict[str, Any]] = None
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in filenames."""
        # Replace special characters with underscores
        return ''.join(c if c.isalnum() else '_' for c in name)
    
    def save_state(
        self,
        state: Dict[str, Any],
        create_backup: bool = True
    ) -> Tuple[int, str]:
        """Save pipeline state to disk.
        
        Args:
            state: The pipeline state to save
            create_backup: Whether to create a backup before saving
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            # Validate state
            is_valid, errors = self._validate_state(state)
            if not is_valid:
                return 1, f"State validation failed: {errors}"
            
            # Create backup if requested
            if create_backup and self.state_file.exists():
                code, output = self.backup_manager.create_backup(self.state_file)
                if code != 0:
                    return code, f"Failed to create backup: {output}"
            
            # Write state with file locking
            with FileLock(self.state_file, timeout=30) as lock:
                # Add metadata
                state["_metadata"] = {
                    "saved_at": datetime.now().isoformat(),
                    "pipeline_name": self.pipeline_name,
                    "feature_name": self.feature_name,
                    "version": "1.0"
                }
                
                with open(self.state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
                self.current_state = state
            
            return 0, f"Pipeline state saved to: {self.state_file}"
        
        except FileError as e:
            return 1, f"File operation failed: {e.message}"
        except BackupError as e:
            return 1, f"Backup operation failed: {e.message}"
        except Exception as e:
            return 1, f"Failed to save state: {str(e)}"
    
    def load_state(self) -> Tuple[int, str, Optional[Dict[str, Any]]]:
        """Load pipeline state from disk.
        
        Returns:
            Tuple of (exit_code, output_message, state_dict)
        """
        try:
            if not self.state_file.exists():
                return 1, f"Pipeline state file not found: {self.state_file}", None
            
            # Read state with file locking
            with FileLock(self.state_file, mode='r', timeout=30) as lock:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
            
            # Validate state
            is_valid, errors = self._validate_state(state)
            if not is_valid:
                return 1, f"State validation failed: {errors}", None
            
            # Verify pipeline and feature names
            metadata = state.get("_metadata", {})
            if metadata.get("pipeline_name") != self.pipeline_name:
                return 1, f"Pipeline name mismatch: expected {self.pipeline_name}, got {metadata.get('pipeline_name')}", None
            
            if metadata.get("feature_name") != self.feature_name:
                return 1, f"Feature name mismatch: expected {self.feature_name}, got {metadata.get('feature_name')}", None
            
            self.current_state = state
            
            return 0, f"Pipeline state loaded from: {self.state_file}", state
        
        except FileError as e:
            return 1, f"File operation failed: {e.message}", None
        except json.JSONDecodeError as e:
            return 1, f"Invalid JSON in state file: {str(e)}", None
        except Exception as e:
            return 1, f"Failed to load state: {str(e)}", None
    
    def delete_state(self, create_backup: bool = True) -> Tuple[int, str]:
        """Delete pipeline state.
        
        Args:
            create_backup: Whether to create a backup before deleting
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            if not self.state_file.exists():
                return 0, "Pipeline state file does not exist."
            
            # Create backup if requested
            if create_backup:
                code, output = self.backup_manager.create_backup(self.state_file)
                if code != 0:
                    return code, f"Failed to create backup: {output}"
            
            # Delete state file
            self.state_file.unlink()
            
            self.current_state = None
            
            return 0, f"Pipeline state deleted: {self.state_file}"
        
        except FileError as e:
            return 1, f"File operation failed: {e.message}"
        except BackupError as e:
            return 1, f"Backup operation failed: {e.message}"
        except Exception as e:
            return 1, f"Failed to delete state: {str(e)}"
    
    def restore_backup(self, backup_index: int = 0) -> Tuple[int, str]:
        """Restore pipeline state from backup.
        
        Args:
            backup_index: Index of the backup to restore (0 = most recent)
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            code, output = self.backup_manager.restore_backup(self.state_file, backup_index)
            
            if code == 0:
                # Reload the restored state
                code2, output2, state = self.load_state()
                if code2 != 0:
                    return code2, f"Restored but failed to load: {output2}"
            
            return code, output
        
        except BackupError as e:
            return 1, f"Backup operation failed: {e.message}"
        except Exception as e:
            return 1, f"Failed to restore backup: {str(e)}"
    
    def list_backups(self) -> Tuple[int, str, List[Dict[str, Any]]]:
        """List available backups for this pipeline.
        
        Returns:
            Tuple of (exit_code, output_message, backup_list)
        """
        try:
            backups = self.backup_manager.list_backups(self.state_file)
            
            if not backups:
                return 0, "No backups available.", []
            
            output = [f"Found {len(backups)} backup(s):"]
            for i, backup in enumerate(backups):
                output.append(f"  {i}: {backup['timestamp']}")
            
            return 0, "\n".join(output), backups
        
        except BackupError as e:
            return 1, f"Backup operation failed: {e.message}", []
        except Exception as e:
            return 1, f"Failed to list backups: {str(e)}", []
    
    def get_state_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of state changes.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of history entries
        """
        history = []
        
        try:
            # Get all backups
            backups = self.backup_manager.list_backups(self.state_file)
            
            for backup in backups[:limit]:
                try:
                    # Load backup state
                    with open(backup['path'], 'r') as f:
                        state = json.load(f)
                    
                    history.append({
                        "timestamp": backup['timestamp'],
                        "status": state.get("status"),
                        "progress": state.get("progress", 0),
                        "current_stage": state.get("current_stage", 0),
                        "total_stages": len(state.get("stages", [])),
                        "path": backup['path']
                    })
                except Exception as e:
                    # Skip corrupted backups
                    self.logger.warning(f"Skipping corrupted backup: {e}")
                    continue
        
        except Exception as e:
            # Return empty list on error
            self.logger.warning(f"Error loading backup history: {e}")
            pass
        
        return history
    
    def compare_states(self, other_state: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current state with another state.
        
        Args:
            other_state: The state to compare against
            
        Returns:
            Dictionary of differences
        """
        if not self.current_state:
            return {
                "error": "No current state loaded"
            }
        
        differences = {
            "status": {
                "current": self.current_state.get("status"),
                "other": other_state.get("status"),
                "changed": self.current_state.get("status") != other_state.get("status")
            },
            "current_stage": {
                "current": self.current_state.get("current_stage"),
                "other": other_state.get("current_stage"),
                "changed": self.current_state.get("current_stage") != other_state.get("current_stage")
            },
            "stages": []
        }
        
        # Compare stages
        current_stages = self.current_state.get("stages", [])
        other_stages = other_state.get("stages", [])
        
        for i in range(max(len(current_stages), len(other_stages))):
            if i < len(current_stages) and i < len(other_stages):
                current_stage = current_stages[i]
                other_stage = other_stages[i]
                
                stage_diff = {
                    "order": current_stage.get("order"),
                    "status": {
                        "current": current_stage.get("status"),
                        "other": other_stage.get("status"),
                        "changed": current_stage.get("status") != other_stage.get("status")
                    }
                }
                
                differences["stages"].append(stage_diff)
        
        return differences
    
    def _validate_state(self, state: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """Validate pipeline state structure.
        
        Args:
            state: The state to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        required_fields = ["pipeline_name", "feature_name", "status", "stages"]
        for field in required_fields:
            if field not in state:
                errors.append(f"Missing required field: {field}")
        
        # Validate status
        valid_statuses = ["pending", "running", "paused", "completed", "failed", "cancelled"]
        if "status" in state and state["status"] not in valid_statuses:
            errors.append(f"Invalid status: {state['status']}")
        
        # Validate stages
        if "stages" in state:
            if not isinstance(state["stages"], list):
                errors.append("Stages must be a list")
            else:
                for i, stage in enumerate(state["stages"]):
                    if not isinstance(stage, dict):
                        errors.append(f"Stage {i} must be a dictionary")
                        continue
                    
                    if "name" not in stage:
                        errors.append(f"Stage {i} missing 'name' field")
                    
                    if "status" not in stage:
                        errors.append(f"Stage {i} missing 'status' field")
        
        return (len(errors) == 0, errors if errors else None)
    
    def export_state(self, export_path: Path) -> Tuple[int, str]:
        """Export pipeline state to a file.
        
        Args:
            export_path: Path to export the state to
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            if not self.current_state:
                return 1, "No state loaded to export."
            
            # Ensure export directory exists
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write export
            with open(export_path, 'w') as f:
                json.dump(self.current_state, f, indent=2)
            
            return 0, f"Pipeline state exported to: {export_path}"
        
        except Exception as e:
            return 1, f"Failed to export state: {str(e)}"
    
    def import_state(self, import_path: Path, replace: bool = False) -> Tuple[int, str]:
        """Import pipeline state from a file.
        
        Args:
            import_path: Path to import the state from
            replace: Whether to replace existing state
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            if not import_path.exists():
                return 1, f"Import file not found: {import_path}"
            
            # Read imported state
            with open(import_path, 'r') as f:
                imported_state = json.load(f)
            
            # Validate imported state
            is_valid, errors = self._validate_state(imported_state)
            if not is_valid:
                return 1, f"Imported state validation failed: {errors}"
            
            # Check if state already exists
            if self.state_file.exists() and not replace:
                return 1, f"State file already exists. Use replace=True to overwrite."
            
            # Save imported state
            return self.save_state(imported_state, create_backup=True)
        
        except json.JSONDecodeError as e:
            return 1, f"Invalid JSON in import file: {str(e)}"
        except Exception as e:
            return 1, f"Failed to import state: {str(e)}"


def create_pipeline_state_manager(
    repo_root: Path,
    pipeline_name: str,
    feature_name: str
) -> PipelineStateManager:
    """Create a pipeline state manager instance."""
    return PipelineStateManager(
        repo_root=repo_root,
        pipeline_name=pipeline_name,
        feature_name=feature_name
    )