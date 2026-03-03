"""Notification System - Sends notifications for review results.

This module provides notification functionality for code review results,
supporting multiple notification channels and configurable triggers.
"""

import json
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import IFlowError, ErrorCode


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


class NotificationChannelHandler(ABC):
    """Abstract base class for notification channel handlers."""
    
    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        """
        Send a notification message.
        
        Args:
            message: NotificationMessage to send
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate channel configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class EmailNotificationHandler(NotificationChannelHandler):
    """Handler for email notifications."""
    
    REQUIRED_CONFIG = ["smtp_server", "smtp_port", "from_email", "to_emails"]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email handler.
        
        Args:
            config: Email configuration
        """
        self.config = config
        self.smtp_server = config.get("smtp_server", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.from_email = config.get("from_email", "")
        self.from_name = config.get("from_name", "iFlow Review")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.use_tls = config.get("use_tls", True)
        self.to_emails = config.get("to_emails", [])
    
    def send(self, message: NotificationMessage) -> bool:
        """Send email notification."""
        try:
            # Create message
            subject = f"[{message.severity.value.upper()}] {message.title}"
            
            # Build email body
            body = self._build_email_body(message)
            
            msg = MIMEText(body, "html")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = ", ".join(message.recipients or self.to_emails)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            return False
    
    def _build_email_body(self, message: NotificationMessage) -> str:
        """Build HTML email body."""
        severity_colors = {
            "info": "#0066cc",
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545",
            "critical": "#343a40"
        }
        
        color = severity_colors.get(message.severity.value, "#6c757d")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .header {{ background-color: {color}; color: white; padding: 20px; }}
                .content {{ padding: 20px; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .timestamp {{ color: #6c757d; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{message.title}</h2>
            </div>
            <div class="content">
                <p>{message.message}</p>
                <div class="details">
                    <h3>Details:</h3>
                    <pre>{json.dumps(message.details, indent=2)}</pre>
                </div>
                <p class="timestamp">Triggered at: {message.timestamp}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate email configuration."""
        missing = [k for k in self.REQUIRED_CONFIG if k not in config]
        
        if missing:
            return False, f"Missing required config: {', '.join(missing)}"
        
        return True, None


class SlackNotificationHandler(NotificationChannelHandler):
    """Handler for Slack notifications."""
    
    REQUIRED_CONFIG = ["webhook_url"]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Slack handler.
        
        Args:
            config: Slack configuration
        """
        self.config = config
        self.webhook_url = config.get("webhook_url", "")
        self.channel = config.get("channel", "#reviews")
        self.username = config.get("username", "iFlow Review Bot")
        self.icon_emoji = config.get("icon_emoji", ":robot_face:")
    
    def send(self, message: NotificationMessage) -> bool:
        """Send Slack notification."""
        try:
            import requests
            
            # Build Slack message
            slack_msg = self._build_slack_message(message)
            
            # Send to webhook
            response = requests.post(self.webhook_url, json=slack_msg, timeout=10)
            response.raise_for_status()
            
            return True
        
        except Exception as e:
            return False
    
    def _build_slack_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """Build Slack message format."""
        severity_colors = {
            "info": "#0066cc",
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545",
            "critical": "#343a40"
        }
        
        color = severity_colors.get(message.severity.value, "#6c757d")
        
        slack_msg = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [{
                "color": color,
                "title": message.title,
                "text": message.message,
                "fields": [
                    {
                        "title": "Trigger",
                        "value": message.trigger.value.replace("_", " ").title(),
                        "short": True
                    },
                    {
                        "title": "Severity",
                        "value": message.severity.value.upper(),
                        "short": True
                    }
                ],
                "footer": f"iFlow Review • {message.timestamp}"
            }]
        }
        
        # Add details if available
        if message.details:
            slack_msg["attachments"][0]["fields"].append({
                "title": "Details",
                "value": f"```{json.dumps(message.details, indent=2)}```",
                "short": False
            })
        
        return slack_msg
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate Slack configuration."""
        missing = [k for k in self.REQUIRED_CONFIG if k not in config]
        
        if missing:
            return False, f"Missing required config: {', '.join(missing)}"
        
        return True, None


class WebhookNotificationHandler(NotificationChannelHandler):
    """Handler for webhook notifications."""
    
    REQUIRED_CONFIG = ["url"]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize webhook handler.
        
        Args:
            config: Webhook configuration
        """
        self.config = config
        self.url = config.get("url", "")
        self.method = config.get("method", "POST")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 10)
    
    def send(self, message: NotificationMessage) -> bool:
        """Send webhook notification."""
        try:
            import requests
            
            # Build payload
            payload = message.to_dict()
            
            # Send webhook
            response = requests.request(
                self.method,
                self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return True
        
        except Exception as e:
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate webhook configuration."""
        missing = [k for k in self.REQUIRED_CONFIG if k not in config]
        
        if missing:
            return False, f"Missing required config: {', '.join(missing)}"
        
        return True, None


class CLINotificationHandler(NotificationChannelHandler):
    """Handler for CLI notifications."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize CLI handler.
        
        Args:
            config: CLI configuration
        """
        self.config = config or {}
    
    def send(self, message: NotificationMessage) -> bool:
        """Send CLI notification."""
        try:
            # Build CLI message
            output = self._build_cli_message(message)
            
            # Print to console
            print(output)
            
            return True
        
        except Exception as e:
            return False
    
    def _build_cli_message(self, message: NotificationMessage) -> str:
        """Build CLI message format."""
        severity_icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨"
        }
        
        icon = severity_icons.get(message.severity.value, "📋")
        
        lines = [
            f"{icon} {message.title}",
            "-" * 50,
            f"Severity: {message.severity.value.upper()}",
            f"Trigger: {message.trigger.value.replace('_', ' ').title()}",
            f"Message: {message.message}",
            f"Time: {message.timestamp}"
        ]
        
        if message.details:
            lines.append("\nDetails:")
            lines.append(json.dumps(message.details, indent=2))
        
        return "\n".join(lines)
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate CLI configuration (always valid)."""
        return True, None


class FileNotificationHandler(NotificationChannelHandler):
    """Handler for file-based notifications."""
    
    REQUIRED_CONFIG = ["file_path"]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize file handler.
        
        Args:
            config: File configuration
        """
        self.config = config
        self.file_path = Path(config.get("file_path", "notifications.log"))
        self.format = config.get("format", "json")
    
    def send(self, message: NotificationMessage) -> bool:
        """Send file notification."""
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build message
            if self.format == "json":
                content = json.dumps(message.to_dict(), indent=2)
            else:
                content = self._build_text_message(message)
            
            # Append to file
            with open(self.file_path, 'a') as f:
                f.write(content + "\n")
            
            return True
        
        except Exception as e:
            return False
    
    def _build_text_message(self, message: NotificationMessage) -> str:
        """Build text message format."""
        lines = [
            f"[{message.timestamp}]",
            f"Channel: {message.channel.value}",
            f"Trigger: {message.trigger.value}",
            f"Severity: {message.severity.value}",
            f"Title: {message.title}",
            f"Message: {message.message}"
        ]
        
        if message.details:
            lines.append(f"Details: {json.dumps(message.details)}")
        
        return " | ".join(lines)
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate file configuration."""
        missing = [k for k in self.REQUIRED_CONFIG if k not in config]
        
        if missing:
            return False, f"Missing required config: {', '.join(missing)}"
        
        return True, None


class NotificationSystem:
    """Manages notifications for code reviews."""
    
    def __init__(self, repo_root: Path):
        """
        Initialize notification system.
        
        Args:
            repo_root: Repository root directory
        """
        self.repo_root = repo_root
        self.config_file = repo_root / ".iflow" / "skills" / "notification_config.json"
        
        self.configs: List[NotificationConfig] = []
        self.handlers: Dict[NotificationChannel, NotificationChannelHandler] = {}
        self.notification_history: List[NotificationMessage] = []
        
        self._load_config()
        self._initialize_handlers()
    
    def _load_config(self):
        """Load notification configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                for config_data in data.get("channels", []):
                    config = NotificationConfig.from_dict(config_data)
                    self.configs.append(config)
            
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_config(self):
        """Save notification configuration."""
        data = {
            "channels": [c.to_dict() for c in self.configs],
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save notification config: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _initialize_handlers(self):
        """Initialize notification handlers."""
        for config in self.configs:
            if not config.enabled:
                continue
            
            handler = self._create_handler(config)
            if handler:
                self.handlers[config.channel] = handler
    
    def _create_handler(
        self,
        config: NotificationConfig
    ) -> Optional[NotificationChannelHandler]:
        """
        Create handler for notification channel.
        
        Args:
            config: Notification configuration
            
        Returns:
            NotificationChannelHandler or None
        """
        handlers = {
            NotificationChannel.EMAIL: EmailNotificationHandler,
            NotificationChannel.SLACK: SlackNotificationHandler,
            NotificationChannel.WEBHOOK: WebhookNotificationHandler,
            NotificationChannel.CLI: CLINotificationHandler,
            NotificationChannel.FILE: FileNotificationHandler
        }
        
        handler_class = handlers.get(config.channel)
        if not handler_class:
            return None
        
        try:
            return handler_class(config.config)
        except Exception:
            return None
    
    def add_channel(self, config: NotificationConfig):
        """
        Add a notification channel.
        
        Args:
            config: Notification configuration
        """
        self.configs.append(config)
        self._save_config()
        self._initialize_handlers()
    
    def remove_channel(self, channel: NotificationChannel):
        """
        Remove a notification channel.
        
        Args:
            channel: Channel to remove
        """
        self.configs = [c for c in self.configs if c.channel != channel]
        
        if channel in self.handlers:
            del self.handlers[channel]
        
        self._save_config()
    
    def should_notify(
        self,
        trigger: NotificationTrigger,
        severity: NotificationSeverity
    ) -> bool:
        """
        Check if notification should be sent.
        
        Args:
            trigger: Trigger event
            severity: Severity level
            
        Returns:
            True if should notify
        """
        for config in self.configs:
            if not config.enabled:
                continue
            
            if config.triggers and trigger not in config.triggers:
                continue
            
            if config.min_severity:
                if self._compare_severity(severity, config.min_severity) < 0:
                    continue
            
            return True
        
        return False
    
    def _compare_severity(
        self,
        severity1: NotificationSeverity,
        severity2: NotificationSeverity
    ) -> int:
        """
        Compare two severity levels.
        
        Args:
            severity1: First severity
            severity2: Second severity
            
        Returns:
            -1 if severity1 < severity2, 0 if equal, 1 if severity1 > severity2
        """
        severity_order = [
            NotificationSeverity.INFO,
            NotificationSeverity.SUCCESS,
            NotificationSeverity.WARNING,
            NotificationSeverity.ERROR,
            NotificationSeverity.CRITICAL
        ]
        
        try:
            idx1 = severity_order.index(severity1)
            idx2 = severity_order.index(severity2)
            return (idx1 > idx2) - (idx1 < idx2)
        except ValueError:
            return 0
    
    def send_notification(
        self,
        message: NotificationMessage
    ) -> bool:
        """
        Send notification message.
        
        Args:
            message: NotificationMessage to send
            
        Returns:
            True if any handler succeeded
        """
        success = False
        
        for channel, handler in self.handlers.items():
            try:
                if handler.send(message):
                    success = True
            except Exception:
                pass
        
        self.notification_history.append(message)
        
        return success
    
    def notify(
        self,
        trigger: NotificationTrigger,
        title: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        recipients: Optional[List[str]] = None
    ) -> bool:
        """
        Send notification.
        
        Args:
            trigger: Trigger event
            title: Notification title
            message: Notification message
            severity: Severity level
            details: Additional details
            recipients: Recipients list
            
        Returns:
            True if notification was sent
        """
        if not self.should_notify(trigger, severity):
            return False
        
        # Send to all enabled channels
        for config in self.configs:
            if not config.enabled:
                continue
            
            if config.triggers and trigger not in config.triggers:
                continue
            
            if config.min_severity:
                if self._compare_severity(severity, config.min_severity) < 0:
                    continue
            
            # Create message for this channel
            msg = NotificationMessage(
                channel=config.channel,
                trigger=trigger,
                severity=severity,
                title=title,
                message=message,
                details=details or {},
                recipients=recipients or []
            )
            
            self.send_notification(msg)
        
        return True
    
    def get_notification_history(
        self,
        limit: int = 100
    ) -> List[NotificationMessage]:
        """
        Get notification history.
        
        Args:
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification messages
        """
        return self.notification_history[-limit:]


def create_notification_system(repo_root: Path) -> NotificationSystem:
    """Create a notification system instance."""
    return NotificationSystem(repo_root)