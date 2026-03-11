"""Tests for structured_logger module."""

import pytest
from pathlib import Path
import sys
import json
import logging
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.structured_logger import (
    LogLevel,
    LogFormat,
    StructuredLogger,
    LogContext
)


class TestLogLevel:
    """Test LogLevel enum."""

    def test_level_values(self):
        """Test that log level values are correct."""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        assert LogLevel.CRITICAL.value == "critical"


class TestLogFormat:
    """Test LogFormat enum."""

    def test_format_values(self):
        """Test that format values are correct."""
        assert LogFormat.JSON.value == "json"
        assert LogFormat.TEXT.value == "text"
        assert LogFormat.CSV.value == "csv"


class TestLogContext:
    """Test LogContext dataclass."""

    def test_context_creation(self):
        """Test creating log context."""
        context = LogContext(
            user_id="user123",
            session_id="session456",
            component="test_component"
        )
        assert context.user_id == "user123"
        assert context.session_id == "session456"

    def test_context_with_metadata(self):
        """Test context with metadata."""
        context = LogContext(
            user_id="user123",
            metadata={"key": "value"}
        )
        assert context.metadata == {"key": "value"}


class TestStructuredLogger:
    """Test StructuredLogger class."""

    def test_initialization_json(self, tmp_path):
        """Test logger initialization with JSON format."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        assert logger.name == "test_logger"
        assert logger.log_format == LogFormat.JSON
        assert logger.log_dir == tmp_path

    def test_initialization_text(self, tmp_path):
        """Test logger initialization with text format."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.TEXT
        )
        assert logger.log_format == LogFormat.TEXT

    def test_log_debug(self, tmp_path):
        """Test debug logging."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.debug("Debug message")
        
        log_file = tmp_path / "test_logger.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "Debug message" in content

    def test_log_info(self, tmp_path):
        """Test info logging."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.info("Info message")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "Info message" in content

    def test_log_warning(self, tmp_path):
        """Test warning logging."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.warning("Warning message")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "Warning message" in content

    def test_log_error(self, tmp_path):
        """Test error logging."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.error("Error message")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "Error message" in content

    def test_log_critical(self, tmp_path):
        """Test critical logging."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.critical("Critical message")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "Critical message" in content

    def test_log_with_context(self, tmp_path):
        """Test logging with context."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        context = LogContext(
            user_id="user123",
            session_id="session456"
        )
        logger.info("Message with context", context=context)
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "user123" in content

    def test_log_with_metadata(self, tmp_path):
        """Test logging with metadata."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.info("Message with metadata", metadata={"key": "value"})
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "key" in content
        assert "value" in content

    def test_log_exception(self, tmp_path):
        """Test logging exception."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logger.exception("An error occurred", exc_info=e)
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "Test exception" in content

    def test_json_format_output(self, tmp_path):
        """Test JSON format output."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.info("Test message")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        # Verify it's valid JSON
        log_entry = json.loads(content.strip().split('\n')[-1])
        assert log_entry["message"] == "Test message"
        assert log_entry["level"] == "info"

    def test_text_format_output(self, tmp_path):
        """Test text format output."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.TEXT
        )
        logger.info("Test message")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "Test message" in content
        assert "INFO" in content

    def test_log_level_filtering(self, tmp_path):
        """Test log level filtering."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON,
            min_level=LogLevel.WARNING
        )
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content

    def test_log_rotation(self, tmp_path):
        """Test log rotation."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON,
            max_bytes=100,
            backup_count=3
        )
        
        # Write enough logs to trigger rotation
        for i in range(10):
            logger.info(f"Message {i}: " + "x" * 50)
        
        # Check for backup files
        backup_files = list(tmp_path.glob("test_logger.log.*"))
        assert len(backup_files) > 0

    def test_multiple_loggers(self, tmp_path):
        """Test multiple independent loggers."""
        logger1 = StructuredLogger(
            name="logger1",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger2 = StructuredLogger(
            name="logger2",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        
        logger1.info("Message from logger1")
        logger2.info("Message from logger2")
        
        log_file1 = tmp_path / "logger1.log"
        log_file2 = tmp_path / "logger2.log"
        
        content1 = log_file1.read_text()
        content2 = log_file2.read_text()
        
        assert "Message from logger1" in content1
        assert "Message from logger2" in content2

    def test_add_context(self, tmp_path):
        """Test adding context to logger."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.add_context("request_id", "req123")
        logger.info("Message with added context")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "req123" in content

    def test_remove_context(self, tmp_path):
        """Test removing context from logger."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.add_context("request_id", "req123")
        logger.remove_context("request_id")
        logger.info("Message without context")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "req123" not in content

    def test_clear_context(self, tmp_path):
        """Test clearing all context."""
        logger = StructuredLogger(
            name="test_logger",
            log_dir=tmp_path,
            log_format=LogFormat.JSON
        )
        logger.add_context("request_id", "req123")
        logger.add_context("user_id", "user456")
        logger.clear_context()
        logger.info("Message with cleared context")
        
        log_file = tmp_path / "test_logger.log"
        content = log_file.read_text()
        assert "req123" not in content
        assert "user456" not in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])