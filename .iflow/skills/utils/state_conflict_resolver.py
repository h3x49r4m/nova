#!/usr/bin/env python3
"""
State Conflict Resolution Module
Handles conflicts when multiple processes attempt to update shared state files.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from copy import deepcopy

from .file_lock import FileLock, FileLockError
from .audit_logger import AuditLogger, AuditEventType, AuditSeverity


class ConflictStrategy(Enum):
    """Strategies for resolving state conflicts."""
    FAIL = "fail"                    # Fail and return error
    USE_NEWEST = "use_newest"        # Use the most recent version
    USE_LATEST_MODIFICATION = "use_latest_modification"  # Use version with latest modification
    MERGE_DEEP = "merge_deep"        # Deep merge both versions
    OVERWRITE = "overwrite"          # Overwrite with new version
    MANUAL = "manual"                # Require manual resolution


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""
    file_path: Path
    expected_version: str
    actual_version: str
    expected_hash: str
    actual_hash: str
    expected_modified: str
    actual_modified: str
    conflicting_fields: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'file_path': str(self.file_path),
            'expected_version': self.expected_version,
            'actual_version': self.actual_version,
            'expected_hash': self.expected_hash,
            'actual_hash': self.actual_hash,
            'expected_modified': self.expected_modified,
            'actual_modified': self.actual_modified,
            'conflicting_fields': self.conflicting_fields
        }


@dataclass
class ResolutionResult:
    """Result of conflict resolution."""
    success: bool
    resolved_state: Optional[Dict[str, Any]]
    conflict_info: Optional[ConflictInfo]
    resolution_strategy: ConflictStrategy
    timestamp: str
    message: str
    
    def to_dict(self) -> Dict:
        result = {
            'success': self.success,
            'resolution_strategy': self.resolution_strategy.value,
            'timestamp': self.timestamp,
            'message': self.message
        }
        if self.resolved_state:
            result['resolved_state'] = self.resolved_state
        if self.conflict_info:
            result['conflict_info'] = self.conflict_info.to_dict()
        return result


class StateConflictResolver:
    """
    Resolves conflicts in shared state files.
    Uses optimistic concurrency control with version tracking.
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize state conflict resolver.
        
        Args:
            audit_logger: Optional audit logger for tracking resolutions
        """
        self.audit_logger = audit_logger
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash of state data."""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def _extract_version(self, state: Dict[str, Any]) -> str:
        """Extract version from state."""
        return state.get('_version', '0')
    
    def _extract_modified(self, state: Dict[str, Any]) -> str:
        """Extract modified timestamp from state."""
        return state.get('_modified', state.get('updated_at', datetime.now().isoformat()))
    
    def _find_conflicting_fields(self, expected: Dict, actual: Dict, path: str = "") -> List[str]:
        """
        Find fields that differ between two states.
        
        Args:
            expected: Expected state
            actual: Actual state
            path: Current path in the state (for nested structures)
        
        Returns:
            List of conflicting field paths
        """
        conflicts = []
        
        # Check for keys in expected but not in actual
        for key in expected.keys():
            if key not in actual:
                conflicts.append(f"{path}.{key}" if path else key)
                continue
            
            # Recursively check nested dictionaries
            if isinstance(expected[key], dict) and isinstance(actual[key], dict):
                nested_conflicts = self._find_conflicting_fields(
                    expected[key],
                    actual[key],
                    f"{path}.{key}" if path else key
                )
                conflicts.extend(nested_conflicts)
            # Check for different values
            elif expected[key] != actual[key]:
                conflicts.append(f"{path}.{key}" if path else key)
        
        # Check for keys in actual but not in expected (additions)
        for key in actual.keys():
            if key not in expected and key not in ['_version', '_modified']:
                conflicts.append(f"{path}.{key}" if path else key)
        
        return conflicts
    
    def detect_conflict(
        self,
        file_path: Path,
        expected_state: Dict[str, Any],
        actual_state: Optional[Dict[str, Any]] = None
    ) -> Optional[ConflictInfo]:
        """
        Detect if there's a conflict between expected and actual state.
        
        Args:
            file_path: Path to state file
            expected_state: Expected state data
            actual_state: Actual state data (if None, will read from file)
        
        Returns:
            ConflictInfo if conflict detected, None otherwise
        """
        # Read actual state if not provided
        if actual_state is None and file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    actual_state = json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        
        if actual_state is None:
            return None
        
        # Extract metadata
        expected_version = self._extract_version(expected_state)
        actual_version = self._extract_version(actual_state)
        
        # Check for version mismatch
        if expected_version != actual_version:
            expected_hash = self._calculate_hash(expected_state)
            actual_hash = self._calculate_hash(actual_state)
            expected_modified = self._extract_modified(expected_state)
            actual_modified = self._extract_modified(actual_state)
            
            # Find conflicting fields
            conflicting_fields = self._find_conflicting_fields(expected_state, actual_state)
            
            return ConflictInfo(
                file_path=file_path,
                expected_version=expected_version,
                actual_version=actual_version,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                expected_modified=expected_modified,
                actual_modified=actual_modified,
                conflicting_fields=conflicting_fields
            )
        
        return None
    
    def resolve_conflict(
        self,
        file_path: Path,
        expected_state: Dict[str, Any],
        new_state: Dict[str, Any],
        strategy: ConflictStrategy = ConflictStrategy.USE_NEWEST,
        actual_state: Optional[Dict[str, Any]] = None
    ) -> ResolutionResult:
        """
        Resolve a conflict using the specified strategy.
        
        Args:
            file_path: Path to state file
            expected_state: Expected state when operation started
            new_state: New state to write
            strategy: Conflict resolution strategy
            actual_state: Actual current state (if None, will read from file)
        
        Returns:
            ResolutionResult with outcome
        """
        timestamp = datetime.now().isoformat()
        
        # Detect conflict
        conflict = self.detect_conflict(file_path, expected_state, actual_state)
        
        if conflict is None:
            # No conflict, write new state
            return ResolutionResult(
                success=True,
                resolved_state=new_state,
                conflict_info=None,
                resolution_strategy=ConflictStrategy.USE_NEWEST,
                timestamp=timestamp,
                message="No conflict detected, proceeding with update"
            )
        
        # Resolve based on strategy
        if strategy == ConflictStrategy.FAIL:
            return ResolutionResult(
                success=False,
                resolved_state=None,
                conflict_info=conflict,
                resolution_strategy=strategy,
                timestamp=timestamp,
                message=f"Conflict detected in {file_path}: version mismatch (expected {conflict.expected_version}, got {conflict.actual_version})"
            )
        
        elif strategy == ConflictStrategy.USE_NEWEST:
            # Use version with most recent timestamp
            if conflict.actual_modified > conflict.expected_modified:
                resolved_state = actual_state
                message = f"Using actual state (newer: {conflict.actual_modified})"
            else:
                resolved_state = new_state
                message = f"Using new state (newer: {conflict.expected_modified})"
            
            return ResolutionResult(
                success=True,
                resolved_state=resolved_state,
                conflict_info=conflict,
                resolution_strategy=strategy,
                timestamp=timestamp,
                message=message
            )
        
        elif strategy == ConflictStrategy.USE_LATEST_MODIFICATION:
            # Use version with latest modification timestamp
            if conflict.actual_modified > conflict.expected_modified:
                resolved_state = actual_state
                message = f"Using actual state (latest modification: {conflict.actual_modified})"
            else:
                resolved_state = new_state
                message = f"Using new state (latest modification: {conflict.expected_modified})"
            
            return ResolutionResult(
                success=True,
                resolved_state=resolved_state,
                conflict_info=conflict,
                resolution_strategy=strategy,
                timestamp=timestamp,
                message=message
            )
        
        elif strategy == ConflictStrategy.MERGE_DEEP:
            # Deep merge both states
            resolved_state = self._deep_merge(actual_state, new_state)
            
            return ResolutionResult(
                success=True,
                resolved_state=resolved_state,
                conflict_info=conflict,
                resolution_strategy=strategy,
                timestamp=timestamp,
                message=f"Merged {len(conflict.conflicting_fields)} conflicting fields"
            )
        
        elif strategy == ConflictStrategy.OVERWRITE:
            # Overwrite with new state
            resolved_state = new_state
            
            return ResolutionResult(
                success=True,
                resolved_state=resolved_state,
                conflict_info=conflict,
                resolution_strategy=strategy,
                timestamp=timestamp,
                message="Overwrote actual state with new state"
            )
        
        elif strategy == ConflictStrategy.MANUAL:
            # Cannot automatically resolve
            return ResolutionResult(
                success=False,
                resolved_state=None,
                conflict_info=conflict,
                resolution_strategy=strategy,
                timestamp=timestamp,
                message=f"Manual resolution required for {len(conflict.conflicting_fields)} conflicting fields: {', '.join(conflict.conflicting_fields[:5])}"
            )
        
        else:
            return ResolutionResult(
                success=False,
                resolved_state=None,
                conflict_info=conflict,
                resolution_strategy=strategy,
                timestamp=timestamp,
                message=f"Unknown conflict resolution strategy: {strategy.value}"
            )
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            update: Dictionary with updates
        
        Returns:
            Merged dictionary
        """
        result = deepcopy(base)
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        
        return result
    
    def write_with_conflict_resolution(
        self,
        file_path: Path,
        expected_state: Dict[str, Any],
        new_state: Dict[str, Any],
        strategy: ConflictStrategy = ConflictStrategy.USE_NEWEST,
        max_retries: int = 3
    ) -> Tuple[bool, str, Optional[ResolutionResult]]:
        """
        Write state to file with automatic conflict resolution.
        
        Args:
            file_path: Path to state file
            expected_state: Expected state when operation started
            new_state: New state to write
            strategy: Conflict resolution strategy
            max_retries: Maximum number of retry attempts
        
        Returns:
            Tuple of (success, message, resolution_result)
        """
        # Increment version
        new_version = int(self._extract_version(expected_state)) + 1
        new_state['_version'] = str(new_version)
        new_state['_modified'] = datetime.now().isoformat()
        
        for attempt in range(max_retries):
            try:
                with FileLock(file_path, timeout=10):
                    # Read current state
                    if file_path.exists():
                        with open(file_path, 'r') as f:
                            actual_state = json.load(f)
                    else:
                        actual_state = {}
                    
                    # Detect and resolve conflict
                    result = self.resolve_conflict(
                        file_path,
                        expected_state,
                        new_state,
                        strategy,
                        actual_state
                    )
                    
                    if not result.success:
                        # Log the conflict
                        if self.audit_logger:
                            self.audit_logger.log_event(
                                event_type=AuditEventType.ERROR,
                                operation="write_with_conflict_resolution",
                                file_path=file_path,
                                actor="system",
                                severity=AuditSeverity.WARNING,
                                details=result.to_dict()
                            )
                        
                        return False, result.message, result
                    
                    # Write resolved state
                    with open(file_path, 'w') as f:
                        json.dump(result.resolved_state, f, indent=2)
                    
                    # Log successful write
                    if self.audit_logger:
                        self.audit_logger.log_state_change(
                            file_path=file_path,
                            operation="write_with_conflict_resolution",
                            previous_state=actual_state,
                            new_state=result.resolved_state,
                            actor="system",
                            tags=['conflict_resolution', strategy.value]
                        )
                    
                    return True, result.message, result
                    
            except FileLockError as e:
                if attempt == max_retries - 1:
                    return False, f"Failed to acquire file lock after {max_retries} attempts: {e}", None
                continue
            except (json.JSONDecodeError, IOError) as e:
                return False, f"Failed to write state file: {e}", None
        
        return False, "Max retries exceeded", None
    
    def update_state_safe(
        self,
        file_path: Path,
        updater: callable,
        strategy: ConflictStrategy = ConflictStrategy.USE_NEWEST,
        max_retries: int = 3
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Safely update state using an updater function with conflict resolution.
        
        Args:
            file_path: Path to state file
            updater: Function that takes current state and returns new state
            strategy: Conflict resolution strategy
            max_retries: Maximum number of retry attempts
        
        Returns:
            Tuple of (success, message, updated_state)
        """
        # Read initial state
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    expected_state = json.load(f)
            else:
                expected_state = {}
        except (json.JSONDecodeError, IOError) as e:
            return False, f"Failed to read state file: {e}", None
        
        # Apply updater
        try:
            new_state = updater(deepcopy(expected_state))
        except Exception as e:
            return False, f"Updater function failed: {e}", None
        
        # Write with conflict resolution
        success, message, result = self.write_with_conflict_resolution(
            file_path,
            expected_state,
            new_state,
            strategy,
            max_retries
        )
        
        if success and result:
            return True, message, result.resolved_state
        
        return success, message, None