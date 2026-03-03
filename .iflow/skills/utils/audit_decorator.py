#!/usr/bin/env python3
"""
Audit Decorator
Provides decorator for automatically logging sensitive operations.
"""

import functools
import traceback
from typing import Callable, Any, Optional
from datetime import datetime

from audit_logger import AuditLogger, AuditEventType, AuditSeverity


class AuditDecorator:
    """Decorator class for adding audit logging to functions."""

    @staticmethod
    def audit_sensitive_operation(
        event_type: AuditEventType,
        category: str = "operation",
        description: Optional[str] = None
    ):
        """
        Decorator to audit sensitive operations.

        Args:
            event_type: Type of audit event
            category: Category of the operation
            description: Optional description of the operation

        Example:
            @AuditDecorator.audit_sensitive_operation(
                event_type=AuditEventType.UPDATE,
                category="git_flow",
                description="Branch merge operation"
            )
            def merge_branch(self, branch_name: str):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Get function name for description if not provided
                op_description = description or f"{func.__name__} operation"

                # Try to get actor from args (usually 'self' for methods)
                actor = "system"
                if args and hasattr(args[0], '__class__'):
                    actor = args[0].__class__.__name__

                # Initialize audit logger
                audit_logger = AuditLogger()

                # Log operation start
                audit_logger.log_event(
                    event_type=AuditEventType.SYSTEM,
                    severity=AuditSeverity.INFO,
                    actor=actor,
                    action=f"{op_description} started",
                    category=category,
                    details={
                        "function": func.__name__,
                        "args": str(args[1:]),  # Skip 'self'
                        "kwargs": str(kwargs)
                    }
                )

                try:
                    # Execute the function
                    result = func(*args, **kwargs)

                    # Log successful completion
                    audit_logger.log_event(
                        event_type=event_type,
                        severity=AuditSeverity.INFO,
                        actor=actor,
                        action=f"{op_description} completed",
                        category=category,
                        details={
                            "function": func.__name__,
                            "success": True
                        }
                    )

                    return result

                except Exception as e:
                    # Log failure
                    audit_logger.log_event(
                        event_type=AuditEventType.ERROR,
                        severity=AuditSeverity.ERROR,
                        actor=actor,
                        action=f"{op_description} failed",
                        category=category,
                        details={
                            "function": func.__name__,
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "traceback": traceback.format_exc()
                        }
                    )

                    # Re-raise the exception
                    raise

            return wrapper
        return decorator

    @staticmethod
    def audit_git_operation(operation: str):
        """
        Quick decorator for git operations.

        Args:
            operation: Name of the git operation (e.g., "merge", "commit", "push")

        Example:
            @AuditDecorator.audit_git_operation("merge")
            def merge_branch(self, branch_name: str):
                ...
        """
        return AuditDecorator.audit_sensitive_operation(
            event_type=AuditEventType.UPDATE,
            category="git_operation",
            description=f"Git {operation}"
        )

    @staticmethod
    def audit_state_change(entity_type: str):
        """
        Quick decorator for state changes.

        Args:
            entity_type: Type of entity being changed (e.g., "branch", "phase", "workflow")

        Example:
            @AuditDecorator.audit_state_change("branch")
            def update_branch_status(self, branch_name: str, status: str):
                ...
        """
        return AuditDecorator.audit_sensitive_operation(
            event_type=AuditEventType.UPDATE,
            category="state_change",
            description=f"{entity_type} state change"
        )

    @staticmethod
    def audit_review_action(action: str):
        """
        Quick decorator for review actions.

        Args:
            action: Type of review action (e.g., "approve", "reject", "request_changes")

        Example:
            @AuditDecorator.audit_review_action("approve")
            def approve_review(self, branch_name: str):
                ...
        """
        return AuditDecorator.audit_sensitive_operation(
            event_type=AuditEventType.UPDATE,
            category="review",
            description=f"Review {action}"
        )

    @staticmethod
    def audit_security_event(severity: AuditSeverity = AuditSeverity.WARNING):
        """
        Quick decorator for security-related events.

        Args:
            severity: Severity level for the event

        Example:
            @AuditDecorator.audit_security_event(AuditSeverity.CRITICAL)
            def handle_secret_detected(self, secret: str):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                op_description = f"Security event: {func.__name__}"

                # Try to get actor
                actor = "system"
                if args and hasattr(args[0], '__class__'):
                    actor = args[0].__class__.__name__

                audit_logger = AuditLogger()

                try:
                    result = func(*args, **kwargs)

                    audit_logger.log_event(
                        event_type=AuditEventType.SYSTEM,
                        severity=severity,
                        actor=actor,
                        action=op_description,
                        category="security",
                        details={
                            "function": func.__name__,
                            "timestamp": datetime.now().isoformat()
                        }
                    )

                    return result

                except Exception as e:
                    audit_logger.log_event(
                        event_type=AuditEventType.ERROR,
                        severity=AuditSeverity.CRITICAL,
                        actor=actor,
                        action=f"Security event failed: {func.__name__}",
                        category="security",
                        details={
                            "function": func.__name__,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                    raise

            return wrapper
        return decorator