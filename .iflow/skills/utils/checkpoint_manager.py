"""Checkpoint Manager - Manages workflow checkpoints for resumption.

This module provides functionality for creating, restoring, and managing
workflow checkpoints to enable resumption from specific points in time.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum
import hashlib
import shutil

from .exceptions import IFlowError, ErrorCode, ErrorCategory
from .backup_manager import BackupManager
from .state_validator import StateValidator
from .constants import BackupConstants


class CheckpointStatus(Enum):
    """Status of a checkpoint."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CORRUPTED = "corrupted"
    DELETED = "deleted"


class Checkpoint:
    """Represents a workflow checkpoint."""
    
    def __init__(
        self,
        checkpoint_id: str,
        name: str,
        timestamp: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a checkpoint.
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            name: Human-readable name for the checkpoint
            timestamp: ISO format timestamp when checkpoint was created
            state_data: Complete state snapshot
            metadata: Additional metadata about the checkpoint
        """
        self.checkpoint_id = checkpoint_id
        self.name = name
        self.timestamp = timestamp
        self.state_data = state_data
        self.metadata = metadata or {}
        self.status = CheckpointStatus.ACTIVE
        self.size_bytes = len(json.dumps(state_data).encode('utf-8'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata
        }


class CheckpointManager:
    """Manages workflow checkpoints."""
    
    def __init__(
        self,
        repo_root: Path,
        checkpoint_dir: Optional[Path] = None,
        max_checkpoints: int = 20
    ):
        """
        Initialize the checkpoint manager.
        
        Args:
            repo_root: Repository root directory
            checkpoint_dir: Directory for storing checkpoints
            max_checkpoints: Maximum number of checkpoints to keep
        """
        self.repo_root = repo_root
        self.checkpoint_dir = checkpoint_dir or (repo_root / ".iflow" / "checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        self.index_file = self.checkpoint_dir / "index.json"
        self.backup_manager = BackupManager(repo_root)
        self.state_validator = StateValidator()
        self.checkpoints: Dict[str, Checkpoint] = {}
        self._load_index()
    
    def _load_index(self):
        """Load the checkpoint index from file."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    index_data = json.load(f)
                
                for cp_data in index_data.get("checkpoints", []):
                    checkpoint = Checkpoint(
                        checkpoint_id=cp_data["checkpoint_id"],
                        name=cp_data["name"],
                        timestamp=cp_data["timestamp"],
                        state_data={},  # Load state separately
                        metadata=cp_data.get("metadata", {})
                    )
                    checkpoint.status = CheckpointStatus(cp_data.get("status", "active"))
                    self.checkpoints[checkpoint.checkpoint_id] = checkpoint
            
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_index(self):
        """Save the checkpoint index to file."""
        index_data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_checkpoints": len(self.checkpoints),
            "checkpoints": [cp.to_dict() for cp in self.checkpoints.values()]
        }
        
        try:
            with open(self.index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save checkpoint index: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _generate_checkpoint_id(self, name: str) -> str:
        """Generate a unique checkpoint ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{name}_{timestamp}".encode('utf-8')
        hash_suffix = hashlib.md5(hash_input).hexdigest()[:8]
        return f"cp_{timestamp}_{hash_suffix}"
    
    def create_checkpoint(
        self,
        name: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Checkpoint:
        """
        Create a new checkpoint.
        
        Args:
            name: Human-readable name for the checkpoint
            state_data: Complete state snapshot to save
            metadata: Additional metadata about the checkpoint
            tags: Optional tags for categorization
            
        Returns:
            Created Checkpoint object
        """
        checkpoint_id = self._generate_checkpoint_id(name)
        timestamp = datetime.now().isoformat()
        
        # Create checkpoint object
        metadata = metadata or {}
        if tags:
            metadata["tags"] = tags
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            name=name,
            timestamp=timestamp,
            state_data=state_data,
            metadata=metadata
        )
        
        # Save checkpoint state to file
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save checkpoint data: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
        
        # Add to index
        self.checkpoints[checkpoint_id] = checkpoint
        
        # Enforce max checkpoints limit
        self._enforce_limit()
        
        # Save index
        self._save_index()
        
        return checkpoint
    
    def restore_checkpoint(
        self,
        checkpoint_id: str,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Restore state from a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to restore
            validate: Whether to validate the restored state
            
        Returns:
            Restored state data
            
        Raises:
            IFlowError: If checkpoint not found or validation fails
        """
        if checkpoint_id not in self.checkpoints:
            raise IFlowError(
                f"Checkpoint '{checkpoint_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        if checkpoint.status == CheckpointStatus.CORRUPTED:
            raise IFlowError(
                f"Checkpoint '{checkpoint_id}' is corrupted",
                ErrorCode.CORRUPTED_DATA
            )
        
        if checkpoint.status == CheckpointStatus.DELETED:
            raise IFlowError(
                f"Checkpoint '{checkpoint_id}' has been deleted",
                ErrorCode.NOT_FOUND
            )
        
        # Load checkpoint state from file
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        try:
            with open(checkpoint_file, 'r') as f:
                state_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            checkpoint.status = CheckpointStatus.CORRUPTED
            self._save_index()
            raise IFlowError(
                f"Failed to load checkpoint data: {str(e)}",
                ErrorCode.CORRUPTED_DATA
            )
        
        # Validate state if requested
        if validate:
            is_valid, errors = self.state_validator.validate_state(state_data)
            if not is_valid:
                raise IFlowError(
                    f"Checkpoint state validation failed: {errors}",
                    ErrorCode.VALIDATION_ERROR
                )
        
        return state_data
    
    def delete_checkpoint(
        self,
        checkpoint_id: str,
        keep_metadata: bool = False
    ):
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to delete
            keep_metadata: Whether to keep metadata in index (mark as deleted)
        """
        if checkpoint_id not in self.checkpoints:
            raise IFlowError(
                f"Checkpoint '{checkpoint_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        # Delete checkpoint file
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            try:
                checkpoint_file.unlink()
            except IOError as e:
                raise IFlowError(
                    f"Failed to delete checkpoint file: {str(e)}",
                    ErrorCode.FILE_DELETE_ERROR
                )
        
        if keep_metadata:
            # Mark as deleted but keep in index
            checkpoint.status = CheckpointStatus.DELETED
        else:
            # Remove from index
            del self.checkpoints[checkpoint_id]
        
        self._save_index()
    
    def archive_checkpoint(self, checkpoint_id: str):
        """
        Archive a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to archive
        """
        if checkpoint_id not in self.checkpoints:
            raise IFlowError(
                f"Checkpoint '{checkpoint_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        checkpoint = self.checkpoints[checkpoint_id]
        checkpoint.status = CheckpointStatus.ARCHIVED
        self._save_index()
    
    def list_checkpoints(
        self,
        status: Optional[CheckpointStatus] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Checkpoint]:
        """
        List checkpoints with optional filtering.
        
        Args:
            status: Optional status filter
            tags: Optional tag filter
            limit: Optional maximum number to return
            
        Returns:
            List of checkpoints
        """
        checkpoints = list(self.checkpoints.values())
        
        # Filter by status
        if status:
            checkpoints = [cp for cp in checkpoints if cp.status == status]
        
        # Filter by tags
        if tags:
            checkpoints = [
                cp for cp in checkpoints
                if any(tag in cp.metadata.get("tags", []) for tag in tags)
            ]
        
        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda cp: cp.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            checkpoints = checkpoints[:limit]
        
        return checkpoints
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Get a checkpoint by ID.
        
        Args:
            checkpoint_id: ID of checkpoint
            
        Returns:
            Checkpoint object or None if not found
        """
        return self.checkpoints.get(checkpoint_id)
    
    def find_latest_checkpoint(
        self,
        tags: Optional[List[str]] = None
    ) -> Optional[Checkpoint]:
        """
        Find the latest checkpoint.
        
        Args:
            tags: Optional tag filter
            
        Returns:
            Latest checkpoint or None
        """
        checkpoints = self.list_checkpoints(
            status=CheckpointStatus.ACTIVE,
            tags=tags,
            limit=1
        )
        return checkpoints[0] if checkpoints else None
    
    def _enforce_limit(self):
        """Enforce maximum checkpoint limit by deleting oldest."""
        active_checkpoints = [
            cp for cp in self.checkpoints.values()
            if cp.status == CheckpointStatus.ACTIVE
        ]
        
        if len(active_checkpoints) > self.max_checkpoints:
            # Sort by timestamp (oldest first)
            active_checkpoints.sort(key=lambda cp: cp.timestamp)
            
            # Delete oldest checkpoints
            to_delete = len(active_checkpoints) - self.max_checkpoints
            for checkpoint in active_checkpoints[:to_delete]:
                try:
                    self.delete_checkpoint(checkpoint.checkpoint_id, keep_metadata=False)
                except IFlowError:
                    pass  # Ignore deletion errors
    
    def cleanup_old_checkpoints(self, days: int = 30) -> int:
        """
        Delete checkpoints older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of checkpoints deleted
        """
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        deleted = 0
        
        checkpoints_to_delete = []
        for checkpoint_id, checkpoint in self.checkpoints.items():
            try:
                checkpoint_time = datetime.fromisoformat(checkpoint.timestamp).timestamp()
                if checkpoint_time < cutoff_time and checkpoint.status == CheckpointStatus.ACTIVE:
                    checkpoints_to_delete.append(checkpoint_id)
            except ValueError:
                pass
        
        for checkpoint_id in checkpoints_to_delete:
            try:
                self.delete_checkpoint(checkpoint_id, keep_metadata=False)
                deleted += 1
            except IFlowError:
                pass
        
        return deleted
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get checkpoint statistics.
        
        Returns:
            Dictionary with statistics
        """
        status_counts = {}
        total_size = 0
        
        for checkpoint in self.checkpoints.values():
            status = checkpoint.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            total_size += checkpoint.size_bytes
        
        return {
            "total_checkpoints": len(self.checkpoints),
            "active_checkpoints": status_counts.get("active", 0),
            "archived_checkpoints": status_counts.get("archived", 0),
            "corrupted_checkpoints": status_counts.get("corrupted", 0),
            "deleted_checkpoints": status_counts.get("deleted", 0),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_checkpoints": self.max_checkpoints
        }
    
    def export_checkpoint(
        self,
        checkpoint_id: str,
        output_file: Path
    ):
        """
        Export a checkpoint to a file.
        
        Args:
            checkpoint_id: ID of checkpoint to export
            output_file: Path to export file
        """
        state_data = self.restore_checkpoint(checkpoint_id, validate=False)
        
        try:
            with open(output_file, 'w') as f:
                json.dump(state_data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to export checkpoint: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def import_checkpoint(
        self,
        input_file: Path,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        """
        Import a checkpoint from a file.
        
        Args:
            input_file: Path to import file
            name: Name for the imported checkpoint
            metadata: Additional metadata
            
        Returns:
            Created Checkpoint object
        """
        try:
            with open(input_file, 'r') as f:
                state_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise IFlowError(
                f"Failed to import checkpoint: {str(e)}",
                ErrorCode.FILE_READ_ERROR
            )
        
        return self.create_checkpoint(name, state_data, metadata)


def create_checkpoint_manager(
    repo_root: Path,
    checkpoint_dir: Optional[Path] = None,
    max_checkpoints: int = 20
) -> CheckpointManager:
    """Create a checkpoint manager instance."""
    return CheckpointManager(
        repo_root=repo_root,
        checkpoint_dir=checkpoint_dir,
        max_checkpoints=max_checkpoints
    )