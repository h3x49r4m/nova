"""Tests for backup_manager module."""

import pytest
from pathlib import Path
import sys
import json
import shutil
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.backup_manager import (
    BackupStatus,
    BackupMetadata,
    BackupManager
)
from utils.exceptions import BackupError
from utils.file_lock import FileLockError


@pytest.fixture
def tmp_backup_dir(tmp_path):
    """Create a temporary backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample file for testing."""
    sample = tmp_path / "sample.txt"
    sample.write_text("Sample content for backup")
    return sample


class TestBackupStatus:
    """Test BackupStatus enum."""

    def test_status_values(self):
        """Test that status values are correct."""
        assert BackupStatus.SUCCESS.value == "success"
        assert BackupStatus.FAILED.value == "failed"
        assert BackupStatus.CORRUPTED.value == "corrupted"
        assert BackupStatus.NOT_FOUND.value == "not_found"


class TestBackupMetadata:
    """Test BackupMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating backup metadata."""
        metadata = BackupMetadata(
            backup_id="backup_001",
            timestamp="2024-01-01T00:00:00",
            original_file="/path/to/file.txt",
            original_size=100,
            original_hash="abc123"
        )
        assert metadata.backup_id == "backup_001"
        assert metadata.original_size == 100
        assert metadata.compressed is False

    def test_metadata_compressed(self):
        """Test metadata with compression."""
        metadata = BackupMetadata(
            backup_id="backup_002",
            timestamp="2024-01-01T00:00:00",
            original_file="/path/to/file.txt",
            original_size=100,
            original_hash="abc123",
            compressed=True,
            compressed_size=50,
            compressed_hash="def456"
        )
        assert metadata.compressed is True
        assert metadata.compressed_size == 50

    def test_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = BackupMetadata(
            backup_id="backup_001",
            timestamp="2024-01-01T00:00:00",
            original_file="/path/to/file.txt",
            original_size=100,
            original_hash="abc123"
        )
        data = metadata.to_dict()
        assert data["backup_id"] == "backup_001"
        assert data["original_size"] == 100

    def test_from_dict(self):
        """Test creating metadata from dictionary."""
        data = {
            "backup_id": "backup_001",
            "timestamp": "2024-01-01T00:00:00",
            "original_file": "/path/to/file.txt",
            "original_size": 100,
            "original_hash": "abc123",
            "compressed": False
        }
        metadata = BackupMetadata.from_dict(data)
        assert metadata.backup_id == "backup_001"
        assert metadata.original_size == 100


class TestBackupManager:
    """Test BackupManager class."""

    def test_initialization(self, tmp_backup_dir):
        """Test backup manager initialization."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        assert manager.backup_dir == tmp_backup_dir
        assert manager.max_backups > 0
        assert manager.index_file.exists()

    def test_custom_max_backups(self, tmp_backup_dir):
        """Test backup manager with custom max_backups."""
        manager = BackupManager(backup_dir=tmp_backup_dir, max_backups=5)
        assert manager.max_backups == 5

    def test_create_backup(self, tmp_backup_dir, sample_file):
        """Test creating a backup."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        backup_path = manager.create_backup(sample_file)
        assert backup_path.exists()
        assert backup_path.parent == tmp_backup_dir

    def test_create_multiple_backups(self, tmp_backup_dir, sample_file):
        """Test creating multiple backups."""
        manager = BackupManager(backup_dir=tmp_backup_dir, max_backups=3)
        for i in range(5):
            manager.create_backup(sample_file)
        # Should only keep max_backups
        backups = manager.list_backups(sample_file)
        assert len(backups) <= 3

    def test_restore_backup(self, tmp_backup_dir, sample_file):
        """Test restoring a backup."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        backup_path = manager.create_backup(sample_file)
        
        # Modify original file
        sample_file.write_text("Modified content")
        
        # Restore backup
        manager.restore_backup(sample_file, backup_path)
        content = sample_file.read_text()
        assert content == "Sample content for backup"

    def test_restore_nonexistent_backup(self, tmp_backup_dir, sample_file):
        """Test restoring a nonexistent backup."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        fake_backup = tmp_backup_dir / "fake_backup.txt"
        with pytest.raises(BackupError):
            manager.restore_backup(sample_file, fake_backup)

    def test_list_backups(self, tmp_backup_dir, sample_file):
        """Test listing backups for a file."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        manager.create_backup(sample_file)
        manager.create_backup(sample_file)
        
        backups = manager.list_backups(sample_file)
        assert len(backups) == 2
        assert all(isinstance(b, BackupMetadata) for b in backups)

    def test_list_backups_empty(self, tmp_backup_dir, sample_file):
        """Test listing backups for a file with no backups."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        backups = manager.list_backups(sample_file)
        assert len(backups) == 0

    def test_delete_backup(self, tmp_backup_dir, sample_file):
        """Test deleting a backup."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        backup_path = manager.create_backup(sample_file)
        
        manager.delete_backup(sample_file, backup_path)
        assert not backup_path.exists()
        
        backups = manager.list_backups(sample_file)
        assert len(backups) == 0

    def test_delete_all_backups(self, tmp_backup_dir, sample_file):
        """Test deleting all backups for a file."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        manager.create_backup(sample_file)
        manager.create_backup(sample_file)
        
        manager.delete_all_backups(sample_file)
        backups = manager.list_backups(sample_file)
        assert len(backups) == 0

    def test_cleanup_old_backups(self, tmp_backup_dir, sample_file):
        """Test cleaning up old backups beyond max_backups."""
        manager = BackupManager(backup_dir=tmp_backup_dir, max_backups=2)
        for i in range(5):
            manager.create_backup(sample_file)
        
        manager.cleanup_old_backups(sample_file)
        backups = manager.list_backups(sample_file)
        assert len(backups) <= 2

    def test_get_backup_metadata(self, tmp_backup_dir, sample_file):
        """Test getting backup metadata."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        backup_path = manager.create_backup(sample_file)
        
        metadata = manager.get_backup_metadata(sample_file, backup_path)
        assert metadata is not None
        assert metadata.original_file == str(sample_file)

    def test_verify_backup_integrity(self, tmp_backup_dir, sample_file):
        """Test verifying backup integrity."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        backup_path = manager.create_backup(sample_file)
        
        is_valid = manager.verify_backup_integrity(sample_file, backup_path)
        assert is_valid is True

    def test_verify_corrupted_backup(self, tmp_backup_dir, sample_file):
        """Test verifying corrupted backup."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        backup_path = manager.create_backup(sample_file)
        
        # Corrupt the backup
        backup_path.write_text("corrupted content")
        
        is_valid = manager.verify_backup_integrity(sample_file, backup_path)
        assert is_valid is False

    def test_prune_old_backups_by_age(self, tmp_backup_dir, sample_file):
        """Test pruning backups by age."""
        manager = BackupManager(backup_dir=tmp_backup_dir, max_backups=10)
        manager.create_backup(sample_file)
        
        # Prune backups older than 0 days (should remove all)
        manager.prune_old_backups(max_age_days=0)
        backups = manager.list_backups(sample_file)
        assert len(backups) == 0

    def test_get_total_backup_size(self, tmp_backup_dir, sample_file):
        """Test getting total backup size."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        manager.create_backup(sample_file)
        manager.create_backup(sample_file)
        
        total_size = manager.get_total_backup_size()
        assert total_size > 0

    def test_load_index(self, tmp_backup_dir):
        """Test loading backup index."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        assert manager.index is not None
        assert isinstance(manager.index, dict)

    def test_save_index(self, tmp_backup_dir, sample_file):
        """Test saving backup index."""
        manager = BackupManager(backup_dir=tmp_backup_dir)
        manager.create_backup(sample_file)
        
        # Force save index
        manager._save_index()
        assert manager.index_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])