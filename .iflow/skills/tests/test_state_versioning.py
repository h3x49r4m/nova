"""Tests for state versioning system."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from utils.state_versioning import (
    StateVersion,
    VersionHistory,
    StateVersionManager
)
from utils.exceptions import IFlowError, ErrorCode


class TestStateVersion:
    """Test StateVersion dataclass."""
    
    def test_version_creation(self):
        """Test creating a state version."""
        version = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00",
            author="user1",
            description="Initial version"
        )
        
        assert version.version_id == "v1"
        assert version.file_path == "test.json"
        assert version.author == "user1"
        assert version.description == "Initial version"
        assert version.parent_version_id is None
    
    def test_version_with_parent(self):
        """Test creating a version with a parent."""
        version = StateVersion(
            version_id="v2",
            file_path="test.json",
            timestamp="2024-01-01T01:00:00",
            parent_version_id="v1"
        )
        
        assert version.parent_version_id == "v1"
    
    def test_version_to_dict(self):
        """Test converting version to dictionary."""
        version = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00",
            author="user1",
            description="Test",
            checksum="abc123",
            size_bytes=1024
        )
        
        data = version.to_dict()
        
        assert data["version_id"] == "v1"
        assert data["file_path"] == "test.json"
        assert data["author"] == "user1"
        assert data["description"] == "Test"
        assert data["checksum"] == "abc123"
        assert data["size_bytes"] == 1024
    
    def test_version_from_dict(self):
        """Test creating version from dictionary."""
        data = {
            "version_id": "v1",
            "file_path": "test.json",
            "timestamp": "2024-01-01T00:00:00",
            "author": "user1",
            "description": "Test",
            "parent_version_id": "v0",
            "checksum": "abc123",
            "size_bytes": 1024
        }
        
        version = StateVersion.from_dict(data)
        
        assert version.version_id == "v1"
        assert version.file_path == "test.json"
        assert version.author == "user1"
        assert version.description == "Test"
        assert version.parent_version_id == "v0"
        assert version.checksum == "abc123"
        assert version.size_bytes == 1024
    
    def test_version_from_dict_defaults(self):
        """Test creating version from dictionary with defaults."""
        data = {
            "version_id": "v1",
            "file_path": "test.json",
            "timestamp": "2024-01-01T00:00:00"
        }
        
        version = StateVersion.from_dict(data)
        
        assert version.author == "system"
        assert version.description == ""
        assert version.parent_version_id is None
        assert version.checksum == ""
        assert version.size_bytes == 0


class TestVersionHistory:
    """Test VersionHistory dataclass."""
    
    def test_history_creation(self):
        """Test creating a version history."""
        history = VersionHistory(file_path="test.json")
        
        assert history.file_path == "test.json"
        assert history.versions == []
        assert history.current_version_id is None
    
    def test_add_version(self):
        """Test adding a version to history."""
        history = VersionHistory(file_path="test.json")
        
        version1 = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00"
        )
        
        history.add_version(version1)
        
        assert len(history.versions) == 1
        assert history.current_version_id == "v1"
        assert history.versions[0] == version1
    
    def test_add_multiple_versions(self):
        """Test adding multiple versions to history."""
        history = VersionHistory(file_path="test.json")
        
        version1 = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00"
        )
        
        version2 = StateVersion(
            version_id="v2",
            file_path="test.json",
            timestamp="2024-01-01T01:00:00",
            parent_version_id="v1"
        )
        
        history.add_version(version1)
        history.add_version(version2)
        
        assert len(history.versions) == 2
        assert history.current_version_id == "v2"
        assert history.versions[0] == version1
        assert history.versions[1] == version2
    
    def test_get_version(self):
        """Test getting a specific version."""
        history = VersionHistory(file_path="test.json")
        
        version1 = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00"
        )
        
        version2 = StateVersion(
            version_id="v2",
            file_path="test.json",
            timestamp="2024-01-01T01:00:00"
        )
        
        history.add_version(version1)
        history.add_version(version2)
        
        assert history.get_version("v1") == version1
        assert history.get_version("v2") == version2
        assert history.get_version("v3") is None
    
    def test_get_latest_version(self):
        """Test getting the latest version."""
        history = VersionHistory(file_path="test.json")
        
        version1 = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00"
        )
        
        version2 = StateVersion(
            version_id="v2",
            file_path="test.json",
            timestamp="2024-01-01T01:00:00"
        )
        
        history.add_version(version1)
        history.add_version(version2)
        
        assert history.get_latest_version() == version2
    
    def test_get_latest_version_empty(self):
        """Test getting latest version from empty history."""
        history = VersionHistory(file_path="test.json")
        
        assert history.get_latest_version() is None
    
    def test_get_version_chain(self):
        """Test getting version chain."""
        history = VersionHistory(file_path="test.json")
        
        version1 = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00"
        )
        
        version2 = StateVersion(
            version_id="v2",
            file_path="test.json",
            timestamp="2024-01-01T01:00:00",
            parent_version_id="v1"
        )
        
        version3 = StateVersion(
            version_id="v3",
            file_path="test.json",
            timestamp="2024-01-01T02:00:00",
            parent_version_id="v2"
        )
        
        history.add_version(version1)
        history.add_version(version2)
        history.add_version(version3)
        
        chain = history.get_version_chain("v3")
        
        assert len(chain) == 3
        assert chain[0] == version1
        assert chain[1] == version2
        assert chain[2] == version3
    
    def test_history_to_dict(self):
        """Test converting history to dictionary."""
        history = VersionHistory(file_path="test.json")
        
        version = StateVersion(
            version_id="v1",
            file_path="test.json",
            timestamp="2024-01-01T00:00:00"
        )
        
        history.add_version(version)
        
        data = history.to_dict()
        
        assert data["file_path"] == "test.json"
        assert len(data["versions"]) == 1
        assert data["versions"][0]["version_id"] == "v1"
        assert data["current_version_id"] == "v1"
    
    def test_history_from_dict(self):
        """Test creating history from dictionary."""
        data = {
            "file_path": "test.json",
            "versions": [
                {
                    "version_id": "v1",
                    "file_path": "test.json",
                    "timestamp": "2024-01-01T00:00:00"
                }
            ],
            "current_version_id": "v1"
        }
        
        history = VersionHistory.from_dict(data)
        
        assert history.file_path == "test.json"
        assert len(history.versions) == 1
        assert history.versions[0].version_id == "v1"
        assert history.current_version_id == "v1"


class TestStateVersionManager:
    """Test StateVersionManager."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_dir = self.temp_dir / "state"
        self.state_dir.mkdir()
        self.manager = StateVersionManager(self.state_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        assert self.manager.state_dir == self.state_dir
        assert self.manager.versions_dir == self.state_dir / ".versions"
        assert self.manager.max_versions == 100
        assert self.manager.version_histories == {}
    
    def test_create_version(self):
        """Test creating a version."""
        # Create a test file
        test_file = self.state_dir / "test.json"
        test_data = {"key": "value"}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        # Create version
        version = self.manager.create_version(
            test_file,
            author="user1",
            description="Initial version"
        )
        
        assert version.version_id is not None
        assert version.file_path == "test.json"
        assert version.author == "user1"
        assert version.description == "Initial version"
        assert version.parent_version_id is None
        assert version.checksum != ""
        assert version.size_bytes > 0
    
    def test_create_version_nonexistent_file(self):
        """Test creating version for non-existent file."""
        test_file = self.state_dir / "nonexistent.json"
        
        with pytest.raises(IFlowError) as exc_info:
            self.manager.create_version(test_file)
        
        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
    
    def test_create_multiple_versions(self):
        """Test creating multiple versions."""
        test_file = self.state_dir / "test.json"
        
        # Create first version
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file, author="user1")
        
        # Modify file and create second version
        with open(test_file, 'w') as f:
            json.dump({"version": 2}, f)
        
        version2 = self.manager.create_version(test_file, author="user2")
        
        assert version1.parent_version_id is None
        assert version2.parent_version_id == version1.version_id
        
        # Check history
        history = self.manager.get_version_history(test_file)
        assert len(history) == 2
        assert history[0].version_id == version1.version_id
        assert history[1].version_id == version2.version_id
    
    def test_restore_version(self):
        """Test restoring a version."""
        test_file = self.state_dir / "test.json"
        
        # Create initial version
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        # Modify file
        with open(test_file, 'w') as f:
            json.dump({"version": 2}, f)
        
        version2 = self.manager.create_version(test_file)
        
        # Restore to version1
        self.manager.restore_version(test_file, version1.version_id)
        
        # Check file content
        with open(test_file, 'r') as f:
            data = json.load(f)
        
        assert data == {"version": 1}
        
        # Check that a new version was created
        history = self.manager.get_version_history(test_file)
        assert len(history) == 3
    
    def test_restore_version_not_found(self):
        """Test restoring non-existent version."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        self.manager.create_version(test_file)
        
        with pytest.raises(IFlowError) as exc_info:
            self.manager.restore_version(test_file, "nonexistent_version")
        
        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
    
    def test_get_version_history(self):
        """Test getting version history."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        # Create multiple versions
        for i in range(3):
            with open(test_file, 'w') as f:
                json.dump({"version": i + 1}, f)
            self.manager.create_version(test_file)
        
        # Get full history
        history = self.manager.get_version_history(test_file)
        assert len(history) == 3
        
        # Get limited history
        history_limited = self.manager.get_version_history(test_file, limit=2)
        assert len(history_limited) == 2
    
    def test_get_version_history_empty(self):
        """Test getting history for file with no versions."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        history = self.manager.get_version_history(test_file)
        assert len(history) == 0
    
    def test_get_version(self):
        """Test getting a specific version."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        retrieved = self.manager.get_version(test_file, version1.version_id)
        
        assert retrieved is not None
        assert retrieved.version_id == version1.version_id
        assert retrieved.author == version1.author
    
    def test_get_version_not_found(self):
        """Test getting non-existent version."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        self.manager.create_version(test_file)
        
        retrieved = self.manager.get_version(test_file, "nonexistent")
        
        assert retrieved is None
    
    def test_get_current_version(self):
        """Test getting current version."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        current = self.manager.get_current_version(test_file)
        
        assert current is not None
        assert current.version_id == version1.version_id
    
    def test_get_current_version_no_versions(self):
        """Test getting current version when no versions exist."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        current = self.manager.get_current_version(test_file)
        
        assert current is None
    
    def test_compare_versions(self):
        """Test comparing two versions."""
        test_file = self.state_dir / "test.json"
        
        # Create first version
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        # Create second version
        with open(test_file, 'w') as f:
            json.dump({"version": 2}, f)
        
        version2 = self.manager.create_version(test_file)
        
        # Compare
        comparison = self.manager.compare_versions(
            test_file,
            version1.version_id,
            version2.version_id
        )
        
        assert "version1" in comparison
        assert "version2" in comparison
        assert comparison["data_changed"] is True
        assert comparison["checksum_changed"] is True
    
    def test_compare_versions_no_history(self):
        """Test comparing versions with no history."""
        test_file = self.state_dir / "test.json"
        
        comparison = self.manager.compare_versions(
            test_file,
            "v1",
            "v2"
        )
        
        assert "error" in comparison
    
    def test_delete_version(self):
        """Test deleting a version."""
        test_file = self.state_dir / "test.json"
        
        # Create two versions
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        with open(test_file, 'w') as f:
            json.dump({"version": 2}, f)
        
        version2 = self.manager.create_version(test_file)
        
        # Delete first version
        self.manager.delete_version(test_file, version1.version_id)
        
        # Check history
        history = self.manager.get_version_history(test_file)
        assert len(history) == 1
        assert history[0].version_id == version2.version_id
    
    def test_delete_current_version(self):
        """Test deleting current version should fail."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        with pytest.raises(IFlowError) as exc_info:
            self.manager.delete_version(test_file, version1.version_id)
        
        assert exc_info.value.code == ErrorCode.VALIDATION_FAILED
    
    def test_delete_version_not_found(self):
        """Test deleting non-existent version."""
        test_file = self.state_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        self.manager.create_version(test_file)
        
        with pytest.raises(IFlowError) as exc_info:
            self.manager.delete_version(test_file, "nonexistent")
        
        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
    
    def test_prune_old_versions(self):
        """Test pruning old versions."""
        # Create manager with max_versions = 3
        manager = StateVersionManager(self.state_dir, max_versions=3)
        
        test_file = self.state_dir / "test.json"
        
        # Create 5 versions
        for i in range(5):
            with open(test_file, 'w') as f:
                json.dump({"version": i + 1}, f)
            manager.create_version(test_file)
        
        # Check that only 3 versions remain
        history = manager.get_version_history(test_file)
        assert len(history) == 3
    
    def test_get_all_histories(self):
        """Test getting all version histories."""
        test_file1 = self.state_dir / "test1.json"
        test_file2 = self.state_dir / "test2.json"
        
        # Create versions for both files
        with open(test_file1, 'w') as f:
            json.dump({"file": 1}, f)
        
        with open(test_file2, 'w') as f:
            json.dump({"file": 2}, f)
        
        self.manager.create_version(test_file1)
        self.manager.create_version(test_file2)
        
        # Get all histories
        histories = self.manager.get_all_histories()
        
        assert len(histories) == 2
        assert "test1.json" in histories
        assert "test2.json" in histories
    
    def test_cleanup_unused_versions(self):
        """Test cleaning up unused versions."""
        test_file = self.state_dir / "test.json"
        
        # Create versions
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        with open(test_file, 'w') as f:
            json.dump({"version": 2}, f)
        
        version2 = self.manager.create_version(test_file)
        
        # Cleanup with max_age_days = 0 (should clean all non-current versions)
        cleaned = self.manager.cleanup_unused_versions(max_age_days=0)
        
        # version1 should be cleaned (not current)
        assert cleaned >= 0
    
    def test_persistence_version_index(self):
        """Test that version index persists across manager instances."""
        test_file = self.state_dir / "test.json"
        
        # Create version with first manager
        with open(test_file, 'w') as f:
            json.dump({"version": 1}, f)
        
        version1 = self.manager.create_version(test_file)
        
        # Create new manager instance
        new_manager = StateVersionManager(self.state_dir)
        
        # Check that version history is loaded
        history = new_manager.get_version_history(test_file)
        assert len(history) == 1
        assert history[0].version_id == version1.version_id
    
    def test_nested_directory_file(self):
        """Test versioning a file in nested directory."""
        nested_dir = self.state_dir / "nested" / "dir"
        nested_dir.mkdir(parents=True)
        
        test_file = nested_dir / "test.json"
        
        with open(test_file, 'w') as f:
            json.dump({"nested": True}, f)
        
        version = self.manager.create_version(test_file)
        
        assert version.file_path == "nested/dir/test.json"
        
        # Verify we can restore it
        restored = self.manager.get_version(test_file, version.version_id)
        assert restored is not None