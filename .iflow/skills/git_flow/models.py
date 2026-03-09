#!/usr/bin/env python3
"""
Git-Flow Data Models
Defines data model classes for workflow, branches, phases, and dependencies.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum

# Import enums from utils
try:
    from utils.constants import BranchStatus, PhaseStatus, WorkflowStatus
except ImportError:
    # Fallback for standalone usage
    class BranchStatus(Enum):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        UNAPPROVED = "unapproved"
        NEEDS_CHANGES = "needs_changes"

    class PhaseStatus(Enum):
        PENDING = "pending"
        ACTIVE = "active"
        COMPLETE = "complete"
        BLOCKED = "blocked"

    class WorkflowStatus(Enum):
        INITIALIZED = "initialized"
        IN_PROGRESS = "in_progress"
        COMPLETE = "complete"
        PAUSED = "paused"
        BLOCKED = "blocked"


class ReviewEvent:
    """Represents a review event (approval, rejection, request changes)."""

    def __init__(self, action: str, actor: str, comment: Optional[str] = None,
                 reason: Optional[str] = None, merge_commit: Optional[str] = None):
        self.action = action
        self.actor = actor
        self.timestamp = datetime.now().isoformat()
        self.comment = comment
        self.reason = reason
        self.merge_commit = merge_commit

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "comment": self.comment,
            "reason": self.reason,
            "merge_commit": self.merge_commit
        }


class BranchState:
    """Represents the state of a branch in the workflow."""

    def __init__(self, name: str, role: str, phase: int):
        self.name = name
        self.role = role
        self.status = BranchStatus.PENDING
        self.phase = phase
        self.created_at = datetime.now().isoformat()
        self.commits: List[Dict] = []
        self.merge_commit: Optional[str] = None
        self.approved_by: Optional[str] = None
        self.approved_at: Optional[str] = None
        self.unapproved_by: Optional[str] = None
        self.unapproved_at: Optional[str] = None
        self.dependencies: List[str] = []
        self.dependents: List[str] = []
        self.review_history: List[Dict] = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "phase": self.phase,
            "created_at": self.created_at,
            "commits": self.commits,
            "merge_commit": self.merge_commit,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "unapproved_by": self.unapproved_by,
            "unapproved_at": self.unapproved_at,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "review_history": self.review_history,
            "_version": str(int(self._get_version_from_history())) if self.review_history else "0",
            "_modified": self._get_last_modified()
        }

    def _get_version_from_history(self) -> int:
        """Calculate version from review history."""
        return len(self.review_history)

    def _get_last_modified(self) -> str:
        """Get the last modification timestamp."""
        if self.review_history:
            return self.review_history[-1].get('timestamp', self.created_at)
        return self.created_at

    @classmethod
    def from_dict(cls, data: Dict) -> 'BranchState':
        """Create from dictionary."""
        branch = cls(data["name"], data["role"], data["phase"])
        status_str = data.get("status", "pending")
        # Handle both string and enum values
        if isinstance(status_str, str):
            branch.status = BranchStatus(status_str)
        else:
            branch.status = status_str
        branch.created_at = data.get("created_at")
        branch.commits = data.get("commits", [])
        branch.merge_commit = data.get("merge_commit")
        branch.approved_by = data.get("approved_by")
        branch.approved_at = data.get("approved_at")
        branch.unapproved_by = data.get("unapproved_by")
        branch.unapproved_at = data.get("unapproved_at")
        branch.dependencies = data.get("dependencies", [])
        branch.dependents = data.get("dependents", [])
        branch.review_history = data.get("review_history", [])
        return branch


class Phase:
    """Represents a phase in the workflow."""

    def __init__(self, name: str, role: str, order: int, required: bool):
        self.name = name
        self.role = role
        self.order = order
        self.required = required
        self.status = PhaseStatus.PENDING
        self.branch: Optional[str] = None
        self.dependencies: List[int] = []
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.timeout_seconds: int = 604800  # 7 days default
        self.timeout_warning_sent: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "order": self.order,
            "required": self.required,
            "status": self.status.value,
            "branch": self.branch,
            "dependencies": self.dependencies,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "timeout_seconds": self.timeout_seconds,
            "timeout_warning_sent": self.timeout_warning_sent
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Phase':
        """Create from dictionary."""
        phase = cls(data["name"], data["role"], data["order"], data["required"])
        status_str = data.get("status", "pending")
        # Handle both string and enum values
        if isinstance(status_str, str):
            phase.status = PhaseStatus(status_str)
        else:
            phase.status = status_str
        phase.branch = data.get("branch")
        phase.dependencies = data.get("dependencies", [])
        phase.started_at = data.get("started_at")
        phase.completed_at = data.get("completed_at")
        phase.timeout_seconds = data.get("timeout_seconds", 604800)
        phase.timeout_warning_sent = data.get("timeout_warning_sent", False)
        return phase


class WorkflowState:
    """Represents the state of a workflow."""

    def __init__(self, feature: str):
        self.feature = feature
        self.status = WorkflowStatus.INITIALIZED
        self.current_phase = 0
        self.phases: List[Phase] = []
        self.branches: Dict[str, BranchState] = {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "feature": self.feature,
            "status": self.status.value,
            "current_phase": self.current_phase,
            "phases": [p.to_dict() for p in self.phases],
            "branches": {k: v.to_dict() for k, v in self.branches.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "_version": str(self._calculate_version()),
            "_modified": self.updated_at
        }

    def _calculate_version(self) -> int:
        """Calculate workflow version based on changes."""
        # Base version from phases
        version = len(self.phases)

        # Add for each branch
        version += len(self.branches)

        # Add for workflow status changes
        if self.status != WorkflowStatus.INITIALIZED:
            version += 1

        # Add for phase transitions
        version += self.current_phase

        return version

    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowState':
        """Create from dictionary."""
        workflow = cls(data["feature"])
        status_str = data.get("status", "initialized")
        # Handle both string and enum values
        if isinstance(status_str, str):
            workflow.status = WorkflowStatus(status_str)
        else:
            workflow.status = status_str
        workflow.current_phase = data.get("current_phase", 0)
        workflow.phases = [Phase.from_dict(p) for p in data.get("phases", [])]
        workflow.branches = {k: BranchState.from_dict(v) for k, v in data.get("branches", {}).items()}
        workflow.created_at = data.get("created_at", datetime.now().isoformat())
        workflow.updated_at = data.get("updated_at", datetime.now().isoformat())
        return workflow


class DependencyGraph:
    """Manages branch dependency relationships."""

    def __init__(self):
        """Initialize an empty dependency graph."""
        self.graph: Dict[str, List[str]] = {}
        self.reverse_graph: Dict[str, List[str]] = {}

    def add_dependency(self, branch: str, depends_on: List[str]):
        """
        Add a dependency relationship between branches.

        Args:
            branch: Name of the branch that has dependencies
            depends_on: List of branch names that this branch depends on
        """
        if branch not in self.graph:
            self.graph[branch] = []
        if branch not in self.reverse_graph:
            self.reverse_graph[branch] = []

        self.graph[branch].extend(depends_on)
        for dep in depends_on:
            if dep not in self.reverse_graph:
                self.reverse_graph[dep] = []
            self.reverse_graph[dep].append(branch)

    def get_dependents(self, branch: str) -> List[str]:
        """
        Get branches that depend on the given branch.

        Args:
            branch: Name of the branch

        Returns:
            List of branch names that depend on this branch
        """
        return self.reverse_graph.get(branch, [])

    def get_all_dependents(self, branch: str) -> List[str]:
        """
        Get all branches that transitively depend on the given branch.

        Args:
            branch: Name of the branch

        Returns:
            List of all branch names that depend on this branch (direct and indirect)
        """
        dependents = []
        visited = set()

        def traverse(b: str):
            if b in visited:
                return
            visited.add(b)

            for dep in self.get_dependents(b):
                dependents.append(dep)
                traverse(dep)

        traverse(branch)
        return dependents