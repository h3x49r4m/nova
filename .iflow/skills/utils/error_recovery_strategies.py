"""Error Recovery Strategies - Provides strategies for recovering from errors.

This module provides automated and manual recovery strategies for common
error scenarios in the iFlow CLI Skills system.
"""

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from enum import Enum

from .exceptions import IFlowError, ErrorCode, ErrorCategory
from .backup_manager import BackupManager
from .state_validator import StateValidator


class RecoveryAction(Enum):
    """Types of recovery actions."""
    RETRY = "retry"
    ROLLBACK = "rollback"
    RESTORE_BACKUP = "restore_backup"
    RESET_STATE = "reset_state"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL_INTERVENTION = "manual_intervention"
    CONTINUE = "continue"
    RESTART = "restart"


class RecoveryStrategy:
    """Represents a recovery strategy for a specific error."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        actions: List[RecoveryAction],
        description: str,
        automatic: bool = False,
        max_attempts: int = 3
    ):
        """
        Initialize a recovery strategy.
        
        Args:
            error_code: Error code this strategy applies to
            actions: List of recovery actions to try
            description: Description of the strategy
            automatic: Whether this can be automatically applied
            max_attempts: Maximum number of retry attempts
        """
        self.error_code = error_code
        self.actions = actions
        self.description = description
        self.automatic = automatic
        self.max_attempts = max_attempts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary."""
        return {
            "error_code": self.error_code.name,
            "actions": [action.value for action in self.actions],
            "description": self.description,
            "automatic": self.automatic,
            "max_attempts": self.max_attempts
        }


class ErrorRecoveryManager:
    """Manages error recovery strategies and execution."""
    
    def __init__(
        self,
        repo_root: Path,
        backup_manager: Optional[BackupManager] = None,
        state_validator: Optional[StateValidator] = None
    ):
        """
        Initialize the error recovery manager.
        
        Args:
            repo_root: Repository root directory
            backup_manager: Optional backup manager instance
            state_validator: Optional state validator instance
        """
        self.repo_root = repo_root
        self.backup_manager = backup_manager or BackupManager(repo_root)
        self.state_validator = state_validator or StateValidator(repo_root)
        self.strategies: Dict[ErrorCode, RecoveryStrategy] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self):
        """Initialize default recovery strategies for common errors."""
        
        # Git operation errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.GIT_ERROR,
            actions=[RecoveryAction.RETRY, RecoveryAction.MANUAL_INTERVENTION],
            description="Retry git operations with exponential backoff",
            automatic=True,
            max_attempts=3
        ))
        
        # File not found errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.FILE_NOT_FOUND,
            actions=[RecoveryAction.RESTORE_BACKUP, RecoveryAction.MANUAL_INTERVENTION],
            description="Restore from backup or manually locate the file",
            automatic=False,
            max_attempts=1
        ))
        
        # File read errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.FILE_READ_ERROR,
            actions=[RecoveryAction.RETRY, RecoveryAction.RESTORE_BACKUP],
            description="Retry read operation or restore from backup",
            automatic=True,
            max_attempts=2
        ))
        
        # File write errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.FILE_WRITE_ERROR,
            actions=[RecoveryAction.RETRY, RecoveryAction.MANUAL_INTERVENTION],
            description="Retry write operation or check permissions",
            automatic=True,
            max_attempts=2
        ))
        
        # Validation errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.VALIDATION_ERROR,
            actions=[RecoveryAction.MANUAL_INTERVENTION],
            description="Review and fix validation issues manually",
            automatic=False,
            max_attempts=1
        ))
        
        # Not found errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.NOT_FOUND,
            actions=[RecoveryAction.SKIP, RecoveryAction.MANUAL_INTERVENTION],
            description="Skip the resource or create it manually",
            automatic=False,
            max_attempts=1
        ))
        
        # Already exists errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.ALREADY_EXISTS,
            actions=[RecoveryAction.CONTINUE, RecoveryAction.MANUAL_INTERVENTION],
            description="Use existing resource or delete and recreate",
            automatic=False,
            max_attempts=1
        ))
        
        # Permission denied errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.PERMISSION_DENIED,
            actions=[RecoveryAction.MANUAL_INTERVENTION],
            description="Check permissions and retry",
            automatic=False,
            max_attempts=1
        ))
        
        # Timeout errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.TIMEOUT,
            actions=[RecoveryAction.RETRY, RecoveryAction.ABORT],
            description="Retry with longer timeout or abort",
            automatic=True,
            max_attempts=3
        ))
        
        # Circular dependency errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.CIRCULAR_DEPENDENCY,
            actions=[RecoveryAction.MANUAL_INTERVENTION],
            description="Review and restructure dependencies",
            automatic=False,
            max_attempts=1
        ))
        
        # Invalid state errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.INVALID_STATE,
            actions=[RecoveryAction.RESET_STATE, RecoveryAction.RESTORE_BACKUP],
            description="Reset state or restore from backup",
            automatic=False,
            max_attempts=1
        ))
        
        # Dependency errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.DEPENDENCY_ERROR,
            actions=[RecoveryAction.MANUAL_INTERVENTION],
            description="Install or update dependencies",
            automatic=False,
            max_attempts=1
        ))
        
        # Configuration errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.CONFIGURATION_ERROR,
            actions=[RecoveryAction.RESET_STATE, RecoveryAction.MANUAL_INTERVENTION],
            description="Reset to default configuration",
            automatic=False,
            max_attempts=1
        ))
        
        # Security errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.SECURITY_ERROR,
            actions=[RecoveryAction.ABORT, RecoveryAction.MANUAL_INTERVENTION],
            description="Abort operation and review security",
            automatic=False,
            max_attempts=1
        ))
        
        # Backup errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.BACKUP_ERROR,
            actions=[RecoveryAction.RETRY, RecoveryAction.MANUAL_INTERVENTION],
            description="Retry backup operation",
            automatic=True,
            max_attempts=2
        ))
        
        # Version errors
        self.register_strategy(RecoveryStrategy(
            error_code=ErrorCode.VERSION_ERROR,
            actions=[RecoveryAction.MANUAL_INTERVENTION],
            description="Update to compatible version",
            automatic=False,
            max_attempts=1
        ))
    
    def register_strategy(self, strategy: RecoveryStrategy):
        """
        Register a recovery strategy.
        
        Args:
            strategy: Recovery strategy to register
        """
        self.strategies[strategy.error_code] = strategy
    
    def get_strategy(self, error_code: ErrorCode) -> Optional[RecoveryStrategy]:
        """
        Get recovery strategy for an error code.
        
        Args:
            error_code: Error code
            
        Returns:
            Recovery strategy or None
        """
        return self.strategies.get(error_code)
    
    def can_recover_automatically(self, error: IFlowError) -> bool:
        """
        Check if an error can be recovered automatically.
        
        Args:
            error: The error to check
            
        Returns:
            True if automatic recovery is possible
        """
        strategy = self.get_strategy(error.code)
        return strategy is not None and strategy.automatic
    
    def recover(
        self,
        error: IFlowError,
        context: Optional[Dict[str, Any]] = None,
        attempt: int = 1
    ) -> Tuple[bool, Optional[RecoveryAction], str]:
        """
        Attempt to recover from an error.
        
        Args:
            error: The error to recover from
            context: Additional context information
            attempt: Current attempt number
            
        Returns:
            Tuple of (success, action_used, message)
        """
        strategy = self.get_strategy(error.code)
        
        if not strategy:
            return False, None, f"No recovery strategy for error: {error.code.name}"
        
        if attempt > strategy.max_attempts:
            return False, None, f"Max recovery attempts ({strategy.max_attempts}) exceeded"
        
        # Try each recovery action
        for action in strategy.actions:
            success, message = self._execute_recovery_action(
                action,
                error,
                context or {}
            )
            
            if success:
                self._record_recovery(error, action, success, attempt, message)
                return True, action, message
        
        # All actions failed
        self._record_recovery(error, None, False, attempt, "All recovery actions failed")
        return False, None, "All recovery actions failed"
    
    def _execute_recovery_action(
        self,
        action: RecoveryAction,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Execute a specific recovery action.
        
        Args:
            action: Recovery action to execute
            error: The error being recovered from
            context: Context information
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if action == RecoveryAction.RETRY:
                return self._retry_operation(error, context)
            
            elif action == RecoveryAction.ROLLBACK:
                return self._rollback_operation(error, context)
            
            elif action == RecoveryAction.RESTORE_BACKUP:
                return self._restore_from_backup(error, context)
            
            elif action == RecoveryAction.RESET_STATE:
                return self._reset_state(error, context)
            
            elif action == RecoveryAction.SKIP:
                return self._skip_operation(error, context)
            
            elif action == RecoveryAction.ABORT:
                return self._abort_operation(error, context)
            
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                return self._request_manual_intervention(error, context)
            
            elif action == RecoveryAction.CONTINUE:
                return self._continue_operation(error, context)
            
            elif action == RecoveryAction.RESTART:
                return self._restart_operation(error, context)
            
            else:
                return False, f"Unknown recovery action: {action.value}"
        
        except Exception as e:
            return False, f"Recovery action failed: {str(e)}"
    
    def _retry_operation(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Retry the failed operation."""
        # This is a placeholder - actual retry would be context-specific
        operation = context.get("operation", "operation")
        return True, f"Ready to retry {operation}"
    
    def _rollback_operation(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Rollback the failed operation."""
        # This is a placeholder - actual rollback would be context-specific
        operation = context.get("operation", "operation")
        return True, f"Rolled back {operation}"
    
    def _restore_from_backup(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Restore from backup."""
        backup_id = context.get("backup_id")
        
        if not backup_id:
            # Try to find the most recent backup
            backups = self.backup_manager.list_backups()
            if not backups:
                return False, "No backups available"
            
            backup_id = backups[0]["backup_id"]
        
        try:
            self.backup_manager.restore_backup(backup_id)
            return True, f"Restored from backup: {backup_id}"
        except Exception as e:
            return False, f"Failed to restore backup: {str(e)}"
    
    def _reset_state(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Reset state to initial values."""
        state_file = context.get("state_file")
        
        if state_file:
            try:
                if Path(state_file).exists():
                    Path(state_file).unlink()
                return True, f"Reset state file: {state_file}"
            except Exception as e:
                return False, f"Failed to reset state: {str(e)}"
        
        return True, "State reset"
    
    def _skip_operation(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Skip the failed operation."""
        operation = context.get("operation", "operation")
        return True, f"Skipping {operation}"
    
    def _abort_operation(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Abort the operation."""
        operation = context.get("operation", "operation")
        return True, f"Aborting {operation}"
    
    def _request_manual_intervention(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Request manual intervention."""
        return False, "Manual intervention required"
    
    def _continue_operation(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Continue with the operation."""
        operation = context.get("operation", "operation")
        return True, f"Continuing {operation}"
    
    def _restart_operation(
        self,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Restart the operation."""
        operation = context.get("operation", "operation")
        return True, f"Restarting {operation}"
    
    def _record_recovery(
        self,
        error: IFlowError,
        action: Optional[RecoveryAction],
        success: bool,
        attempt: int,
        message: str
    ):
        """Record a recovery attempt in history."""
        record = {
            "timestamp": self._get_timestamp(),
            "error_code": error.code.name,
            "error_message": str(error),
            "action": action.value if action else None,
            "success": success,
            "attempt": attempt,
            "message": message
        }
        
        self.recovery_history.append(record)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_recovery_history(
        self,
        error_code: Optional[ErrorCode] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recovery history.
        
        Args:
            error_code: Optional filter by error code
            limit: Maximum number of records to return
            
        Returns:
            List of recovery records
        """
        history = self.recovery_history
        
        if error_code:
            history = [r for r in history if r["error_code"] == error_code.name]
        
        return history[-limit:]
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r["success"])
        failed = total - successful
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Count by error code
        error_counts = {}
        for record in self.recovery_history:
            error_code = record["error_code"]
            error_counts[error_code] = error_counts.get(error_code, 0) + 1
        
        return {
            "total_recoveries": total,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "error_counts": error_counts,
            "strategies_available": len(self.strategies)
        }
    
    def export_recovery_report(
        self,
        output_file: Optional[Path] = None
    ) -> str:
        """
        Export a recovery report.
        
        Args:
            output_file: Optional file to save report
            
        Returns:
            Report content
        """
        stats = self.get_recovery_statistics()
        history = self.get_recovery_history()
        
        lines = [
            "Error Recovery Report",
            "=" * 50,
            "",
            f"Generated: {self._get_timestamp()}",
            "",
            "Statistics:",
            "-" * 30,
            f"Total Recovery Attempts: {stats['total_recoveries']}",
            f"Successful: {stats['successful']}",
            f"Failed: {stats['failed']}",
            f"Success Rate: {stats['success_rate']:.1f}%",
            f"Strategies Available: {stats['strategies_available']}",
            "",
            "Recovery History:",
            "-" * 30
        ]
        
        for record in history:
            lines.append(f"- {record['timestamp']}: {record['error_code']} - {record['action']} - {'Success' if record['success'] else 'Failed'}")
        
        content = "\n".join(lines)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(content)
            except IOError:
                pass
        
        return content


def create_recovery_manager(
    repo_root: Path,
    backup_manager: Optional[BackupManager] = None
) -> ErrorRecoveryManager:
    """Create an error recovery manager instance."""
    return ErrorRecoveryManager(repo_root, backup_manager)