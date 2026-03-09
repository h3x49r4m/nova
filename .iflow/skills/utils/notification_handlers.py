"""Notification Handlers - Channel-specific notification handlers.

This module contains the handlers for different notification channels.
Each handler implements the NotificationChannelHandler interface.
"""

import json
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .notification_types import NotificationMessage


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