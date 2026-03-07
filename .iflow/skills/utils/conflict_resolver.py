"""Conflict Resolver - Detects and resolves state conflicts.

This module provides conflict detection and resolution for state management
when multiple operations may modify the same state concurrently.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import IFlowError, ErrorCode


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""
    LAST_WRITER_WINS = "last_writer_wins"
    FIRST_WRITER_WINS = "first_writer_wins"
    MERGE = "merge"
    MANUAL = "manual"
    REJECT = "reject"


class ConflictSeverity(Enum):
    """Severity levels for conflicts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "critical"


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""
    conflict_id: str
    file_path: str
    timestamp: str
    base_version: str
    local_version: str
    remote_version: str
    conflict_type: str
    severity: ConflictSeverity
    base_data: Optional[Any] = None
    local_data: Optional[Any] = None
    remote_data: Optional[Any] = None
    resolved: bool = False
    resolution_strategy: Optional[ConflictResolutionStrategy] = None
    resolution_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conflict info to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "base_version": self.base_version,
            "local_version": self.local_version,
            "remote_version": self.remote_version,
            "conflict_type": self.conflict_type,
            "severity": self.severity.value,
            "base_data": self.base_data,
            "local_data": self.local_data,
            "remote_data": self.remote_data,
            "resolved": self.resolved,
            "resolution_strategy": self.resolution_strategy.value if self.resolution_strategy else None,
            "resolution_notes": self.resolution_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConflictInfo":
        """Create conflict info from dictionary."""
        return cls(
            conflict_id=data["conflict_id"],
            file_path=data["file_path"],
            timestamp=data["timestamp"],
            base_version=data["base_version"],
            local_version=data["local_version"],
            remote_version=data["remote_version"],
            conflict_type=data["conflict_type"],
            severity=ConflictSeverity(data.get("severity", "medium")),
            base_data=data.get("base_data"),
            local_data=data.get("local_data"),
            remote_data=data.get("remote_data"),
            resolved=data.get("resolved", False),
            resolution_strategy=ConflictResolutionStrategy(data["resolution_strategy"]) if data.get("resolution_strategy") else None,
            resolution_notes=data.get("resolution_notes", "")
        )


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    merged_data: Optional[Any] = None
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    strategy_used: Optional[ConflictResolutionStrategy] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert merge result to dictionary."""
        return {
            "success": self.success,
            "merged_data": self.merged_data,
            "conflicts": self.conflicts,
            "strategy_used": self.strategy_used.value if self.strategy_used else None
        }


class ConflictResolver:
    """Resolves conflicts in state management."""
    
    def __init__(self, state_dir: Path):
        """
        Initialize conflict resolver.
        
        Args:
            state_dir: Directory containing state files
        """
        self.state_dir = state_dir
        self.conflict_log_file = state_dir / ".conflicts.json"
        self.conflicts: Dict[str, ConflictInfo] = {}
        self._load_conflicts()
    
    def _load_conflicts(self) -> None:
        """Load conflicts from file."""
        if self.conflict_log_file.exists():
            try:
                with open(self.conflict_log_file, 'r') as f:
                    conflicts_data = json.load(f)
                    for conflict_id, conflict_data in conflicts_data.items():
                        self.conflicts[conflict_id] = ConflictInfo.from_dict(conflict_data)
            except (json.JSONDecodeError, IOError):
                self.conflicts = {}
    
    def _save_conflicts(self) -> None:
        """Save conflicts to file."""
        try:
            conflicts_data = {
                conflict_id: conflict.to_dict()
                for conflict_id, conflict in self.conflicts.items()
            }
            with open(self.conflict_log_file, 'w') as f:
                json.dump(conflicts_data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save conflict log: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def detect_conflict(
        self,
        file_path: Path,
        base_data: Any,
        local_data: Any,
        remote_data: Any,
        base_version: str = "base",
        local_version: str = "local",
        remote_version: str = "remote"
    ) -> Optional[ConflictInfo]:
        """
        Detect if there's a conflict between local and remote changes.
        
        Args:
            file_path: Path to the state file
            base_data: Original data before changes
            local_data: Local changes
            remote_data: Remote changes
            base_version: Version identifier for base
            local_version: Version identifier for local
            remote_version: Version identifier for remote
            
        Returns:
            ConflictInfo if conflict detected, None otherwise
        """
        import uuid
        
        # Check if data is the same
        if local_data == remote_data:
            return None
        
        # Check if only one side changed
        if local_data == base_data or remote_data == base_data:
            return None
        
        # Determine conflict type and severity
        conflict_type = self._determine_conflict_type(base_data, local_data, remote_data)
        
        # If it's mergeable, don't create a conflict
        if conflict_type == "mergeable":
            return None
        
        severity = self._determine_severity(conflict_type)
        
        # Create conflict info with stored data
        conflict_id = str(uuid.uuid4())
        conflict = ConflictInfo(
            conflict_id=conflict_id,
            file_path=str(file_path.relative_to(self.state_dir)),
            timestamp=datetime.now().isoformat(),
            base_version=base_version,
            local_version=local_version,
            remote_version=remote_version,
            conflict_type=conflict_type,
            severity=severity,
            base_data=base_data,
            local_data=local_data,
            remote_data=remote_data
        )
        
        # Store conflict
        self.conflicts[conflict_id] = conflict
        self._save_conflicts()
        
        return conflict
    
    def _determine_conflict_type(
        self,
        base_data: Any,
        local_data: Any,
        remote_data: Any
    ) -> str:
        """
        Determine the type of conflict.
        
        Args:
            base_data: Original data
            local_data: Local changes
            remote_data: Remote changes
            
        Returns:
            Conflict type string
        """
        if isinstance(base_data, dict) and isinstance(local_data, dict) and isinstance(remote_data, dict):
            # Check for overlapping key changes
            local_keys = set(local_data.keys()) - set(base_data.keys())
            remote_keys = set(remote_data.keys()) - set(base_data.keys())
            overlapping = local_keys & remote_keys
            
            if overlapping:
                return "overlapping_keys"
            
            # Check for same key modified differently
            modified_keys = set(base_data.keys()) & set(local_data.keys()) & set(remote_data.keys())
            for key in modified_keys:
                if local_data[key] != remote_data[key]:
                    return "value_conflict"
            
            return "mergeable"
        
        elif isinstance(base_data, list) and isinstance(local_data, list) and isinstance(remote_data, list):
            # List conflicts
            return "list_conflict"
        
        return "value_conflict"
    
    def _determine_severity(self, conflict_type: str) -> ConflictSeverity:
        """
        Determine severity based on conflict type.
        
        Args:
            conflict_type: Type of conflict
            
        Returns:
            Conflict severity
        """
        high_severity_types = ["overlapping_keys", "value_conflict"]
        medium_severity_types = ["list_conflict"]
        
        if conflict_type in high_severity_types:
            return ConflictSeverity.HIGH
        elif conflict_type in medium_severity_types:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.LOW
    
    def resolve_conflict(
        self,
        conflict_id: str,
        strategy: ConflictResolutionStrategy,
        custom_merge_fn: Optional[Callable[[Any, Any, Any], Any]] = None
    ) -> MergeResult:
        """
        Resolve a conflict using the specified strategy.
        
        Args:
            conflict_id: ID of the conflict to resolve
            strategy: Resolution strategy to use
            custom_merge_fn: Optional custom merge function for MERGE strategy
            
        Returns:
            MergeResult with resolved data
            
        Raises:
            IFlowError if conflict not found
        """
        # Get conflict
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            raise IFlowError(
                f"Conflict {conflict_id} not found",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Use stored data if available, otherwise try to load from file
        base_data = conflict.base_data
        local_data = conflict.local_data
        remote_data = conflict.remote_data
        
        if base_data is None or local_data is None or remote_data is None:
            # Try to load from file as fallback
            file_path = self.state_dir / conflict.file_path
            if base_data is None:
                base_data = self._load_version_data(file_path, conflict.base_version)
            if local_data is None:
                local_data = self._load_version_data(file_path, conflict.local_version)
            if remote_data is None:
                remote_data = self._load_version_data(file_path, conflict.remote_version)
        
        # Resolve based on strategy
        if strategy == ConflictResolutionStrategy.LAST_WRITER_WINS:
            result = self._resolve_last_writer_wins(local_data, remote_data, conflict.timestamp)
        elif strategy == ConflictResolutionStrategy.FIRST_WRITER_WINS:
            result = self._resolve_first_writer_wins(local_data, remote_data, conflict.timestamp)
        elif strategy == ConflictResolutionStrategy.MERGE:
            result = self._resolve_merge(base_data, local_data, remote_data, custom_merge_fn)
        elif strategy == ConflictResolutionStrategy.MANUAL:
            result = self._resolve_manual(conflict)
        elif strategy == ConflictResolutionStrategy.REJECT:
            result = self._resolve_reject()
        else:
            raise IFlowError(
                f"Unknown resolution strategy: {strategy}",
                ErrorCode.VALIDATION_FAILED
            )
        
        # Mark conflict as resolved
        if result.success:
            conflict.resolved = True
            conflict.resolution_strategy = strategy
            conflict.resolution_notes = f"Resolved using {strategy.value} strategy"
            self._save_conflicts()
        
        return result
    
    def _resolve_last_writer_wins(
        self,
        local_data: Any,
        remote_data: Any,
        conflict_timestamp: str
    ) -> MergeResult:
        """Resolve conflict by accepting the last writer."""
        # For simplicity, prefer remote_data (the incoming change)
        return MergeResult(
            success=True,
            merged_data=remote_data,
            strategy_used=ConflictResolutionStrategy.LAST_WRITER_WINS
        )
    
    def _resolve_first_writer_wins(
        self,
        local_data: Any,
        remote_data: Any,
        conflict_timestamp: str
    ) -> MergeResult:
        """Resolve conflict by accepting the first writer."""
        # For simplicity, prefer local_data (the existing change)
        return MergeResult(
            success=True,
            merged_data=local_data,
            strategy_used=ConflictResolutionStrategy.FIRST_WRITER_WINS
        )
    
    def _resolve_merge(
        self,
        base_data: Any,
        local_data: Any,
        remote_data: Any,
        custom_merge_fn: Optional[Callable[[Any, Any, Any], Any]] = None
    ) -> MergeResult:
        """
        Resolve conflict by merging changes.
        
        Args:
            base_data: Original data
            local_data: Local changes
            remote_data: Remote changes
            custom_merge_fn: Optional custom merge function
            
        Returns:
            MergeResult with merged data
        """
        if custom_merge_fn:
            try:
                merged = custom_merge_fn(base_data, local_data, remote_data)
                return MergeResult(
                    success=True,
                    merged_data=merged,
                    strategy_used=ConflictResolutionStrategy.MERGE
                )
            except Exception as e:
                return MergeResult(
                    success=False,
                    conflicts=[{"error": str(e)}],
                    strategy_used=ConflictResolutionStrategy.MERGE
                )
        
        # Default merge logic for dictionaries
        if isinstance(base_data, dict) and isinstance(local_data, dict) and isinstance(remote_data, dict):
            return self._merge_dicts(base_data, local_data, remote_data)
        elif isinstance(base_data, list) and isinstance(local_data, list) and isinstance(remote_data, list):
            return self._merge_lists(base_data, local_data, remote_data)
        else:
            # Can't merge non-collections
            return MergeResult(
                success=False,
                conflicts=[{"reason": "Cannot merge non-collection types"}],
                strategy_used=ConflictResolutionStrategy.MERGE
            )
    
    def _merge_dicts(
        self,
        base: Dict[str, Any],
        local: Dict[str, Any],
        remote: Dict[str, Any]
    ) -> MergeResult:
        """Merge dictionaries, resolving conflicts."""
        merged = base.copy()
        conflicts = []
        
        # Get all keys
        all_keys = set(base.keys()) | set(local.keys()) | set(remote.keys())
        
        for key in all_keys:
            base_val = base.get(key)
            local_val = local.get(key)
            remote_val = remote.get(key)
            
            # Key only in local
            if key not in base and key not in remote:
                merged[key] = local_val
            # Key only in remote
            elif key not in base and key not in local:
                merged[key] = remote_val
            # Key unchanged in one side
            elif local_val == base_val:
                merged[key] = remote_val
            elif remote_val == base_val:
                merged[key] = local_val
            # Both sides changed the same way
            elif local_val == remote_val:
                merged[key] = local_val
            # Conflict - both changed differently
            else:
                conflicts.append({
                    "key": key,
                    "base_value": base_val,
                    "local_value": local_val,
                    "remote_value": remote_val
                })
                # Prefer remote (last writer wins for this key)
                merged[key] = remote_val
        
        return MergeResult(
            success=len(conflicts) == 0,
            merged_data=merged,
            conflicts=conflicts,
            strategy_used=ConflictResolutionStrategy.MERGE
        )
    
    def _merge_lists(
        self,
        base: List[Any],
        local: List[Any],
        remote: List[Any]
    ) -> MergeResult:
        """Merge lists by appending unique items."""
        merged = base.copy()
        conflicts = []
        
        # Add items from local
        for item in local:
            if item not in merged:
                merged.append(item)
        
        # Add items from remote
        for item in remote:
            if item not in merged:
                merged.append(item)
            else:
                # Item exists in both - potential conflict
                conflicts.append({
                    "type": "duplicate_item",
                    "item": item
                })
        
        return MergeResult(
            success=len(conflicts) == 0,
            merged_data=merged,
            conflicts=conflicts,
            strategy_used=ConflictResolutionStrategy.MERGE
        )
    
    def _resolve_manual(self, conflict: ConflictInfo) -> MergeResult:
        """Mark conflict for manual resolution."""
        return MergeResult(
            success=False,
            conflicts=[{
                "message": "Manual resolution required",
                "conflict_id": conflict.conflict_id,
                "file_path": conflict.file_path
            }],
            strategy_used=ConflictResolutionStrategy.MANUAL
        )
    
    def _resolve_reject(self) -> MergeResult:
        """Reject the incoming change."""
        return MergeResult(
            success=False,
            conflicts=[{"message": "Change rejected due to conflict"}],
            strategy_used=ConflictResolutionStrategy.REJECT
        )
    
    def _load_version_data(self, file_path: Path, version: str) -> Any:
        """
        Load data for a specific version.
        
        Args:
            file_path: Path to the file
            version: Version identifier
            
        Returns:
            Data for the version
        """
        # For simplicity, try to load from file
        # In a real implementation, this would use the versioning system
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def get_conflict(self, conflict_id: str) -> Optional[ConflictInfo]:
        """
        Get a specific conflict.
        
        Args:
            conflict_id: Conflict ID
            
        Returns:
            ConflictInfo or None if not found
        """
        return self.conflicts.get(conflict_id)
    
    def get_unresolved_conflicts(self) -> List[ConflictInfo]:
        """
        Get all unresolved conflicts.
        
        Returns:
            List of unresolved conflicts
        """
        return [
            conflict for conflict in self.conflicts.values()
            if not conflict.resolved
        ]
    
    def get_conflicts_by_file(self, file_path: Path) -> List[ConflictInfo]:
        """
        Get conflicts for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of conflicts for the file
        """
        rel_path = str(file_path.relative_to(self.state_dir))
        return [
            conflict for conflict in self.conflicts.values()
            if conflict.file_path == rel_path
        ]
    
    def clear_resolved_conflicts(self, max_age_days: int = 30) -> int:
        """
        Clear resolved conflicts older than specified age.
        
        Args:
            max_age_days: Maximum age in days to keep resolved conflicts
            
        Returns:
            Number of conflicts cleared
        """
        import time
        cutoff = time.time() - (max_age_days * 86400)
        cleared = 0
        
        conflicts_to_remove = []
        for conflict_id, conflict in self.conflicts.items():
            if conflict.resolved:
                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(conflict.timestamp).timestamp()
                    if timestamp < cutoff:
                        conflicts_to_remove.append(conflict_id)
                except (ValueError, TypeError):
                    pass
        
        for conflict_id in conflicts_to_remove:
            del self.conflicts[conflict_id]
            cleared += 1
        
        if cleared > 0:
            self._save_conflicts()
        
        return cleared
    
    def apply_manual_resolution(
        self,
        conflict_id: str,
        resolved_data: Any
    ) -> MergeResult:
        """
        Apply manually resolved data to a conflict.
        
        Args:
            conflict_id: Conflict ID
            resolved_data: Manually resolved data
            
        Returns:
            MergeResult indicating success
            
        Raises:
            IFlowError if conflict not found
        """
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            raise IFlowError(
                f"Conflict {conflict_id} not found",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Mark as resolved
        conflict.resolved = True
        conflict.resolution_strategy = ConflictResolutionStrategy.MANUAL
        conflict.resolution_notes = "Manually resolved by user"
        self._save_conflicts()
        
        return MergeResult(
            success=True,
            merged_data=resolved_data,
            strategy_used=ConflictResolutionStrategy.MANUAL
        )