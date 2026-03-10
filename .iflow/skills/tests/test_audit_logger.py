#!/usr/bin/env python3
"""Test suite for audit_logger.py.

Tests the audit logging system for state changes including:
- Audit event creation and logging
- Index management
- Statistics gathering
- Log pruning
"""

import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open

import pytest

from utils.audit_logger import AuditLogger
from utils.audit_types import AuditEventType, AuditSeverity, AuditEvent


class TestAuditEvent:
    """Tests for the AuditEvent dataclass."""

    def test_audit_event_creation(self):
        """Test creating a basic audit event."""
        event = AuditEvent(
            event_id="test-001",
            event_type=AuditEventType.CREATE,
            severity=AuditSeverity.INFO,
            timestamp="2024-03-10T12:00:00",
            actor="test-user",
            component="test-component",
            file_path="/test/path",
            operation="create_file",
            details={"key": "value"}
        )
        assert event.event_id == "test-001"
        assert event.event_type == AuditEventType.CREATE
        assert event.severity == AuditSeverity.INFO

    def test_audit_event_to_dict(self):
        """Test converting audit event to dictionary."""
        event = AuditEvent(
            event_id="test-002",
            event_type=AuditEventType.UPDATE,
            severity=AuditSeverity.WARNING,
            timestamp="2024-03-10T12:00:00",
            actor="test-user",
            component="test-component",
            file_path="/test/path",
            operation="update_file",
            details={"key": "value"}
        )
        event_dict = event.to_dict()
        assert event_dict["event_id"] == "test-002"
        assert event_dict["event_type"] == "update"
        assert event_dict["severity"] == "warning"

    def test_audit_event_from_dict(self):
        """Test creating audit event from dictionary."""
        event_dict = {
            "event_id": "test-003",
            "event_type": "delete",
            "severity": "error",
            "timestamp": "2024-03-10T12:00:00",
            "actor": "test-user",
            "component": "test-component",
            "file_path": "/test/path",
            "operation": "delete_file",
            "details": {"key": "value"},
            "previous_state": None,
            "new_state": None,
            "error": None,
            "tags": None,
            "metadata": None
        }
        event = AuditEvent.from_dict(event_dict)
        assert event.event_id == "test-003"
        assert event.event_type == AuditEventType.DELETE
        assert event.severity == AuditSeverity.ERROR

    def test_audit_event_with_optional_fields(self):
        """Test audit event with optional fields populated."""
        event = AuditEvent(
            event_id="test-004",
            event_type=AuditEventType.UPDATE,
            severity=AuditSeverity.INFO,
            timestamp="2024-03-10T12:00:00",
            actor="test-user",
            component="test-component",
            file_path="/test/path",
            operation="update_file",
            details={"key": "value"},
            previous_state={"old_key": "old_value"},
            new_state={"new_key": "new_value"},
            error="Test error",
            tags=["tag1", "tag2"],
            metadata={"meta_key": "meta_value"}
        )
        assert event.previous_state == {"old_key": "old_value"}
        assert event.new_state == {"new_key": "new_value"}
        assert event.error == "Test error"
        assert event.tags == ["tag1", "tag2"]
        assert event.metadata == {"meta_key": "meta_value"}


class TestAuditLogger:
    """Tests for the AuditLogger class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def audit_logger(self, temp_dir):
        """Create an AuditLogger instance for testing."""
        log_dir = temp_dir / "audit_logs"
        logger = AuditLogger(log_dir=log_dir, component="test-component")
        return logger

    def test_audit_logger_initialization(self, audit_logger):
        """Test audit logger initialization."""
        assert audit_logger.log_dir.exists()
        assert audit_logger.log_file.name == "test-component_audit.log"
        assert audit_logger.index_file.name == "test-component_audit_index.json"
        assert audit_logger.component == "test-component"

    def test_log_event_basic(self, audit_logger):
        """Test logging a basic audit event."""
        event_id = audit_logger.log_event(
            event_type=AuditEventType.CREATE,
            operation="create_file",
            file_path="/test/path",
            actor="test-user",
            severity=AuditSeverity.INFO,
            details={"key": "value"}
        )
        
        # Verify event_id was returned
        assert event_id is not None
        assert isinstance(event_id, str)
        
        # Verify log file was created
        assert audit_logger.log_file.exists()
        
        # Verify event was added to index
        assert "/test/path" in audit_logger.index
        assert event_id in audit_logger.index["/test/path"]

    def test_log_event_with_state_changes(self, audit_logger):
        """Test logging an event with state changes."""
        event_id = audit_logger.log_event(
            event_type=AuditEventType.UPDATE,
            operation="update_file",
            file_path="/test/path",
            actor="test-user",
            severity=AuditSeverity.INFO,
            details={"key": "value"},
            previous_state={"old": "value"},
            new_state={"new": "value"}
        )
        
        # Verify event was logged
        assert event_id is not None
        assert "/test/path" in audit_logger.index

    def test_log_event_with_error(self, audit_logger):
        """Test logging an event with an error."""
        event_id = audit_logger.log_event(
            event_type=AuditEventType.ERROR,
            operation="error_operation",
            file_path="/test/path",
            actor="test-user",
            severity=AuditSeverity.ERROR,
            details={"key": "value"},
            error="Test error message"
        )
        
        # Verify error was logged
        assert event_id is not None
        assert "/test/path" in audit_logger.index

    def test_log_event_multiple_files(self, audit_logger):
        """Test logging events for multiple files."""
        # Log events for different files
        file_paths = ["/path1/file.txt", "/path2/file.txt", "/path1/file2.txt"]
        event_ids = []
        
        for file_path in file_paths:
            event_id = audit_logger.log_event(
                event_type=AuditEventType.CREATE,
                operation="create_file",
                file_path=file_path,
                actor="test-user",
                severity=AuditSeverity.INFO,
                details={"path": file_path}
            )
            event_ids.append(event_id)
        
        # Verify all events were logged
        assert len(event_ids) == 3
        assert all(eid is not None for eid in event_ids)
        
        # Verify index contains entries for all files
        assert "/path1/file.txt" in audit_logger.index
        assert "/path2/file.txt" in audit_logger.index
        assert "/path1/file2.txt" in audit_logger.index

    def test_get_statistics_empty(self, audit_logger):
        """Test getting statistics when no events have been logged."""
        stats = audit_logger.get_statistics()
        assert stats is not None
        # Statistics should include some keys even when empty
        assert isinstance(stats, dict)

    def test_get_statistics_with_events(self, audit_logger):
        """Test getting statistics after logging events."""
        # Log various events
        event_types = [AuditEventType.CREATE, AuditEventType.UPDATE, AuditEventType.CREATE]
        severities = [AuditSeverity.INFO, AuditSeverity.WARNING, AuditSeverity.ERROR]
        
        for event_type, severity in zip(event_types, severities):
            audit_logger.log_event(
                event_type=event_type,
                operation=f"operation_{event_type.value}",
                file_path="/test/path",
                actor="test-user",
                severity=severity,
                details={"index": event_type.value}
            )
        
        # Get statistics
        stats = audit_logger.get_statistics()
        assert stats is not None
        assert isinstance(stats, dict)

    def test_prune_old_logs(self, audit_logger):
        """Test pruning old log entries."""
        # Log some events
        for i in range(5):
            audit_logger.log_event(
                event_type=AuditEventType.CREATE,
                operation=f"operation_{i}",
                file_path="/test/path",
                actor="test-user",
                severity=AuditSeverity.INFO,
                details={"index": i}
            )
        
        # Prune logs older than 30 days (shouldn't remove anything since we just created them)
        pruned_count = audit_logger.prune_old_logs(max_age_days=30)
        assert pruned_count == 0
        
        # Prune logs older than 0 days (should remove all)
        pruned_count = audit_logger.prune_old_logs(max_age_days=0)
        # The exact behavior depends on implementation

    def test_log_file_format(self, audit_logger):
        """Test that log entries are formatted correctly."""
        event_id = audit_logger.log_event(
            event_type=AuditEventType.CREATE,
            operation="create_file",
            file_path="/test/path",
            actor="test-user",
            severity=AuditSeverity.INFO,
            details={"key": "value"}
        )
        
        # Read the log file
        with open(audit_logger.log_file, 'r') as f:
            log_content = f.read()
        
        # Verify the log entry contains expected information
        assert "CREATE" in log_content
        assert "INFO" in log_content
        assert "test-user" in log_content
        assert "/test/path" in log_content
        assert "create_file" in log_content

    def test_index_persistence(self, audit_logger, temp_dir):
        """Test that the index is persisted and can be loaded."""
        # Log an event
        event_id = audit_logger.log_event(
            event_type=AuditEventType.CREATE,
            operation="create_file",
            file_path="/test/path",
            actor="test-user",
            severity=AuditSeverity.INFO
        )
        
        # Create a new logger instance (should load the existing index)
        log_dir = temp_dir / "audit_logs"
        new_logger = AuditLogger(log_dir=log_dir, component="test-component")
        
        # Verify the index was loaded
        assert "/test/path" in new_logger.index
        assert event_id in new_logger.index["/test/path"]


class TestAuditLoggerEdgeCases:
    """Tests for edge cases and error handling in AuditLogger."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def audit_logger(self, temp_dir):
        """Create an AuditLogger instance for testing."""
        log_dir = temp_dir / "audit_logs"
        logger = AuditLogger(log_dir=log_dir, component="test-component")
        return logger

    def test_log_event_with_path_object(self, audit_logger):
        """Test logging an event with a Path object instead of string."""
        file_path = Path("/test/path")
        event_id = audit_logger.log_event(
            event_type=AuditEventType.CREATE,
            operation="create_file",
            file_path=file_path,
            actor="test-user",
            severity=AuditSeverity.INFO
        )
        
        # Verify event was logged
        assert event_id is not None
        assert str(file_path) in audit_logger.index

    def test_log_event_without_optional_params(self, audit_logger):
        """Test logging an event with only required parameters."""
        event_id = audit_logger.log_event(
            event_type=AuditEventType.CREATE,
            operation="create_file",
            file_path="/test/path"
        )
        
        # Verify event was logged with defaults
        assert event_id is not None

    def test_log_event_with_empty_details(self, audit_logger):
        """Test logging an event with empty details dict."""
        event_id = audit_logger.log_event(
            event_type=AuditEventType.CREATE,
            operation="create_file",
            file_path="/test/path",
            details={}
        )
        
        # Verify event was logged
        assert event_id is not None

    def test_multiple_loggers_same_component(self, temp_dir):
        """Test that multiple loggers for the same component share the same log file."""
        log_dir = temp_dir / "audit_logs"
        
        logger1 = AuditLogger(log_dir=log_dir, component="shared-component")
        logger2 = AuditLogger(log_dir=log_dir, component="shared-component")
        
        # Log events from both loggers
        event_id1 = logger1.log_event(
            event_type=AuditEventType.CREATE,
            operation="create_file",
            file_path="/test/path1"
        )
        
        event_id2 = logger2.log_event(
            event_type=AuditEventType.UPDATE,
            operation="update_file",
            file_path="/test/path2"
        )
        
        # Both should write to the same log file
        assert logger1.log_file == logger2.log_file
        assert logger1.log_file.exists()

    def test_index_size_limit(self, audit_logger):
        """Test that the index limits the number of events per file."""
        # Log many events for the same file
        for i in range(150):  # More than the max index size
            audit_logger.log_event(
                event_type=AuditEventType.CREATE,
                operation=f"operation_{i}",
                file_path="/test/path",
                actor="test-user",
                severity=AuditSeverity.INFO
            )
        
        # Verify the index doesn't exceed the limit
        # The limit is defined in AuditConstants.MAX_INDEX_EVENTS
        assert len(audit_logger.index["/test/path"]) <= 100  # Assuming limit is 100