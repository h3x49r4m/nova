"""Transactional State Manager - Provides ACID-like transactions for state updates.

This module implements transactional state updates to ensure atomicity,
consistency, isolation, and durability when modifying state files.
"""

import json
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from contextlib import contextmanager

from .file_lock import FileLock, FileLockError
from .exceptions import IFlowError, ErrorCode


class TransactionError(IFlowError):
    """Transaction-related errors."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.VALIDATION_FAILED)


class TransactionState(Enum):
    """Transaction states."""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


class StateTransaction:
    """Represents a transaction for state updates."""
    
    def __init__(self, transaction_id: str, state_files: List[Path], temp_dir: Path):
        """
        Initialize state transaction.
        
        Args:
            transaction_id: Unique transaction identifier
            state_files: List of state files involved in transaction
            temp_dir: Temporary directory for transaction backups
        """
        self.transaction_id = transaction_id
        self.state_files = state_files
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.state = TransactionState.ACTIVE
        self.started_at = datetime.now().isoformat()
        self.completed_at: Optional[str] = None
        self.operations: List[Dict[str, Any]] = []
        self.backup_files: Dict[Path, Path] = {}
        
        # Create backups
        self._create_backups()
    
    def _create_backups(self) -> None:
        """Create backups of all state files."""
        for state_file in self.state_files:
            if state_file.exists():
                backup_path = self.temp_dir / f"{state_file.name}.backup"
                shutil.copy2(state_file, backup_path)
                self.backup_files[state_file] = backup_path
    
    def add_operation(
        self,
        operation_type: str,
        file_path: Path,
        old_data: Optional[Any],
        new_data: Optional[Any]
    ) -> None:
        """
        Log an operation performed during the transaction.
        
        Args:
            operation_type: Type of operation (create, update, delete)
            file_path: Path to the file
            old_data: Previous data
            new_data: New data
        """
        self.operations.append({
            "operation_type": operation_type,
            "file_path": str(file_path),
            "old_data": old_data,
            "new_data": new_data,
            "timestamp": datetime.now().isoformat()
        })
    
    def rollback(self) -> None:
        """Rollback the transaction by restoring backups."""
        for state_file, backup_path in self.backup_files.items():
            if backup_path.exists():
                # Restore from backup
                if state_file.exists():
                    state_file.unlink()
                shutil.copy2(backup_path, state_file)
            else:
                # File was created during transaction, delete it
                if state_file.exists():
                    state_file.unlink()
        
        self.state = TransactionState.ROLLED_BACK
        self.completed_at = datetime.now().isoformat()
        
        # Clean up temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def commit(self) -> None:
        """Commit the transaction."""
        self.state = TransactionState.COMMITTED
        self.completed_at = datetime.now().isoformat()
        
        # Clean up temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def get_duration(self) -> str:
        """Get transaction duration."""
        if not self.completed_at:
            return "Not completed"
        
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.completed_at)
        duration = end - start
        
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "state": self.state.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "operations": self.operations,
            "duration": self.get_duration()
        }


class TransactionalStateManager:
    """Manages state updates with transaction support."""
    
    def __init__(self, state_dir: Path):
        """
        Initialize transactional state manager.
        
        Args:
            state_dir: Directory containing state files
        """
        self.state_dir = state_dir
        self.transaction_log_file = state_dir / ".transaction_log.json"
        self.current_transaction: Optional[StateTransaction] = None
        self.transaction_history: List[Dict[str, Any]] = []
        self._load_transaction_log()
    
    def _load_transaction_log(self) -> None:
        """Load transaction log from file."""
        if self.transaction_log_file.exists():
            try:
                with open(self.transaction_log_file, 'r') as f:
                    self.transaction_history = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.transaction_history = []
    
    def _save_transaction_log(self) -> None:
        """Save transaction log to file."""
        try:
            with open(self.transaction_log_file, 'w') as f:
                json.dump(self.transaction_history, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save transaction log: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    @contextmanager
    def transaction(
        self,
        state_files: Optional[List[Path]] = None
    ):
        """
        Context manager for executing a transaction.
        
        Args:
            state_files: List of state files involved in transaction
            
        Yields:
            StateTransaction object
            
        Example:
            with manager.transaction([file1, file2]) as tx:
                # Perform operations
                manager.update_state(file1, new_data)
                manager.update_state(file2, new_data2)
                # Changes are committed automatically on success
                # Or use tx.rollback() on failure
        """
        import uuid
        
        if self.current_transaction:
            raise TransactionError("Nested transactions are not supported")
        
        # Determine state files
        if state_files is None:
            # Include all JSON files in state directory
            state_files = [
                f for f in self.state_dir.iterdir()
                if f.is_file() and f.suffix == '.json' and not f.name.startswith('.')
            ]
        
        # Create transaction
        transaction_id = str(uuid.uuid4())
        temp_dir = self.state_dir / ".transactions" / transaction_id
        transaction = StateTransaction(transaction_id, state_files, temp_dir)
        self.current_transaction = transaction
        
        try:
            yield transaction
            
            # Commit on success
            transaction.commit()
            self.transaction_history.append(transaction.to_dict())
            self._save_transaction_log()
            
        except Exception as e:
            # Rollback on failure
            if self.current_transaction:
                self.current_transaction.rollback()
            raise IFlowError(
                f"Transaction failed and was rolled back: {str(e)}",
                ErrorCode.VALIDATION_FAILED
            )
        finally:
            self.current_transaction = None
    
    def update_state(
        self,
        file_path: Path,
        new_data: Any,
        validate: Optional[Callable[[Any], bool]] = None
    ) -> None:
        """
        Update a state file within a transaction.
        
        Args:
            file_path: Path to the state file
            new_data: New data to write
            validate: Optional validation function
            
        Raises:
            TransactionError if not in a transaction
        """
        if not self.current_transaction:
            raise TransactionError("Must be called within a transaction")
        
        # Load old data
        old_data = None
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    old_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Validate new data
        if validate and not validate(new_data):
            raise TransactionError("Data validation failed")
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write new data
        with open(file_path, 'w') as f:
            json.dump(new_data, f, indent=2)
        
        # Log operation
        operation_type = "update" if old_data else "create"
        self.current_transaction.add_operation(
            operation_type,
            file_path,
            old_data,
            new_data
        )
    
    def delete_state(self, file_path: Path) -> None:
        """
        Delete a state file within a transaction.
        
        Args:
            file_path: Path to the state file
            
        Raises:
            TransactionError if not in a transaction
        """
        if not self.current_transaction:
            raise TransactionError("Must be called within a transaction")
        
        # Load old data
        old_data = None
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    old_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Delete file
        if file_path.exists():
            file_path.unlink()
        
        # Log operation
        self.current_transaction.add_operation(
            "delete",
            file_path,
            old_data,
            None
        )
    
    def read_state(self, file_path: Path) -> Optional[Any]:
        """
        Read a state file.
        
        Args:
            file_path: Path to the state file
            
        Returns:
            Parsed JSON data or None if file doesn't exist
        """
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def get_transaction_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get transaction history.
        
        Args:
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction records
        """
        return self.transaction_history[-limit:]
    
    def get_current_transaction(self) -> Optional[StateTransaction]:
        """
        Get the current active transaction.
        
        Returns:
            Current transaction or None
        """
        return self.current_transaction
    
    def cleanup_old_transactions(self, max_age_days: int = 7) -> int:
        """
        Clean up old transaction directories.
        
        Args:
            max_age_days: Maximum age in days to keep
            
        Returns:
            Number of directories cleaned up
        """
        transactions_dir = self.state_dir / ".transactions"
        if not transactions_dir.exists():
            return 0
        
        cleaned = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        
        for transaction_dir in transactions_dir.iterdir():
            if transaction_dir.is_dir():
                # Check modification time
                if transaction_dir.stat().st_mtime < cutoff:
                    try:
                        shutil.rmtree(transaction_dir)
                        cleaned += 1
                    except (IOError, OSError):
                        pass
        
        return cleaned