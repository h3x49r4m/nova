#!/usr/bin/env python3
"""
Unit tests for CheckpointManager module.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

from checkpoint_manager import CheckpointManager, Checkpoint, CheckpointStatus
from exceptions import IFlowError, ErrorCode


class TestCheckpoint:
    """Tests for the Checkpoint class."""

    def test_checkpoint_initialization(self):
        """Test checkpoint object initialization."""
        checkpoint_id = "cp_20240307_120000_abc12345"
        name = "Test Checkpoint"
        timestamp = "2024-03-07T12:00:00"
        state_data = {"key": "value"}
        metadata = {"tags": ["test"]}

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            name=name,
            timestamp=timestamp,
            state_data=state_data,
            metadata=metadata
        )

        assert checkpoint.checkpoint_id == checkpoint_id
        assert checkpoint.name == name
        assert checkpoint.timestamp == timestamp
        assert checkpoint.state_data == state_data
        assert checkpoint.metadata == metadata
        assert checkpoint.status == CheckpointStatus.ACTIVE
        assert checkpoint.size_bytes > 0

    def test_checkpoint_to_dict(self):
        """Test converting checkpoint to dictionary."""
        checkpoint = Checkpoint(
            checkpoint_id="cp_test",
            name="Test",
            timestamp="2024-03-07T12:00:00",
            state_data={"data": "test"},
            metadata={"tags": ["test"]}
        )

        result = checkpoint.to_dict()

        assert result["checkpoint_id"] == "cp_test"
        assert result["name"] == "Test"
        assert result["timestamp"] == "2024-03-07T12:00:00"
        assert result["status"] == "active"
        assert "size_bytes" in result
        assert result["metadata"]["tags"] == ["test"]


class TestCheckpointManager:
    """Tests for the CheckpointManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def checkpoint_manager(self, temp_dir):
        """Create a CheckpointManager instance for testing."""
        return CheckpointManager(repo_root=temp_dir)

    def test_checkpoint_manager_initialization(self, temp_dir):
        """Test CheckpointManager initialization."""
        checkpoint_dir = temp_dir / ".iflow" / "checkpoints"
        manager = CheckpointManager(repo_root=temp_dir, max_checkpoints=10)

        assert manager.repo_root == temp_dir
        assert manager.checkpoint_dir == checkpoint_dir
        assert manager.max_checkpoints == 10
        assert manager.checkpoint_dir.exists()
        assert isinstance(manager.checkpoints, dict)

    def test_create_checkpoint(self, checkpoint_manager):
        """Test creating a new checkpoint."""
        state_data = {"key1": "value1", "key2": "value2"}
        metadata = {"tags": ["test", "unit"]}
        tags = ["test"]

        checkpoint = checkpoint_manager.create_checkpoint(
            name="Test Checkpoint",
            state_data=state_data,
            metadata=metadata,
            tags=tags
        )

        assert checkpoint.name == "Test Checkpoint"
        assert checkpoint.state_data == state_data
        assert checkpoint.status == CheckpointStatus.ACTIVE
        assert checkpoint.checkpoint_id in checkpoint_manager.checkpoints
        assert checkpoint.checkpoint_id.startswith("cp_")

    def test_create_checkpoint_with_minimal_args(self, checkpoint_manager):
        """Test creating a checkpoint with minimal arguments."""
        state_data = {"simple": "data"}

        checkpoint = checkpoint_manager.create_checkpoint(
            name="Minimal Checkpoint",
            state_data=state_data
        )

        assert checkpoint.name == "Minimal Checkpoint"
        assert checkpoint.state_data == state_data
        assert checkpoint.metadata == {}

    def test_create_checkpoint_persists_state(self, checkpoint_manager):
        """Test that checkpoint state is persisted to file."""
        state_data = {"persisted": "data", "number": 42}

        checkpoint = checkpoint_manager.create_checkpoint(
            name="Persistence Test",
            state_data=state_data
        )

        checkpoint_file = checkpoint_manager.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        assert checkpoint_file.exists()

        with open(checkpoint_file, 'r') as f:
            loaded_data = json.load(f)

        assert loaded_data == state_data

    def test_create_checkpoint_updates_index(self, checkpoint_manager):
        """Test that creating a checkpoint updates the index."""
        checkpoint_manager.create_checkpoint(
            name="Index Test",
            state_data={"index": "test"}
        )

        assert checkpoint_manager.index_file.exists()

        with open(checkpoint_manager.index_file, 'r') as f:
            index_data = json.load(f)

        assert index_data["total_checkpoints"] == 1
        assert len(index_data["checkpoints"]) == 1
        assert index_data["checkpoints"][0]["name"] == "Index Test"

    def test_create_checkpoint_enforces_limit(self, checkpoint_manager):
        """Test that max checkpoints limit is enforced."""
        # Set max to 3
        checkpoint_manager.max_checkpoints = 3

        # Create 5 checkpoints
        for i in range(5):
            checkpoint_manager.create_checkpoint(
                name=f"Checkpoint {i}",
                state_data={"index": i}
            )

        # Should only have 3 checkpoints (oldest deleted)
        assert len(checkpoint_manager.checkpoints) == 3

        # Oldest checkpoint (0 and 1) should be deleted
        # Newest (2, 3, 4) should remain
        remaining_ids = list(checkpoint_manager.checkpoints.keys())
        assert "Checkpoint 2" in [checkpoint_manager.checkpoints[cp_id].name for cp_id in remaining_ids]
        assert "Checkpoint 3" in [checkpoint_manager.checkpoints[cp_id].name for cp_id in remaining_ids]
        assert "Checkpoint 4" in [checkpoint_manager.checkpoints[cp_id].name for cp_id in remaining_ids]

    def test_restore_checkpoint(self, checkpoint_manager):
        """Test restoring a checkpoint."""
        original_state = {"key": "original", "value": 42}

        checkpoint = checkpoint_manager.create_checkpoint(
            name="Restore Test",
            state_data=original_state
        )

        # Modify state
        modified_state = {"key": "modified", "value": 99}

        # Restore checkpoint
        restored_state = checkpoint_manager.restore_checkpoint(checkpoint.checkpoint_id)

        assert restored_state == original_state
        assert restored_state != modified_state

    def test_restore_nonexistent_checkpoint(self, checkpoint_manager):
        """Test restoring a non-existent checkpoint."""
        with pytest.raises(IFlowError) as exc_info:
            checkpoint_manager.restore_checkpoint("cp_nonexistent")

        assert exc_info.value.code == ErrorCode.CHECKPOINT_NOT_FOUND

    def test_list_checkpoints(self, checkpoint_manager):
        """Test listing all checkpoints."""
        # Create multiple checkpoints
        cp1 = checkpoint_manager.create_checkpoint("CP1", {"id": 1})
        cp2 = checkpoint_manager.create_checkpoint("CP2", {"id": 2})
        cp3 = checkpoint_manager.create_checkpoint("CP3", {"id": 3})

        checkpoints = checkpoint_manager.list_checkpoints()

        assert len(checkpoints) == 3
        assert cp1.checkpoint_id in [cp.checkpoint_id for cp in checkpoints]
        assert cp2.checkpoint_id in [cp.checkpoint_id for cp in checkpoints]
        assert cp3.checkpoint_id in [cp.checkpoint_id for cp in checkpoints]

    def test_list_checkpoints_empty(self, checkpoint_manager):
        """Test listing checkpoints when none exist."""
        checkpoints = checkpoint_manager.list_checkpoints()
        assert checkpoints == []

    def test_delete_checkpoint(self, checkpoint_manager):
        """Test deleting a checkpoint."""
        checkpoint = checkpoint_manager.create_checkpoint(
            name="Delete Test",
            state_data={"to": "delete"}
        )

        assert checkpoint.checkpoint_id in checkpoint_manager.checkpoints

        checkpoint_manager.delete_checkpoint(checkpoint.checkpoint_id)

        assert checkpoint.checkpoint_id not in checkpoint_manager.checkpoints
        assert checkpoint.status == CheckpointStatus.DELETED

    def test_delete_nonexistent_checkpoint(self, checkpoint_manager):
        """Test deleting a non-existent checkpoint."""
        with pytest.raises(IFlowError) as exc_info:
            checkpoint_manager.delete_checkpoint("cp_nonexistent")

        assert exc_info.value.code == ErrorCode.CHECKPOINT_NOT_FOUND

    def test_archive_checkpoint(self, checkpoint_manager):
        """Test archiving a checkpoint."""
        checkpoint = checkpoint_manager.create_checkpoint(
            name="Archive Test",
            state_data={"to": "archive"}
        )

        checkpoint_manager.archive_checkpoint(checkpoint.checkpoint_id)

        assert checkpoint.status == CheckpointStatus.ARCHIVED

    def test_get_checkpoint(self, checkpoint_manager):
        """Test getting a specific checkpoint."""
        checkpoint = checkpoint_manager.create_checkpoint(
            name="Get Test",
            state_data={"get": "me"}
        )

        retrieved = checkpoint_manager.get_checkpoint(checkpoint.checkpoint_id)

        assert retrieved.checkpoint_id == checkpoint.checkpoint_id
        assert retrieved.name == checkpoint.name
        assert retrieved.state_data == checkpoint.state_data

    def test_get_nonexistent_checkpoint(self, checkpoint_manager):
        """Test getting a non-existent checkpoint."""
        with pytest.raises(IFlowError) as exc_info:
            checkpoint_manager.get_checkpoint("cp_nonexistent")

        assert exc_info.value.code == ErrorCode.CHECKPOINT_NOT_FOUND

    def test_get_checkpoint_by_name(self, checkpoint_manager):
        """Test getting checkpoints by name."""
        cp1 = checkpoint_manager.create_checkpoint("Unique Name", {"id": 1})
        cp2 = checkpoint_manager.create_checkpoint("Duplicate Name", {"id": 2})
        cp3 = checkpoint_manager.create_checkpoint("Duplicate Name", {"id": 3})

        # Should return only checkpoints with "Duplicate Name"
        checkpoints = checkpoint_manager.get_checkpoint_by_name("Duplicate Name")

        assert len(checkpoints) == 2
        for cp in checkpoints:
            assert cp.name == "Duplicate Name"

    def test_get_checkpoint_by_name_not_found(self, checkpoint_manager):
        """Test getting checkpoints by name when none match."""
        checkpoints = checkpoint_manager.get_checkpoint_by_name("Nonexistent")
        assert checkpoints == []

    def test_checkpoint_size_calculation(self, checkpoint_manager):
        """Test that checkpoint size is calculated correctly."""
        state_data = {"key1": "value1" * 100, "key2": "value2" * 100}
        checkpoint = checkpoint_manager.create_checkpoint(
            name="Size Test",
            state_data=state_data
        )

        expected_size = len(json.dumps(state_data).encode('utf-8'))
        assert checkpoint.size_bytes == expected_size

    def test_checkpoint_metadata_tags(self, checkpoint_manager):
        """Test checkpoint tags in metadata."""
        tags = ["important", "production", "stable"]
        checkpoint = checkpoint_manager.create_checkpoint(
            name="Tagged Checkpoint",
            state_data={"tagged": True},
            tags=tags
        )

        assert "tags" in checkpoint.metadata
        assert checkpoint.metadata["tags"] == tags

    def test_load_index_from_file(self, temp_dir):
        """Test loading checkpoint index from file."""
        # Create a mock index file
        checkpoint_dir = temp_dir / ".iflow" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        index_file = checkpoint_dir / "index.json"

        index_data = {
            "version": "1.0",
            "last_updated": "2024-03-07T12:00:00",
            "total_checkpoints": 2,
            "checkpoints": [
                {
                    "checkpoint_id": "cp_20240307_120000_abc12345",
                    "name": "Existing CP 1",
                    "timestamp": "2024-03-07T12:00:00",
                    "status": "active",
                    "size_bytes": 100,
                    "metadata": {}
                },
                {
                    "checkpoint_id": "cp_20240307_130000_def67890",
                    "name": "Existing CP 2",
                    "timestamp": "2024-03-07T13:00:00",
                    "status": "archived",
                    "size_bytes": 200,
                    "metadata": {"tags": ["archived"]}
                }
            ]
        }

        with open(index_file, 'w') as f:
            json.dump(index_data, f)

        # Create manager and load index
        manager = CheckpointManager(repo_root=temp_dir)

        assert len(manager.checkpoints) == 2
        assert "cp_20240307_120000_abc12345" in manager.checkpoints
        assert "cp_20240307_130000_def67890" in manager.checkpoints

    def test_load_index_corrupted_file(self, temp_dir):
        """Test handling corrupted index file."""
        checkpoint_dir = temp_dir / ".iflow" / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        index_file = checkpoint_dir / "index.json"

        # Write corrupted JSON
        with open(index_file, 'w') as f:
            f.write("{corrupted json")

        # Should handle gracefully and start with empty checkpoints
        manager = CheckpointManager(repo_root=temp_dir)
        assert len(manager.checkpoints) == 0

    def test_multiple_checkpoints_same_name(self, checkpoint_manager):
        """Test creating multiple checkpoints with the same name."""
        cp1 = checkpoint_manager.create_checkpoint("Same Name", {"id": 1})
        cp2 = checkpoint_manager.create_checkpoint("Same Name", {"id": 2})
        cp3 = checkpoint_manager.create_checkpoint("Same Name", {"id": 3})

        # All should have unique IDs
        assert cp1.checkpoint_id != cp2.checkpoint_id
        assert cp2.checkpoint_id != cp3.checkpoint_id
        assert cp1.checkpoint_id != cp3.checkpoint_id

        # All should be in the manager
        assert len(checkpoint_manager.checkpoints) == 3

    def test_checkpoint_state_modification(self, checkpoint_manager):
        """Test that modifying checkpoint state doesn't affect original."""
        original_data = {"key": "value"}

        checkpoint = checkpoint_manager.create_checkpoint(
            name="State Test",
            state_data=original_data
        )

        # Modify the returned checkpoint's state
        checkpoint.state_data["key"] = "modified"

        # Restore checkpoint - should get original state
        restored_state = checkpoint_manager.restore_checkpoint(checkpoint.checkpoint_id)

        assert restored_state["key"] == "value"
        assert restored_state["key"] != "modified"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])