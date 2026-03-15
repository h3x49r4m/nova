#!/usr/bin/env python3
"""
Git-Flow Checkpoint Module
Handles checkpoint creation, restoration, and management.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from utils import (
    run_git_command,
    StructuredLogger,
    LogFormat,
    LogLevel
)
from .git_flow_config import GitFlowConfig


class GitFlowCheckpoint:
    """Manages Git-Flow checkpoint operations."""
    
    def __init__(self, config: GitFlowConfig):
        """
        Initialize checkpoint manager.
        
        Args:
            config: GitFlowConfig instance
        """
        self.config = config
        self.logger = config.logger
        self.repo_root = config.repo_root
        self.checkpoints_dir = self.repo_root / '.iflow' / 'checkpoints'
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    
    def create_checkpoint(
        self,
        checkpoint_id: Optional[str] = None,
        description: Optional[str] = None,
        include_state: bool = True
    ) -> Tuple[int, str]:
        """
        Create a checkpoint of the current workflow state.
        
        Args:
            checkpoint_id: Optional checkpoint ID (auto-generated if not provided)
            description: Optional checkpoint description
            include_state: If True, include workflow state files
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Generate checkpoint ID if not provided
            if not checkpoint_id:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                checkpoint_id = f"checkpoint_{timestamp}"
            
            # Create checkpoint directory
            checkpoint_dir = self.checkpoints_dir / checkpoint_id
            checkpoint_dir.mkdir(exist_ok=True)
            
            # Create checkpoint metadata
            metadata = {
                'id': checkpoint_id,
                'created_at': datetime.now().isoformat(),
                'description': description or f"Checkpoint created at {datetime.now()}",
                'branch': self._get_current_branch(),
                'commit': self._get_current_commit(),
                'workflow_state': None
            }
            
            # Include workflow state if requested
            if include_state and self.config.workflow_state:
                metadata['workflow_state'] = self.config.workflow_state.to_dict()
                
                # Copy state files
                state_files = [
                    self.config.workflow_state_file,
                    self.config.branch_states_file
                ]
                
                for state_file in state_files:
                    if state_file.exists():
                        dest = checkpoint_dir / state_file.name
                        shutil.copy2(state_file, dest)
            
            # Save metadata
            metadata_file = checkpoint_dir / 'metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            message = f"Created checkpoint '{checkpoint_id}'"
            if description:
                message += f"\nDescription: {description}"
            
            self.logger.info(f"Created checkpoint '{checkpoint_id}'")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error creating checkpoint: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def restore_checkpoint(self, checkpoint_id: str) -> Tuple[int, str]:
        """
        Restore a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID to restore
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            checkpoint_dir = self.checkpoints_dir / checkpoint_id
            
            if not checkpoint_dir.exists():
                return (1, f"Checkpoint '{checkpoint_id}' not found")
            
            # Load metadata
            metadata_file = checkpoint_dir / 'metadata.json'
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Checkout the commit from checkpoint
            commit = metadata.get('commit')
            if commit:
                code, stdout, stderr = run_git_command(
                    ['checkout', commit],
                    cwd=self.repo_root
                )
                
                if code != 0:
                    return (code, f"Failed to checkout commit: {stderr}")
            
            # Restore state files if they exist
            state_files = [
                self.config.workflow_state_file,
                self.config.branch_states_file
            ]
            
            for state_file in state_files:
                src = checkpoint_dir / state_file.name
                if src.exists():
                    shutil.copy2(src, state_file)
            
            # Reload configuration and state
            self.config.load_workflow_state()
            self.config.load_branch_states()
            
            message = f"Restored checkpoint '{checkpoint_id}'"
            self.logger.info(message)
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error restoring checkpoint: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def list_checkpoints(self) -> Tuple[int, str]:
        """
        List all available checkpoints.
        
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            checkpoints = []
            
            for checkpoint_dir in self.checkpoints_dir.iterdir():
                if not checkpoint_dir.is_dir():
                    continue
                
                metadata_file = checkpoint_dir / 'metadata.json'
                if not metadata_file.exists():
                    continue
                
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                checkpoints.append({
                    'id': checkpoint_dir.name,
                    'created_at': metadata.get('created_at'),
                    'description': metadata.get('description'),
                    'branch': metadata.get('branch'),
                    'commit': metadata.get('commit')
                })
            
            # Sort by creation time (newest first)
            checkpoints.sort(key=lambda x: x['created_at'], reverse=True)
            
            if not checkpoints:
                return (0, "No checkpoints found")
            
            # Format output
            message = f"Found {len(checkpoints)} checkpoints:\n\n"
            for cp in checkpoints:
                message += f"ID: {cp['id']}\n"
                message += f"  Created: {cp['created_at']}\n"
                message += f"  Branch: {cp['branch']}\n"
                message += f"  Commit: {cp['commit']}\n"
                if cp['description']:
                    message += f"  Description: {cp['description']}\n"
                message += "\n"
            
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error listing checkpoints: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def delete_checkpoint(self, checkpoint_id: str) -> Tuple[int, str]:
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID to delete
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            checkpoint_dir = self.checkpoints_dir / checkpoint_id
            
            if not checkpoint_dir.exists():
                return (1, f"Checkpoint '{checkpoint_id}' not found")
            
            # Delete checkpoint directory
            shutil.rmtree(checkpoint_dir)
            
            message = f"Deleted checkpoint '{checkpoint_id}'"
            self.logger.info(message)
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error deleting checkpoint: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def get_checkpoint_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about checkpoints.
        
        Returns:
            Dictionary with checkpoint statistics
        """
        try:
            checkpoints = list(self.checkpoints_dir.iterdir())
            checkpoints = [cp for cp in checkpoints if cp.is_dir()]
            
            total_size = sum(
                sum(f.stat().st_size for f in cp.rglob('*') if f.is_file())
                for cp in checkpoints
            )
            
            return {
                'total_checkpoints': len(checkpoints),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_checkpoint': self._get_oldest_checkpoint(checkpoints),
                'newest_checkpoint': self._get_newest_checkpoint(checkpoints)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting checkpoint statistics: {e}")
            return {
                'total_checkpoints': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'oldest_checkpoint': None,
                'newest_checkpoint': None
            }
    
    def cleanup_old_checkpoints(self, max_age_days: int = 30, max_count: int = 10) -> Tuple[int, List[str]]:
        """
        Clean up old checkpoints based on age and count.
        
        Args:
            max_age_days: Maximum age of checkpoints to keep
            max_count: Maximum number of checkpoints to keep
            
        Returns:
            Tuple of (count_deleted, list of deleted checkpoint IDs)
        """
        try:
            deleted = []
            checkpoints = []
            
            # Collect all checkpoints with metadata
            for checkpoint_dir in self.checkpoints_dir.iterdir():
                if not checkpoint_dir.is_dir():
                    continue
                
                metadata_file = checkpoint_dir / 'metadata.json'
                if not metadata_file.exists():
                    continue
                
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                created_at = datetime.fromisoformat(metadata.get('created_at'))
                age_days = (datetime.now() - created_at).days
                
                checkpoints.append({
                    'id': checkpoint_dir.name,
                    'created_at': created_at,
                    'age_days': age_days
                })
            
            # Sort by age (oldest first)
            checkpoints.sort(key=lambda x: x['created_at'])
            
            # Delete old checkpoints
            for cp in checkpoints:
                if cp['age_days'] > max_age_days or len(checkpoints) - len(deleted) > max_count:
                    code, msg = self.delete_checkpoint(cp['id'])
                    if code == 0:
                        deleted.append(cp['id'])
            
            message = f"Cleaned up {len(deleted)} old checkpoints"
            self.logger.info(message)
            return (len(deleted), deleted)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up checkpoints: {e}")
            return (0, [])
    
    def _get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            code, stdout, stderr = run_git_command(
                ['rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.repo_root
            )
            if code == 0:
                return stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_current_commit(self) -> str:
        """Get current commit hash."""
        try:
            code, stdout, stderr = run_git_command(
                ['rev-parse', 'HEAD'],
                cwd=self.repo_root
            )
            if code == 0:
                return stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_oldest_checkpoint(self, checkpoints: List[Path]) -> Optional[str]:
        """Get the oldest checkpoint ID."""
        if not checkpoints:
            return None
        
        oldest = None
        oldest_time = None
        
        for checkpoint_dir in checkpoints:
            metadata_file = checkpoint_dir / 'metadata.json'
            if not metadata_file.exists():
                continue
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            created_at = datetime.fromisoformat(metadata.get('created_at'))
            
            if oldest_time is None or created_at < oldest_time:
                oldest_time = created_at
                oldest = checkpoint_dir.name
        
        return oldest
    
    def _get_newest_checkpoint(self, checkpoints: List[Path]) -> Optional[str]:
        """Get the newest checkpoint ID."""
        if not checkpoints:
            return None
        
        newest = None
        newest_time = None
        
        for checkpoint_dir in checkpoints:
            metadata_file = checkpoint_dir / 'metadata.json'
            if not metadata_file.exists():
                continue
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            created_at = datetime.fromisoformat(metadata.get('created_at'))
            
            if newest_time is None or created_at > newest_time:
                newest_time = created_at
                newest = checkpoint_dir.name
        
        return newest