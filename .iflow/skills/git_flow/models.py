#!/usr/bin/env python3
"""
Git-Flow Data Models
Defines data model classes for workflow, branches, phases, and dependencies.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum


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
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ReviewEvent':
        """Create from dictionary."""
        return cls(
            action=data["action"],
            actor=data["actor"],
            timestamp=data.get("timestamp"),
            comment=data.get("comment"),
            reason=data.get("reason"),
            merge_commit=data.get("merge_commit")
        )


class BranchState:
    """Represents the state of a branch in the workflow."""
    
    def __init__(self, name: str, role: str, phase: int):
        self.name = name
        self.role = role
        self.status = "pending"
        self.base_branch = "main"
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.commits: List[str] = []
        self.reviews: List[ReviewEvent] = []
        self.phase = phase
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "base_branch": self.base_branch,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "commits": self.commits,
            "reviews": [r.to_dict() for r in self.reviews],
            "phase": self.phase
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BranchState':
        """Create from dictionary."""
        branch = cls(
            name=data["name"],
            role=data["role"],
            phase=data["phase"]
        )
        branch.status = data.get("status", "pending")
        branch.base_branch = data.get("base_branch", "main")
        branch.created_at = data.get("created_at", branch.created_at)
        branch.updated_at = data.get("updated_at", branch.updated_at)
        branch.commits = data.get("commits", [])
        branch.reviews = [ReviewEvent.from_dict(r) for r in data.get("reviews", [])]
        return branch


class Phase:
    """Represents a phase in the workflow."""
    
    def __init__(self, name: str, order: int, assigned_skill: str):
        self.name = name
        self.order = order
        self.status = "pending"
        self.assigned_skill = assigned_skill
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.dependencies: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "order": self.order,
            "status": self.status,
            "assigned_skill": self.assigned_skill,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "dependencies": self.dependencies,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Phase':
        """Create from dictionary."""
        phase = cls(
            name=data["name"],
            order=data["order"],
            assigned_skill=data["assigned_skill"]
        )
        phase.status = data.get("status", "pending")
        phase.start_time = data.get("start_time")
        phase.end_time = data.get("end_time")
        phase.dependencies = data.get("dependencies", [])
        phase.metadata = data.get("metadata", {})
        return phase
    
    def can_start(self, completed_phases: Set[str]) -> bool:
        """Check if phase can start based on dependencies."""
        return all(dep in completed_phases for dep in self.dependencies)


class WorkflowState:
    """Represents the state of a workflow."""
    
    def __init__(self, name: str, feature: str):
        self.name = name
        self.feature = feature
        self.status = "initialized"
        self.current_phase = "planning"
        self.phases: List[Phase] = []
        self.branches: Dict[str, BranchState] = {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.metadata: Dict[str, Any] = {}
        self.version = "1"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "feature": self.feature,
            "status": self.status,
            "current_phase": self.current_phase,
            "phases": [p.to_dict() for p in self.phases],
            "branches": {name: b.to_dict() for name, b in self.branches.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowState':
        """Create from dictionary."""
        workflow = cls(
            name=data["name"],
            feature=data["feature"]
        )
        workflow.status = data.get("status", "initialized")
        workflow.current_phase = data.get("current_phase", "planning")
        workflow.phases = [Phase.from_dict(p) for p in data.get("phases", [])]
        workflow.branches = {
            name: BranchState.from_dict(b)
            for name, b in data.get("branches", {}).items()
        }
        workflow.created_at = data.get("created_at", workflow.created_at)
        workflow.updated_at = data.get("updated_at", workflow.updated_at)
        workflow.metadata = data.get("metadata", {})
        workflow.version = data.get("version", "1")
        return workflow
    
    def get_phase(self, phase_name: str) -> Optional[Phase]:
        """Get a phase by name."""
        return next((p for p in self.phases if p.name == phase_name), None)
    
    def get_branch(self, branch_name: str) -> Optional[BranchState]:
        """Get a branch by name."""
        return self.branches.get(branch_name)
    
    def get_completed_phases(self) -> Set[str]:
        """Get names of completed phases."""
        return {p.name for p in self.phases if p.status == "complete"}


class DependencyGraph:
    """Manages dependencies between workflow components."""
    
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}
    
    def add_dependency(self, component: str, depends_on: str) -> None:
        """Add a dependency relationship."""
        if component not in self.graph:
            self.graph[component] = set()
        if depends_on not in self.graph:
            self.graph[depends_on] = set()
        self.graph[component].add(depends_on)
    
    def add_dependencies(self, component: str, depends_on: List[str]) -> None:
        """Add multiple dependencies for a component."""
        for dep in depends_on:
            self.add_dependency(component, dep)
    
    def get_dependents(self, component: str) -> Set[str]:
        """Get all components that depend on the given component."""
        return {comp for comp, deps in self.graph.items() if component in deps}
    
    def get_all_dependents(self, component: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all transitive dependents of a component."""
        if visited is None:
            visited = set()
        if component in visited:
            return visited
        visited.add(component)
        
        for dependent in self.get_dependents(component):
            self.get_all_dependents(dependent, visited)
        
        return visited
    
    def check_circular(self) -> bool:
        """Check for circular dependencies."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.graph:
            if node not in visited:
                if has_cycle(node):
                    return True
        
        return False
    
    def topological_sort(self) -> List[str]:
        """Get topological order of components."""
        in_degree = {node: 0 for node in self.graph}
        for node in self.graph:
            for neighbor in self.graph[node]:
                in_degree[neighbor] = in_degree.get(neighbor, 0) + 1
        
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self.graph.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(self.graph):
            raise ValueError("Graph has a cycle")
        
        return result
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "graph": {node: list(deps) for node, deps in self.graph.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DependencyGraph':
        """Create from dictionary."""
        graph = cls()
        for node, deps in data.get("graph", {}).items():
            for dep in deps:
                graph.add_dependency(node, dep)
        return graph