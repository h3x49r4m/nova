#!/usr/bin/env python3
"""
Backup Manager for Critical State Files
Provides backup, restore, and cleanup functionality for state files.
"""

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from .constants import BackupConstants
from .exceptions import BackupError, ErrorCategory, ErrorCode
from .file_lock import FileLock, FileLockError
from .structured_logger import LogFormat, StructuredLogger


class BackupStatus(Enum):
    """Status of backup operations."""
    SUCCESS = "success"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    NOT_FOUND = "not_found"


@dataclass
class BackupMetadata:
    """Metadata about a backup."""
    backup_id: str
    timestamp: str
    original_file: str
    original_size: int
    original_hash: str
    compressed: bool = False
    compressed_size: int | None = None
    compressed_hash: str | None = None
    created_by: str | None = None
    tags: list[str] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> BackupMetadata:
        """Create from dictionary."""
        return cls(**data)


class BackupManager:
    """Manages backups of critical state files."""

    def __init__(self, backup_dir: Path, max_backups: int | None = None):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory to store backups
            max_backups: Maximum number of backups to keep per file
        """
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups or BackupConstants.MAX_BACKUPS_PER_FILE.value
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Initialize logger
        self.logger = StructuredLogger(
            name="backup_manager",
            log_dir=self.backup_dir / ".logs",
            log_format=LogFormat.JSON
        )

        # Create index file
        self.index_file = self.backup_dir / 'backup_index.json'
        self.index = self._load_index()
        
        # Create empty index file if it doesn't exist
        if not self.index_file.exists():
            self._save_index()

    def _load_index(self) -> dict[str, list[BackupMetadata]]:
        """Load backup index from file."""
        if not self.index_file.exists():
            return {}

        try:
            with FileLock(self.index_file, timeout=10):
                with open(self.index_file) as f:
                    data = json.load(f)

                # Convert to BackupMetadata objects
                index = {}
                for file_path, backups in data.items():
                    index[file_path] = [BackupMetadata.from_dict(b) for b in backups]

                return index
        except (OSError, FileLockError, json.JSONDecodeError) as e:
            self.logger.warning(f"Could not load backup index: {e}")
            return {}

    def _save_index(self):
        """Save backup index to file."""
        try:
            # Create backup of index
            index_backup = None
            if self.index_file.exists():
                index_backup = self.backup_dir / 'backup_index.backup.json'
                shutil.copy2(self.index_file, index_backup)

            # Use separate lock file
            lock_file = self.backup_dir / 'backup_index.json.lock'
            with FileLock(lock_file, timeout=10):
                # Convert to serializable format
                data = {}
                for file_path, backups in self.index.items():
                    data[file_path] = [b.to_dict() for b in backups]

                with open(self.index_file, 'w') as f:
                    json.dump(data, f, indent=2)

                # Remove backup if successful
                if index_backup is not None and index_backup.exists():
                    index_backup.unlink()
        except FileLockError as e:
            raise BackupError(
                f"Could not save backup index: {e}",
                ErrorCode.LOCK_ERROR,
                ErrorCategory.SYSTEM
            )
        except (OSError, TypeError) as e:
            raise BackupError(
                f"Error writing backup index: {e}",
                ErrorCode.FILE_WRITE_ERROR,
                ErrorCategory.SYSTEM
            )

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except OSError:
            return ""

    def _generate_backup_id(self, file_path: Path) -> str:
        """Generate a unique backup ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        file_hash = self._calculate_hash(file_path)[:8]
        file_name = file_path.stem
        return f"{file_name}_{timestamp}_{file_hash}"

    def create_backup(
        self,
        file_path: Path,
        tags: list[str] | None = None,
        compress: bool = False
    ) -> Path:
        """
        Create a backup of a file.

        Args:
            file_path: Path to file to backup
            tags: Optional tags for categorization
            compress: Whether to compress the backup

        Returns:
            Path to the backup file
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise BackupError(
                f"File not found: {file_path}",
                ErrorCode.FILE_NOT_FOUND,
                ErrorCategory.SYSTEM_ERROR
            )

        # Calculate hash before backup
        original_hash = self._calculate_hash(file_path)
        original_size = file_path.stat().st_size

        # Generate backup ID
        backup_id = self._generate_backup_id(file_path)

        # Create backup directory
        backup_subdir = self.backup_dir / backup_id
        backup_subdir.mkdir(exist_ok=True)

        # Copy file to backup directory
        backup_file = backup_subdir / file_path.name
        shutil.copy2(file_path, backup_file)

        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=datetime.now().isoformat(),
            original_file=str(file_path),
            original_size=original_size,
            original_hash=original_hash,
            compressed=compress,
            compressed_size=None,
            compressed_hash=None,
            created_by="system",
            tags=tags or []
        )

        # Save metadata
        metadata_file = backup_subdir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Update index
        file_key = str(file_path)
        if file_key not in self.index:
            self.index[file_key] = []

        self.index[file_key].insert(0, metadata)

        # Enforce max backups
        if len(self.index[file_key]) > self.max_backups:
            self._cleanup_old_backups(file_key)

        self._save_index()

        return backup_file

    def restore_backup(
        self,
        file_path: Path,
        backup_path: Path,
        validate: bool = True
    ) -> None:
        """
        Restore a backup.

        Args:
            file_path: Target file path to restore to
            backup_path: Path to the backup file to restore from
            validate: Whether to validate backup integrity
        """
        if not backup_path.exists():
            raise BackupError(
                f"Backup not found: {backup_path}",
                ErrorCode.FILE_NOT_FOUND,
                ErrorCategory.SYSTEM_ERROR
            )

        if not backup_path.is_dir():
            # If backup_path is a file, get the parent directory
            backup_dir = backup_path.parent
            backup_file = backup_path
        else:
            # If backup_path is a directory, look for metadata
            backup_dir = backup_path
            metadata_file = backup_dir / 'metadata.json'
            if not metadata_file.exists():
                raise BackupError(
                    f"Backup metadata not found: {backup_dir}",
                    ErrorCode.FILE_NOT_FOUND,
                    ErrorCategory.SYSTEM_ERROR
                )

            with open(metadata_file) as f:
                metadata_data = json.load(f)

            metadata = BackupMetadata.from_dict(metadata_data)

            # Find backup file
            backup_file = backup_dir / Path(metadata.original_file).name
            if not backup_file.exists():
                raise BackupError(
                    f"Backup file not found: {backup_dir}",
                    ErrorCode.FILE_NOT_FOUND,
                    ErrorCategory.SYSTEM_ERROR
                )

            # Validate if requested
            if validate:
                current_hash = self._calculate_hash(backup_file)
                if current_hash != metadata.original_hash:
                    raise ValueError(f"Backup corrupted (hash mismatch): {backup_dir}")

        # Create target directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup of current file before restoring
        if file_path.exists():
            current_backup_id = self._generate_backup_id(file_path)
            current_backup_dir = self.backup_dir / f"pre_restore_{current_backup_id}"
            current_backup_dir.mkdir(exist_ok=True)
            shutil.copy2(file_path, current_backup_dir / file_path.name)

        # Restore backup
        shutil.copy2(backup_file, file_path)

    def list_backups(
        self,
        file_path: Path | None = None,
        tags: list[str] | None = None
    ) -> list[BackupMetadata]:
        """
        List backups, optionally filtered by file or tags.

        Args:
            file_path: Filter by original file path
            tags: Filter by tags

        Returns:
            List of backup metadata
        """
        if file_path:
            file_key = str(file_path)
            backups = self.index.get(file_key, [])
        else:
            backups = []
            for file_backups in self.index.values():
                backups.extend(file_backups)

        # Filter by tags
        if tags:
            backups = [
                b for b in backups
                if b.tags and any(tag in b.tags for tag in tags)
            ]

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)

        return backups

    def delete_backup(self, backup_id: str) -> tuple[bool, str]:
        """
        Delete a backup.

        Args:
            backup_id: ID of backup to delete

        Returns:
            Tuple of (success, message)
        """
        backup_dir = self.backup_dir / backup_id

        if not backup_dir.exists():
            return False, f"Backup not found: {backup_id}"

        try:
            # Find and remove from index
            for file_key, backups in self.index.items():
                for i, backup in enumerate(backups):
                    if backup.backup_id == backup_id:
                        self.index[file_key].pop(i)
                        break

            # Remove backup directory
            shutil.rmtree(backup_dir)

            # Save updated index
            self._save_index()

            return True, f"Backup deleted: {backup_id}"

        except Exception as e:
            return False, f"Error deleting backup: {e}"

    def _cleanup_old_backups(self, file_key: str) -> int:
        """
        Remove old backups beyond max limit.

        Args:
            file_key: Key in index to cleanup

        Returns:
            Number of backups removed
        """
        backups = self.index.get(file_key, [])

        if len(backups) <= self.max_backups:
            return 0

        to_remove = backups[self.max_backups:]
        removed_count = 0

        for backup in to_remove:
            backup_dir = self.backup_dir / backup.backup_id
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
                removed_count += 1

        # Update index
        self.index[file_key] = backups[:self.max_backups]

        return removed_count

    def cleanup_old_backups(self, keep_count: int | None = None) -> dict[str, int]:
        """
        Delete old backups across all files.

        Args:
            keep_count: Number of backups to keep per file (uses max_backups if not specified)

        Returns:
            Dictionary mapping file paths to number of backups removed
        """
        keep = keep_count or self.max_backups
        results = {}

        for file_key, backups in list(self.index.items()):
            if len(backups) > keep:
                self.index[file_key] = backups[:keep]
                removed = len(backups) - keep

                # Actually delete the backup directories
                for backup in backups[keep:]:
                    backup_dir = self.backup_dir / backup.backup_id
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)

                results[file_key] = removed

        if results:
            self._save_index()

        return results

    def get_backup_stats(self) -> dict:
        """
        Get statistics about backups.

        Returns:
            Dictionary with backup statistics
        """
        total_backups = sum(len(backups) for backups in self.index.values())
        total_size = 0

        for backups in self.index.values():
            for backup in backups:
                backup_dir = self.backup_dir / backup.backup_id
                if backup_dir.exists():
                    total_size += sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())

        return {
            'total_backups': total_backups,
            'total_files_backed': len(self.index),
            'total_size_bytes': total_size,
            'total_size_human': self._human_readable_size(total_size),
            'max_backups_per_file': self.max_backups
        }

    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


class StateBackupManager(BackupManager):
    """
    Specialized backup manager for state files.
    Handles state-specific operations like version tracking.
    """

    def backup_state_before_operation(
        self,
        state_file: Path,
        operation: str
    ) -> tuple[BackupStatus, str | None, BackupMetadata | None]:
        """
        Create a backup before performing an operation on state.

        Args:
            state_file: Path to state file
            operation: Name of operation being performed

        Returns:
            Tuple of (status, message, metadata)
        """
        tags = ['state', 'pre-operation', operation]
        return self.create_backup(state_file, tags=tags)

    def validate_state_backup(self, backup_id: str, expected_state: dict) -> tuple[bool, list[str]]:
        """
        Validate a state backup against expected state structure.

        Args:
            backup_id: ID of backup to validate
            expected_state: Expected state structure for validation

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        backup_dir = self.backup_dir / backup_id

        if not backup_dir.exists():
            return False, [f"Backup not found: {backup_id}"]

        errors = []

        try:
            # Load backup
            metadata_file = backup_dir / 'metadata.json'
            if not metadata_file.exists():
                errors.append("Metadata file missing")
                return False, errors

            with open(metadata_file) as f:
                metadata = BackupMetadata.from_dict(json.load(f))

            backup_file = backup_dir / Path(metadata.original_file).name
            if not backup_file.exists():
                errors.append("Backup file missing")
                return False, errors

            with open(backup_file) as f:
                state_data = json.load(f)

            # Validate structure
            for key, value_type in expected_state.items():
                if key not in state_data:
                    errors.append(f"Missing required field: {key}")
                elif not isinstance(state_data[key], value_type):
                    errors.append(f"Field {key} has wrong type: expected {value_type.__name__}")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"Validation error: {e!s}")
            return False, errors
