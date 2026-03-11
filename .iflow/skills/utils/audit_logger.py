#!/usr/bin/env python3
"""
Audit Logging System for State Changes
Tracks all modifications to state files for compliance and debugging.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from copy import deepcopy

from .file_lock import FileLock, FileLockError
from .exceptions import IFlowError
from .constants import AuditConstants
from .structured_logger import StructuredLogger, LogFormat

# Import audit types from separate module
from .audit_types import AuditEventType, AuditSeverity, AuditEvent


class AuditLogger:
    """Manages audit logging for state changes."""
    
    def __init__(self, log_dir: Path, component: str = "iflow-skills"):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory to store audit logs
            component: Component name for log identification
        """
        self.log_dir = Path(log_dir)
        self.component = component
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger for system messages
        self.logger = StructuredLogger(
            name="audit_logger",
            log_dir=self.log_dir / ".logs",
            log_format=LogFormat.JSON
        )
        
        # Create log file
        self.log_file = self.log_dir / f"{component}_audit.log"
        
        # Create index file for quick lookups
        self.index_file = self.log_dir / f"{component}_audit_index.json"
        
        # Load existing index
        self.index = self._load_index()
        
        # Initialize counter
        self._event_counter = 0
    
    def _load_index(self) -> Dict[str, List[str]]:
        """Load audit index from file."""
        if not self.index_file.exists():
            return {}
        
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_index(self):
        """Save audit index to file."""
        try:
            with FileLock(self.index_file, timeout=10):
                with open(self.index_file, 'w') as f:
                    json.dump(self.index, f, indent=2)
        except FileLockError as e:
            self.logger.warning(f"Could not save audit index: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        self._event_counter += 1
        return f"{timestamp}_{self._event_counter:06d}"
    
    def _format_log_entry(self, event: AuditEvent) -> str:
        """Format audit event as log entry."""
        timestamp = event.timestamp
        event_type = event.event_type.value.upper()
        severity = event.severity.value.upper()
        
        entry = (
            f"[{timestamp}] [{severity}] [{event_type}] "
            f"Component: {event.component} | "
            f"Actor: {event.actor} | "
            f"File: {event.file_path} | "
            f"Operation: {event.operation}"
        )
        
        if event.error:
            entry += f" | Error: {event.error}"
        
        if event.tags:
            entry += f" | Tags: {', '.join(event.tags)}"
        
        if event.details:
            details_str = json.dumps(event.details, separators=(',', ':'))
            entry += f" | Details: {details_str}"
        
        return entry
    
    def log_event(
        self,
        event_type: AuditEventType,
        operation: str,
        file_path: Union[str, Path],
        actor: str = "system",
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        error: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            operation: Operation being performed
            file_path: Path to file being operated on
            actor: Who performed the operation
            severity: Severity level
            details: Additional details about the event
            previous_state: State before operation
            new_state: State after operation
            error: Error message if operation failed
            tags: Tags for categorization
            metadata: Additional metadata
        
        Returns:
            Event ID of logged event
        """
        # Convert file_path to string
        if isinstance(file_path, Path):
            file_path = str(file_path)
        
        # Create event
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now().isoformat(),
            actor=actor,
            component=self.component,
            file_path=file_path,
            operation=operation,
            details=details or {},
            previous_state=deepcopy(previous_state) if previous_state else None,
            new_state=deepcopy(new_state) if new_state else None,
            error=error,
            tags=tags,
            metadata=metadata
        )
        
        # Write to log file
        try:
            with FileLock(self.log_file, timeout=5):
                with open(self.log_file, 'a') as f:
                    f.write(self._format_log_entry(event) + '\n')
        except FileLockError as e:
            self.logger.warning(f"Could not write to audit log: {e}")
        
        # Update index
        file_key = file_path
        if file_key not in self.index:
            self.index[file_key] = []
        
        self.index[file_key].insert(0, event.event_id)
        
        # Keep only recent events in index
        if len(self.index[file_key]) > AuditConstants.MAX_INDEX_EVENTS.value:
            self.index[file_key] = self.index[file_key][:AuditConstants.MAX_INDEX_EVENTS.value]
        
        self._save_index()
        
        return event.event_id
    
    def log_state_change(
        self,
        file_path: Union[str, Path],
        operation: str,
        previous_state: Optional[Dict],
        new_state: Dict,
        actor: str = "system",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Log a state change event.
        
        Args:
            file_path: Path to state file
            operation: Operation being performed
            previous_state: State before change
            new_state: State after change
            actor: Who performed the change
            tags: Tags for categorization
        
        Returns:
            Event ID of logged event
        """
        return self.log_event(
            event_type=AuditEventType.UPDATE,
            operation=operation,
            file_path=file_path,
            actor=actor,
            severity=AuditSeverity.INFO,
            previous_state=previous_state,
            new_state=new_state,
            details={
                'change_type': 'state_update',
                'has_previous': previous_state is not None
            },
            tags=tags
        )
    
    def log_error(
        self,
        error: Exception,
        file_path: Optional[Union[str, Path]] = None,
        operation: Optional[str] = None,
        actor: str = "system",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Log an error event.
        
        Args:
            error: The exception that occurred
            file_path: Path to file being operated on (if applicable)
            operation: Operation being performed (if applicable)
            actor: Who was performing the operation
            tags: Tags for categorization
        
        Returns:
            Event ID of logged event
        """
        error_str = str(error)
        if isinstance(error, IFlowError):
            error_details = {
                'code': error.code.value,
                'category': error.category.value,
                'details': error.details
            }
        else:
            error_details = {'type': type(error).__name__}
        
        return self.log_event(
            event_type=AuditEventType.ERROR,
            operation=operation or "unknown",
            file_path=file_path or "unknown",
            actor=actor,
            severity=AuditSeverity.ERROR,
            error=error_str,
            details=error_details,
            tags=tags
        )
    
    def get_events(
        self,
        file_path: Optional[Union[str, Path]] = None,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        limit: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[AuditEvent]:
        """
        Query audit events with optional filters.
        
        Args:
            file_path: Filter by file path
            event_type: Filter by event type
            severity: Filter by severity
            limit: Maximum number of events to return
            tags: Filter by tags
        
        Returns:
            List of audit events matching filters
        """
        events = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    # Parse log line (simplified parsing)
                    # Format: [timestamp] [severity] [type] Component: ... | ...
                    parts = line.split(' | ')
                    if len(parts) < 5:
                        continue
                    
                    # Extract basic info from parts[0]
                    header = parts[0]
                    if not header.startswith('[') or not header.endswith(']'):
                        continue
                    
                    # Parse timestamp, severity, type
                    inner_parts = header[1:-1].split('] [')
                    if len(inner_parts) < 3:
                        continue
                    
                    timestamp = inner_parts[0]
                    severity_str = inner_parts[1]
                    type_str = inner_parts[2]
                    
                    # Parse rest of the line
                    details_str = ' | '.join(parts[1:])
                    
                    # Create minimal event (full parsing would be more complex)
                    # For now, just store the raw log line
                    event = AuditEvent(
                        event_id="",
                        event_type=AuditEventType(type_str.lower()),
                        severity=AuditSeverity(severity_str.lower()),
                        timestamp=timestamp,
                        actor="",
                        component=self.component,
                        file_path="",
                        operation="",
                        details={'raw_line': line}
                    )
                    
                    # Apply filters
                    if file_path:
                        if file_path not in line:
                            continue
                    
                    if event_type and event.event_type != event_type:
                        continue
                    
                    if severity and event.severity != severity:
                        continue
                    
                    if tags and event.tags:
                        if not any(tag in line for tag in tags):
                            continue
                    
                    events.append(event)
                    if limit and len(events) >= limit:
                        break
        
        except IOError:
            pass
        
        return events
    
    def get_file_history(
        self,
        file_path: Union[str, Path],
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get history of changes for a specific file.
        
        Args:
            file_path: Path to file
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        file_key = str(file_path)
        event_ids = self.index.get(file_key, [])
        
        if limit:
            event_ids = event_ids[:limit]
        
        history = []
        for event_id in event_ids:
            event = self._get_event_by_id(event_id)
            if event:
                history.append(event.to_dict())
        
        return history
    
    def _get_event_by_id(self, event_id: str) -> Optional[AuditEvent]:
        """
        Find an event by ID in the log file.
        
        Args:
            event_id: ID of event to find
        
        Returns:
            AuditEvent if found, None otherwise
        """
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if event_id in line:
                        # Parse and return event
                        # Simplified - would need proper parsing in production
                        return AuditEvent(
                            event_id=event_id,
                            event_type=AuditEventType.UNKNOWN,
                            severity=AuditSeverity.INFO,
                            timestamp=datetime.now().isoformat(),
                            actor="",
                            component=self.component,
                            file_path="",
                            operation="",
                            details={'raw_line': line}
                        )
        except IOError:
            pass
        
        return None
    
    def get_statistics(self) -> Dict:
        """
        Get audit log statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_events': 0,
            'by_type': {},
            'by_severity': {},
            'by_file': {},
            'by_actor': {},
            'recent_errors': []
        }
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    stats['total_events'] += 1
                    
                    # Count by type
                    for event_type in AuditEventType:
                        if event_type.value.upper() in line:
                            stats['by_type'][event_type.value] = stats['by_type'].get(event_type.value, 0) + 1
                    
                    # Count by severity
                    for severity in AuditSeverity:
                        if severity.value.upper() in line:
                            stats['by_severity'][severity.value] = stats['by_severity'].get(severity.value, 0) + 1
                    
                    # Count by file
                    if '| File:' in line:
                        file_part = line.split('| File: ')[1].split(' |')[0]
                        stats['by_file'][file_part] = stats['by_file'].get(file_part, 0) + 1
                    
                    # Count by actor
                    if '| Actor:' in line:
                        actor_part = line.split('| Actor: ')[1].split(' |')[0]
                        stats['by_actor'][actor_part] = stats['by_actor'].get(actor_part, 0) + 1
                    
                    # Track recent errors
                    if '[ERROR]' in line:
                        if len(stats['recent_errors']) < 10:
                            stats['recent_errors'].append(line.strip())
        except IOError:
            pass
        
        return stats
    
    def prune_old_logs(self, max_age_days: Optional[int] = None) -> int:
        """
        Remove old log entries based on age.
        
        Args:
            max_age_days: Maximum age of logs to keep in days
        
        Returns:
            Number of log entries removed
        """
        if max_age_days is None:
            max_age_days = AuditConstants.LOG_RETENTION_DAYS.value
        
        cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        
        try:
            temp_file = self.log_file.with_suffix('.tmp')
            removed_count = 0
            
            with open(self.log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    # Parse timestamp
                    if line.startswith('['):
                        timestamp_str = line[1:].split(']')[0]
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if timestamp.timestamp() >= cutoff_date:
                                temp_file.write(line + '\n')
                            else:
                                removed_count += 1
                        except ValueError:
                            # Keep lines we can't parse
                            temp_file.write(line + '\n')
                    else:
                        temp_file.write(line + '\n')
            
            # Replace original file
            temp_file.replace(self.log_file)
            
            # Rebuild index
            self._rebuild_index()
            
            return removed_count
            
        except IOError:
            return 0
    
    def _rebuild_index(self):
        """Rebuild the index from current log file."""
        self.index = {}
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if '| File:' in line:
                        file_part = line.split('| File: ')[1].split(' |')[0]
                        event_id = line.split('] [')[0][1:]
                        
                        if file_part not in self.index:
                            self.index[file_part] = []
                        
                        if event_id not in self.index[file_part]:
                            self.index[file_part].append(event_id)
            
            # Trim index
            for file_key in self.index:
                if len(self.index[file_key]) > AuditConstants.MAX_INDEX_EVENTS.value:
                    self.index[file_key] = self.index[file_key][:AuditConstants.MAX_INDEX_EVENTS.value]
            
            self._save_index()
        except IOError:
            pass


class StateAuditor:
    """
    High-level auditor for state operations.
    Wraps AuditLogger for state-specific auditing.
    """
    
    def __init__(self, audit_dir: Path):
        """
        Initialize state auditor.
        
        Args:
            audit_dir: Directory for audit logs
        """
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.logger = AuditLogger(audit_dir, component="state")
    
    def audit_state_update(
        self,
        state_file: Path,
        operation: str,
        previous_state: Optional[Dict],
        new_state: Dict,
        actor: str = "system"
    ) -> str:
        """
        Audit a state update operation.
        
        Args:
            state_file: Path to state file
            operation: Operation being performed
            previous_state: State before update
            new_state: State after update
            actor: Who performed the update
        
        Returns:
            Event ID of logged event
        """
        return self.logger.log_state_change(
            file_path=state_file,
            operation=operation,
            previous_state=previous_state,
            new_state=new_state,
            actor=actor,
            tags=['state', 'update']
        )
    
    def audit_state_read(
        self,
        state_file: Path,
        actor: str = "system"
    ) -> str:
        """
        Audit a state read operation.
        
        Args:
            state_file: Path to state file
            actor: Who is reading the state
        
        Returns:
            Event ID of logged event
        """
        return self.logger.log_event(
            event_type=AuditEventType.READ,
            operation="read_state",
            file_path=state_file,
            actor=actor,
            severity=AuditSeverity.INFO,
            tags=['state', 'read']
        )
    
    def audit_state_backup(
        self,
        state_file: Path,
        backup_id: str,
        actor: str = "system"
    ) -> str:
        """
        Audit a state backup operation.
        
        Args:
            state_file: Path to state file
            backup_id: ID of the backup
            actor: Who performed the backup
        
        Returns:
            Event ID of logged event
        """
        return self.logger.log_event(
            event_type=AuditEventType.BACKUP,
            operation="backup_state",
            file_path=state_file,
            actor=actor,
            severity=AuditSeverity.INFO,
            details={'backup_id': backup_id},
            tags=['state', 'backup']
        )
    
    def audit_state_restore(
        self,
        state_file: Path,
        backup_id: str,
        actor: str = "system"
    ) -> str:
        """
        Audit a state restore operation.
        
        Args:
            state_file: Path to state file
            backup_id: ID of the backup being restored
            actor: Who performed the restore
        
        Returns:
            Event ID of logged event
        """
        return self.logger.log_event(
            event_type=AuditEventType.RESTORE,
            operation="restore_state",
            file_path=state_file,
            actor=actor,
            severity=AuditSeverity.WARNING,
            details={'backup_id': backup_id},
            tags=['state', 'restore']
        )
    
    def audit_validation(
        self,
        state_file: Path,
        validation_result: bool,
        errors: List[str],
        actor: str = "system"
    ) -> str:
        """
        Audit a state validation operation.
        
        Args:
            state_file: Path to state file being validated
            validation_result: Whether validation passed
            errors: List of validation errors
            actor: Who performed the validation
        
        Returns:
            Event ID of logged event
        """
        return self.logger.log_event(
            event_type=AuditEventType.VALIDATION,
            operation="validate_state",
            file_path=state_file,
            actor=actor,
            severity=AuditSeverity.INFO if validation_result else AuditSeverity.WARNING,
            details={
                'validation_result': validation_result,
                'error_count': len(errors),
                'errors': errors
            },
            tags=['state', 'validation']
        )
    
    def get_state_history(
        self,
        state_file: Path,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get audit history for a state file.
        
        Args:
            state_file: Path to state file
            limit: Maximum number of events to return
        
        Returns:
            List of audit event dictionaries
        """
        return self.logger.get_file_history(state_file, limit)
