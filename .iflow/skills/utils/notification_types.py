"""Notification Types - Enums and data structures for the notification system.

This module contains the core types, enums, and dataclasses used
throughout the notification system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    CLI = "cli"
    FILE = "file"


class NotificationSeverity(Enum):
    """Notification severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationTrigger(Enum):
    """Notification trigger events."""
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_FAILED = "review_failed"
    CRITICAL_FINDING = "critical_finding"
    HIGH_SEVERITY = "high_severity"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    BLOCKING_RULE_FAILED = "blocking_rule_failed"
    TOOL_ERROR = "tool_error"


@dataclass
class NotificationConfig:
    """Configuration for a notification channel."""
    channel: NotificationChannel
    enabled: bool = True
    triggers: List[NotificationTrigger] = field(default_factory=list)
    min_severity: Optional[NotificationSeverity] = None
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel": self.channel.value,
            "enabled": self.enabled,
            "triggers": [t.value for t in self.triggers],
            "min_severity": self.min_severity.value if self.min_severity else None,
            "config": self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationConfig':
        """Create from dictionary."""
        return cls(
            channel=NotificationChannel(data["channel"]),
            enabled=data.get("enabled", True),
            triggers=[NotificationTrigger(t) for t in data.get("triggers", [])],
            min_severity=NotificationSeverity(data["min_severity"]) if data.get("min_severity") else None,
            config=data.get("config", {})
        )


@dataclass
class NotificationMessage:
    """Represents a notification message."""
    channel: NotificationChannel
    trigger: NotificationTrigger
    severity: NotificationSeverity
    title: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recipients: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel": self.channel.value,
            "trigger": self.trigger.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "recipients": self.recipients,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationMessage':
        """Create from dictionary."""
        return cls(
            channel=NotificationChannel(data["channel"]),
            trigger=NotificationTrigger(data["trigger"]),
            severity=NotificationSeverity(data["severity"]),
            title=data["title"],
            message=data["message"],
            details=data.get("details", {}),
            recipients=data.get("recipients", []),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )