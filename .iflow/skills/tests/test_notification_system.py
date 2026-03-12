"""Tests for notification_system module."""

import pytest
from pathlib import Path
import sys
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.notification_system import (
    NotificationSeverity,
    NotificationChannel,
    NotificationMessage,
    NotificationConfig,
    NotificationSystem
)
from utils.exceptions import IFlowError


class TestNotificationSeverity:
    """Test NotificationSeverity enum."""

    def test_severity_values(self):
        """Test that severity values are correct."""
        assert NotificationSeverity.INFO.value == "info"
        assert NotificationSeverity.SUCCESS.value == "success"
        assert NotificationSeverity.WARNING.value == "warning"
        assert NotificationSeverity.ERROR.value == "error"
        assert NotificationSeverity.CRITICAL.value == "critical"


class TestNotificationChannel:
    """Test NotificationChannel enum."""

    def test_channel_values(self):
        """Test that channel values are correct."""
        assert NotificationChannel.CLI.value == "cli"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.SLACK.value == "slack"
        assert NotificationChannel.WEBHOOK.value == "webhook"


class TestNotificationMessage:
    """Test NotificationMessage dataclass."""

    def test_message_creation(self):
        """Test creating a notification message."""
        message = NotificationMessage(
            title="Test",
            content="Test content",
            severity=NotificationSeverity.INFO,
            channel=NotificationChannel.CLI
        )
        assert message.title == "Test"
        assert message.content == "Test content"
        assert message.severity == NotificationSeverity.INFO
        assert message.channel == NotificationChannel.CLI

    def test_message_with_optional_fields(self):
        """Test message with optional fields."""
        message = NotificationMessage(
            title="Test",
            content="Test content",
            severity=NotificationSeverity.WARNING,
            channel=NotificationChannel.EMAIL,
            recipients=["test@example.com"],
            metadata={"key": "value"}
        )
        assert message.recipients == ["test@example.com"]
        assert message.metadata == {"key": "value"}


class TestNotificationConfig:
    """Test NotificationConfig dataclass."""

    def test_config_creation(self):
        """Test creating notification config."""
        config = NotificationConfig(
            enabled_channels=[NotificationChannel.CLI],
            cli_enabled=True,
            email_enabled=False,
            slack_enabled=False,
            webhook_enabled=False
        )
        assert config.cli_enabled is True
        assert config.email_enabled is False


class TestNotificationSystem:
    """Test NotificationSystem class."""

    def test_system_initialization(self, tmp_path):
        """Test system initialization."""
        system = NotificationSystem(config_dir=tmp_path)
        assert system is not None
        assert system.config_dir == tmp_path

    def test_send_cli_notification(self, tmp_path, capsys):
        """Test sending CLI notification."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Test",
            content="Test content",
            severity=NotificationSeverity.INFO,
            channel=NotificationChannel.CLI
        )
        result = system.send(message)
        assert result is True
        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_send_with_cli_disabled(self, tmp_path, capsys):
        """Test sending notification when CLI is disabled."""
        config = NotificationConfig(
            enabled_channels=[],
            cli_enabled=False
        )
        system = NotificationSystem(config_dir=tmp_path, config=config)
        message = NotificationMessage(
            title="Test",
            content="Test content",
            severity=NotificationSeverity.INFO,
            channel=NotificationChannel.CLI
        )
        result = system.send(message)
        assert result is True  # Should succeed even if channel disabled

    def test_send_message_with_metadata(self, tmp_path):
        """Test sending message with metadata."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Test",
            content="Test content",
            severity=NotificationSeverity.INFO,
            channel=NotificationChannel.CLI,
            metadata={"key": "value"}
        )
        result = system.send(message)
        assert result is True

    def test_send_message_with_recipients(self, tmp_path):
        """Test sending message with recipients."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Test",
            content="Test content",
            severity=NotificationSeverity.INFO,
            channel=NotificationChannel.CLI,
            recipients=["test@example.com"]
        )
        result = system.send(message)
        assert result is True

    def test_send_error_message(self, tmp_path, capsys):
        """Test sending error message."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Error",
            content="Error occurred",
            severity=NotificationSeverity.ERROR,
            channel=NotificationChannel.CLI
        )
        result = system.send(message)
        assert result is True
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_send_critical_message(self, tmp_path, capsys):
        """Test sending critical message."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Critical",
            content="Critical issue",
            severity=NotificationSeverity.CRITICAL,
            channel=NotificationChannel.CLI
        )
        result = system.send(message)
        assert result is True
        captured = capsys.readouterr()
        assert "Critical" in captured.out

    def test_send_success_message(self, tmp_path, capsys):
        """Test sending success message."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Success",
            content="Operation completed",
            severity=NotificationSeverity.SUCCESS,
            channel=NotificationChannel.CLI
        )
        result = system.send(message)
        assert result is True
        captured = capsys.readouterr()
        assert "Success" in captured.out

    def test_send_warning_message(self, tmp_path, capsys):
        """Test sending warning message."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Warning",
            content="Warning issued",
            severity=NotificationSeverity.WARNING,
            channel=NotificationChannel.CLI
        )
        result = system.send(message)
        assert result is True
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_send_with_timestamp(self, tmp_path):
        """Test sending message with timestamp."""
        system = NotificationSystem(config_dir=tmp_path)
        message = NotificationMessage(
            title="Test",
            content="Test content",
            severity=NotificationSeverity.INFO,
            channel=NotificationChannel.CLI,
            timestamp=datetime.now()
        )
        result = system.send(message)
        assert result is True

    def test_load_config(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "notification_config.json"
        config_file.write_text('{"cli_enabled": true, "email_enabled": false}')
        system = NotificationSystem(config_dir=tmp_path)
        assert system is not None

    def test_save_config(self, tmp_path):
        """Test saving configuration to file."""
        system = NotificationSystem(config_dir=tmp_path)
        system.save_config()
        config_file = tmp_path / "notification_config.json"
        assert config_file.exists()

    def test_bulk_send(self, tmp_path):
        """Test sending multiple messages."""
        system = NotificationSystem(config_dir=tmp_path)
        messages = [
            NotificationMessage(
                title=f"Message {i}",
                content=f"Content {i}",
                severity=NotificationSeverity.INFO,
                channel=NotificationChannel.CLI
            )
            for i in range(3)
        ]
        results = system.bulk_send(messages)
        assert len(results) == 3
        assert all(results) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])