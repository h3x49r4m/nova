"""Deadlock Detector - Detects and prevents circular dependencies.

This module provides functionality for detecting circular dependencies and
potential deadlocks in git-flow workflows and pipeline dependencies.
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
from enum import Enum

from .exceptions import IFlowError, ErrorCode, ErrorCategory


class DependencyType(Enum):
    """Types of dependency relationships."""
    REQUIRES = "requires"
    DEPENDS_ON = "depends_on"
    MUST_COMPLETE = "must_complete"
    MUST_START_AFTER = "must_start_after"
    BLOCKED_BY = "blocked_by"


class DeadlockType(Enum):
    """Types of deadlocks."""
    CIRCULAR_DEPENDENCY = "circular_dependency"
    MUTUAL_BLOCKING = "mutual_blocking"
    RESOURCE_WAIT = "resource_wait"
    PHASE_WAIT = "phase_wait"


class Deadlock:
    """Represents a detected deadlock."""
    
    def __init__(
        self,
        deadlock_type: DeadlockType,
        cycle: List[str],
        description: str,
        severity: str = "error"
    ):
        """
        Initialize a deadlock.
        
        Args:
            deadlock_type: Type of deadlock
            cycle: List of nodes in the deadlock cycle
            description: Human-readable description
            severity: Severity level (error, warning, info)
        """
        self.deadlock_type = deadlock_type
        self.cycle = cycle
        self.description = description
        self.severity = severity
    
    def to_dict(self) -> Dict:
        """Convert deadlock to dictionary."""
        return {
            "type": self.deadlock_type.value,
            "cycle": self.cycle,
            "description": self.description,
            "severity": self.severity
        }


class DeadlockDetector:
    """Detects deadlocks in dependency graphs."""
    
    def __init__(self):
        """Initialize the deadlock detector."""
        self.graph: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.nodes: Set[str] = set()
    
    def add_dependency(
        self,
        from_node: str,
        to_node: str,
        dependency_type: DependencyType = DependencyType.REQUIRES
    ):
        """
        Add a dependency relationship.
        
        Args:
            from_node: Node that depends on to_node
            to_node: Node that from_node depends on
            dependency_type: Type of dependency
        """
        self.graph[from_node][dependency_type.value].append(to_node)
        self.nodes.add(from_node)
        self.nodes.add(to_node)
    
    def add_dependencies(
        self,
        dependencies: List[Tuple[str, str, DependencyType]]
    ):
        """
        Add multiple dependencies.
        
        Args:
            dependencies: List of (from_node, to_node, dependency_type) tuples
        """
        for from_node, to_node, dep_type in dependencies:
            self.add_dependency(from_node, to_node, dep_type)
    
    def clear(self):
        """Clear all dependencies."""
        self.graph.clear()
        self.nodes.clear()
    
    def detect_circular_dependencies(
        self,
        dependency_type: Optional[DependencyType] = None
    ) -> List[Deadlock]:
        """
        Detect circular dependencies in the graph.
        
        Args:
            dependency_type: Optional specific dependency type to check
            
        Returns:
            List of detected deadlocks
        """
        deadlocks = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> Optional[Deadlock]:
            """Depth-first search to detect cycles."""
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                return Deadlock(
                    deadlock_type=DeadlockType.CIRCULAR_DEPENDENCY,
                    cycle=cycle,
                    description=f"Circular dependency detected: {' -> '.join(cycle)}",
                    severity="error"
                )
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # Get dependencies based on type
            deps = []
            if dependency_type:
                deps = self.graph[node].get(dependency_type.value, [])
            else:
                # Check all dependency types
                for dep_list in self.graph[node].values():
                    deps.extend(dep_list)
            
            for dep in deps:
                deadlock = dfs(dep, path.copy())
                if deadlock:
                    return deadlock
            
            rec_stack.remove(node)
            return None
        
        for node in self.nodes:
            if node not in visited:
                deadlock = dfs(node, [])
                if deadlock:
                    deadlocks.append(deadlock)
        
        return deadlocks
    
    def detect_mutual_blocking(
        self,
        blocked_nodes: Dict[str, List[str]]
    ) -> List[Deadlock]:
        """
        Detect mutual blocking scenarios where nodes are waiting for each other.
        
        Args:
            blocked_nodes: Dictionary mapping node to list of nodes it's blocked by
            
        Returns:
            List of detected mutual blocking deadlocks
        """
        deadlocks = []
        checked = set()
        
        for node, blockers in blocked_nodes.items():
            for blocker in blockers:
                # Check if blocker is also blocked by node
                if blocker in blocked_nodes and node in blocked_nodes[blocker]:
                    cycle = [node, blocker, node]
                    
                    # Avoid duplicate detection
                    cycle_key = tuple(sorted([node, blocker]))
                    if cycle_key not in checked:
                        checked.add(cycle_key)
                        deadlocks.append(Deadlock(
                            deadlock_type=DeadlockType.MUTUAL_BLOCKING,
                            cycle=cycle,
                            description=f"Mutual blocking detected: {node} and {blocker} are blocking each other",
                            severity="error"
                        ))
        
        return deadlocks
    
    def detect_phase_deadlock(
        self,
        phase_status: Dict[str, Dict[str, str]]
    ) -> List[Deadlock]:
        """
        Detect deadlocks related to phase transitions.
        
        Args:
            phase_status: Dictionary mapping phase to status info
            
        Returns:
            List of detected phase deadlocks
        """
        deadlocks = []
        
        # Find phases that are blocked
        blocked_phases = {
            phase: info
            for phase, info in phase_status.items()
            if info.get("status") == "blocked"
        }
        
        # Check for chains of blocked phases
        if len(blocked_phases) > 1:
            phases_list = list(blocked_phases.keys())
            deadlocks.append(Deadlock(
                deadlock_type=DeadlockType.PHASE_WAIT,
                cycle=phases_list,
                description=f"Multiple phases blocked: {', '.join(phases_list)}",
                severity="warning"
            ))
        
        return deadlocks
    
    def get_dependency_chain(
        self,
        from_node: str,
        to_node: str,
        dependency_type: Optional[DependencyType] = None
    ) -> Optional[List[str]]:
        """
        Get the dependency chain between two nodes.
        
        Args:
            from_node: Starting node
            to_node: Target node
            dependency_type: Optional specific dependency type
            
        Returns:
            List of nodes in the chain, or None if no path exists
        """
        if from_node == to_node:
            return [from_node]
        
        visited = set()
        queue = deque([(from_node, [from_node])])
        
        while queue:
            current, path = queue.popleft()
            
            if current == to_node:
                return path
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Get dependencies
            deps = []
            if dependency_type:
                deps = self.graph[current].get(dependency_type.value, [])
            else:
                for dep_list in self.graph[current].values():
                    deps.extend(dep_list)
            
            for dep in deps:
                if dep not in visited:
                    queue.append((dep, path + [dep]))
        
        return None
    
    def get_all_chains(
        self,
        node: str,
        dependency_type: Optional[DependencyType] = None
    ) -> List[List[str]]:
        """
        Get all dependency chains from a node.
        
        Args:
            node: Starting node
            dependency_type: Optional specific dependency type
            
        Returns:
            List of all chains
        """
        chains = []
        visited = set()
        
        def dfs(current: str, path: List[str]):
            """DFS to find all chains."""
            if current in visited:
                return
            
            if path:  # Don't include the starting node
                chains.append(path)
            
            visited.add(current)
            
            # Get dependencies
            deps = []
            if dependency_type:
                deps = self.graph[current].get(dependency_type.value, [])
            else:
                for dep_list in self.graph[current].values():
                    deps.extend(dep_list)
            
            for dep in deps:
                dfs(dep, path + [dep])
            
            visited.remove(current)
        
        # Get dependencies of the starting node
        deps = []
        if dependency_type:
            deps = self.graph[node].get(dependency_type.value, [])
        else:
            for dep_list in self.graph[node].values():
                deps.extend(dep_list)
        
        for dep in deps:
            dfs(dep, [node, dep])
        
        return chains
    
    def validate_dependencies(
        self,
        allow_self_dependency: bool = False
    ) -> Tuple[bool, List[Deadlock]]:
        """
        Validate all dependencies in the graph.
        
        Args:
            allow_self_dependency: Whether self-dependencies are allowed
            
        Returns:
            Tuple of (is_valid, list_of_deadlocks)
        """
        deadlocks = []
        
        # Check for self-dependencies
        if not allow_self_dependency:
            for node in self.nodes:
                for dep_type, deps in self.graph[node].items():
                    if node in deps:
                        deadlocks.append(Deadlock(
                            deadlock_type=DeadlockType.CIRCULAR_DEPENDENCY,
                            cycle=[node, node],
                            description=f"Self-dependency detected: {node} depends on itself",
                            severity="error"
                        ))
        
        # Check for circular dependencies
        deadlocks.extend(self.detect_circular_dependencies())
        
        return len(deadlocks) == 0, deadlocks
    
    def get_dependency_report(self) -> Dict:
        """
        Generate a report of the dependency graph.
        
        Returns:
            Dictionary with dependency graph information
        """
        report = {
            "total_nodes": len(self.nodes),
            "total_dependencies": 0,
            "nodes": {},
            "dependency_types": {}
        }
        
        # Count dependencies by type
        type_counts = defaultdict(int)
        
        for node in self.nodes:
            node_info = {
                "dependencies": {},
                "dependents": []
            }
            
            for dep_type, deps in self.graph[node].items():
                if deps:
                    node_info["dependencies"][dep_type] = deps
                    type_counts[dep_type] += len(deps)
                    report["total_dependencies"] += len(deps)
            
            report["nodes"][node] = node_info
        
        # Find dependents
        for node in self.nodes:
            for dep_type, deps in self.graph[node].items():
                for dep in deps:
                    if dep in report["nodes"]:
                        report["nodes"][dep]["dependents"].append(node)
        
        report["dependency_types"] = dict(type_counts)
        
        return report


def create_deadlock_detector() -> DeadlockDetector:
    """Create a deadlock detector instance."""
    return DeadlockDetector()


def validate_git_flow_dependencies(
    branch_states: Dict[str, Dict]
) -> Tuple[bool, List[Deadlock]]:
    """
    Validate git-flow branch dependencies for deadlocks.
    
    Args:
        branch_states: Dictionary of branch states
        
    Returns:
        Tuple of (is_valid, list_of_deadlocks)
    """
    detector = create_deadlock_detector()
    
    # Build dependency graph from branch states
    for branch_name, branch_data in branch_states.items():
        # Add dependencies
        for dep in branch_data.get("dependencies", []):
            detector.add_dependency(
                from_node=branch_name,
                to_node=dep,
                dependency_type=DependencyType.REQUIRES
            )
        
        # Add dependent relationships (reverse of dependencies)
        for dependent in branch_data.get("dependents", []):
            detector.add_dependency(
                from_node=dependent,
                to_node=branch_name,
                dependency_type=DependencyType.DEPENDS_ON
            )
    
    return detector.validate_dependencies()


def validate_pipeline_dependencies(
    stages: List[Dict]
) -> Tuple[bool, List[Deadlock]]:
    """
    Validate pipeline stage dependencies for deadlocks.
    
    Args:
        stages: List of pipeline stages
        
    Returns:
        Tuple of (is_valid, list_of_deadlocks)
    """
    detector = create_deadlock_detector()
    
    # Build dependency graph from stages
    for stage in stages:
        stage_name = stage.get("name", "")
        
        # Add dependencies
        for dep in stage.get("depends_on", []):
            detector.add_dependency(
                from_node=stage_name,
                to_node=dep,
                dependency_type=DependencyType.MUST_COMPLETE
            )
        
        # Add stage ordering dependencies
        for after in stage.get("must_start_after", []):
            detector.add_dependency(
                from_node=stage_name,
                to_node=after,
                dependency_type=DependencyType.MUST_START_AFTER
            )
    
    return detector.validate_dependencies()