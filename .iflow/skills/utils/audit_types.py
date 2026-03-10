"""Audit Types - Core types for the audit logging system.

This module contains the core data structures and enums used throughout
the audit logging system for tracking state changes and operations.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class AuditEventType(Enum):
    """Types of audit events."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    BACKUP = "backup"
    RESTORE = "restore"
    VALIDATION = "validation"
    ERROR = "error"
    SYSTEM = "system"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """A single audit event."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: str
    actor: str
    component: str
    file_path: str
    operation: str
    details: Dict[str, Any]
    previous_state: Optional[Dict] = None
    new_state: Optional[Dict] = None
    error: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary with Enum values as strings."""
        data = asdict(self)
        # Convert Enum values to their string values
        if isinstance(data.get('event_type'), AuditEventType):
            data['event_type'] = data['event_type'].value
        if isinstance(data.get('severity'), AuditSeverity):
            data['severity'] = data['severity'].value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AuditEvent':
        """Create from dictionary."""
        # Convert string enums back to enums
        if isinstance(data.get('event_type'), str):
            data['event_type'] = AuditEventType(data['event_type'])
        if isinstance(data.get('severity'), str):
            data['severity'] = AuditSeverity(data['severity'])
        return cls(**data)
    
    @classmethod
    def create_event(
        cls,
        event_type: AuditEventType,
        severity: AuditSeverity,
        actor: str,
        component: str,
        file_path: str,
        operation: str,
        details: Dict[str, Any],
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        error: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ) -> 'AuditEvent':
        """
        Factory method to create a new audit event.
        
        Args:
            event_type: Type of the audit event
            severity: Severity level
            actor: Who performed the action
            component: Component that generated the event
            file_path: File that was operated on
            operation: Operation that was performed
            details: Additional details about the event
            previous_state: State before the operation
            new_state: State after the operation
            error: Error message if operation failed
            tags: Optional tags for categorization
            metadata: Optional metadata
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            AuditEvent instance
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        return cls(
            event_id=cls._generate_event_id(),
            event_type=event_type,
            severity=severity,
            timestamp=timestamp,
            actor=actor,
            component=component,
            file_path=str(file_path),
            operation=operation,
            details=details,
            previous_state=previous_state,
            new_state=new_state,
            error=error,
            tags=tags or [],
            metadata=metadata or {}
        )
    
    @staticmethod
    def _generate_event_id() -> str:
        """Generate a unique event ID."""
        import uuid
        return str(uuid.uuid4())