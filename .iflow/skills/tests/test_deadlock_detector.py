#!/usr/bin/env python3
"""
Unit tests for DeadlockDetector module.
"""

import pytest
from typing import Dict, List

import sys
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

from deadlock_detector import (
    DeadlockDetector,
    Deadlock,
    DeadlockType,
    DependencyType
)
from exceptions import IFlowError, ErrorCode


class TestDeadlock:
    """Tests for the Deadlock class."""

    def test_deadlock_initialization(self):
        """Test deadlock object initialization."""
        deadlock = Deadlock(
            deadlock_type=DeadlockType.CIRCULAR_DEPENDENCY,
            cycle=["A", "B", "C", "A"],
            description="Circular dependency detected",
            severity="error"
        )

        assert deadlock.deadlock_type == DeadlockType.CIRCULAR_DEPENDENCY
        assert deadlock.cycle == ["A", "B", "C", "A"]
        assert deadlock.description == "Circular dependency detected"
        assert deadlock.severity == "error"

    def test_deadlock_to_dict(self):
        """Test converting deadlock to dictionary."""
        deadlock = Deadlock(
            deadlock_type=DeadlockType.MUTUAL_BLOCKING,
            cycle=["X", "Y", "X"],
            description="Mutual blocking detected",
            severity="warning"
        )

        result = deadlock.to_dict()

        assert result["type"] == "mutual_blocking"
        assert result["cycle"] == ["X", "Y", "X"]
        assert result["description"] == "Mutual blocking detected"
        assert result["severity"] == "warning"


class TestDeadlockDetector:
    """Tests for the DeadlockDetector class."""

    def test_deadlock_detector_initialization(self):
        """Test DeadlockDetector initialization."""
        detector = DeadlockDetector()

        assert isinstance(detector.graph, dict)
        assert isinstance(detector.nodes, set)
        assert len(detector.nodes) == 0

    def test_add_dependency(self):
        """Test adding a single dependency."""
        detector = DeadlockDetector()
        detector.add_dependency("A", "B", DependencyType.REQUIRES)

        assert "A" in detector.nodes
        assert "B" in detector.nodes
        assert "B" in detector.graph["A"]["requires"]

    def test_add_dependency_default_type(self):
        """Test adding dependency with default type."""
        detector = DeadlockDetector()
        detector.add_dependency("A", "B")

        assert "B" in detector.graph["A"]["requires"]

    def test_add_multiple_dependencies(self):
        """Test adding multiple dependencies."""
        detector = DeadlockDetector()
        dependencies = [
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.DEPENDS_ON),
            ("C", "D", DependencyType.MUST_COMPLETE)
        ]

        detector.add_dependencies(dependencies)

        assert len(detector.nodes) == 4
        assert "A" in detector.nodes
        assert "B" in detector.nodes
        assert "C" in detector.nodes
        assert "D" in detector.nodes

    def test_detect_circular_dependency(self):
        """Test detecting a circular dependency."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "A", DependencyType.REQUIRES)
        ])

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 1
        assert deadlocks[0].deadlock_type == DeadlockType.CIRCULAR_DEPENDENCY
        assert "A" in deadlocks[0].cycle
        assert "B" in deadlocks[0].cycle
        assert "C" in deadlocks[0].cycle

    def test_detect_no_deadlock(self):
        """Test detecting when no deadlock exists."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "D", DependencyType.REQUIRES)
        ])

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 0

    def test_detect_multiple_deadlocks(self):
        """Test detecting multiple deadlocks."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "A", DependencyType.REQUIRES),
            ("C", "D", DependencyType.REQUIRES),
            ("D", "C", DependencyType.REQUIRES)
        ])

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 2

    def test_detect_mutual_blocking(self):
        """Test detecting mutual blocking."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("Task1", "Task2", DependencyType.BLOCKED_BY),
            ("Task2", "Task1", DependencyType.BLOCKED_BY)
        ])

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 1
        assert deadlocks[0].deadlock_type == DeadlockType.MUTUAL_BLOCKING

    def test_self_dependency(self):
        """Test detecting self-dependency."""
        detector = DeadlockDetector()
        detector.add_dependency("A", "A", DependencyType.REQUIRES)

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 1

    def test_complex_circular_dependency(self):
        """Test detecting complex circular dependency."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "D", DependencyType.REQUIRES),
            ("D", "A", DependencyType.REQUIRES)
        ])

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 1
        assert len(deadlocks[0].cycle) == 4

    def test_partial_circular_dependency(self):
        """Test detecting partial circular dependency in larger graph."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "A", DependencyType.REQUIRES),  # Circular part
            ("D", "E", DependencyType.REQUIRES),  # Non-circular part
            ("E", "F", DependencyType.REQUIRES)
        ])

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 1
        assert set(deadlocks[0].cycle) == {"A", "B", "C"}

    def test_multiple_dependency_types(self):
        """Test handling multiple dependency types."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.DEPENDS_ON),
            ("C", "A", DependencyType.MUST_COMPLETE)
        ])

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 1

    def test_empty_graph(self):
        """Test detecting deadlocks in empty graph."""
        detector = DeadlockDetector()

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 0

    def test_single_node(self):
        """Test detecting deadlocks with single node."""
        detector = DeadlockDetector()
        detector.add_dependency("A", "B", DependencyType.REQUIRES)

        deadlocks = detector.detect_deadlocks()

        assert len(deadlocks) == 0

    def test_get_dependency_chain(self):
        """Test getting dependency chain."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "D", DependencyType.REQUIRES)
        ])

        chain = detector.get_dependency_chain("A", DependencyType.REQUIRES)

        assert chain == ["A", "B", "C", "D"]

    def test_get_dependency_chain_cycle(self):
        """Test getting dependency chain with cycle."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "A", DependencyType.REQUIRES)
        ])

        chain = detector.get_dependency_chain("A", DependencyType.REQUIRES)

        # Should detect cycle and stop
        assert "A" in chain
        assert "B" in chain
        assert "C" in chain

    def test_get_dependency_chain_no_path(self):
        """Test getting dependency chain when no path exists."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("C", "D", DependencyType.REQUIRES)
        ])

        chain = detector.get_dependency_chain("A", DependencyType.REQUIRES)

        assert chain == ["A", "B"]

    def test_get_affected_nodes(self):
        """Test getting nodes affected by a deadlock."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "A", DependencyType.REQUIRES),
            ("D", "B", DependencyType.REQUIRES)
        ])

        deadlocks = detector.detect_deadlocks()
        affected = detector.get_affected_nodes(deadlocks[0])

        assert "A" in affected
        assert "B" in affected
        assert "C" in affected
        assert "D" in affected

    def test_clear_graph(self):
        """Test clearing the dependency graph."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES)
        ])

        assert len(detector.nodes) == 3

        detector.clear_graph()

        assert len(detector.nodes) == 0
        assert len(detector.graph) == 0

    def test_get_all_nodes(self):
        """Test getting all nodes in the graph."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("C", "D", DependencyType.REQUIRES),
            ("E", "F", DependencyType.REQUIRES)
        ])

        nodes = detector.get_all_nodes()

        assert len(nodes) == 6
        assert "A" in nodes
        assert "B" in nodes
        assert "C" in nodes
        assert "D" in nodes
        assert "E" in nodes
        assert "F" in nodes

    def test_get_dependencies_for_node(self):
        """Test getting dependencies for a specific node."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("A", "C", DependencyType.REQUIRES),
            ("A", "D", DependencyType.DEPENDS_ON)
        ])

        deps = detector.get_dependencies_for_node("A")

        assert "B" in deps
        assert "C" in deps
        assert "D" in deps

    def test_get_dependencies_for_nonexistent_node(self):
        """Test getting dependencies for nonexistent node."""
        detector = DeadlockDetector()
        deps = detector.get_dependencies_for_node("Nonexistent")

        assert deps == []

    def test_node_count(self):
        """Test counting nodes in the graph."""
        detector = DeadlockDetector()
        assert detector.node_count() == 0

        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES)
        ])

        assert detector.node_count() == 3

    def test_dependency_count(self):
        """Test counting dependencies in the graph."""
        detector = DeadlockDetector()
        assert detector.dependency_count() == 0

        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "D", DependencyType.DEPENDS_ON)
        ])

        assert detector.dependency_count() == 3

    def test_validate_graph_valid(self):
        """Test validating a valid graph."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES)
        ])

        is_valid, errors = detector.validate_graph()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_graph_invalid(self):
        """Test validating an invalid graph."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "A", DependencyType.REQUIRES)
        ])

        is_valid, errors = detector.validate_graph()

        assert is_valid is False
        assert len(errors) > 0

    def test_remove_dependency(self):
        """Test removing a dependency."""
        detector = DeadlockDetector()
        detector.add_dependency("A", "B", DependencyType.REQUIRES)

        assert "B" in detector.graph["A"]["requires"]

        detector.remove_dependency("A", "B", DependencyType.REQUIRES)

        assert "B" not in detector.graph["A"]["requires"]

    def test_remove_node(self):
        """Test removing a node and its dependencies."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.REQUIRES),
            ("C", "A", DependencyType.REQUIRES)
        ])

        assert len(detector.nodes) == 3

        detector.remove_node("B")

        assert "B" not in detector.nodes
        assert "B" not in detector.graph

    def test_export_graph(self):
        """Test exporting graph to dictionary."""
        detector = DeadlockDetector()
        detector.add_dependencies([
            ("A", "B", DependencyType.REQUIRES),
            ("B", "C", DependencyType.DEPENDS_ON)
        ])

        exported = detector.export_graph()

        assert isinstance(exported, dict)
        assert "nodes" in exported
        assert "dependencies" in exported
        assert len(exported["nodes"]) == 3

    def test_import_graph(self):
        """Test importing graph from dictionary."""
        graph_data = {
            "nodes": ["A", "B", "C"],
            "dependencies": [
                ("A", "B", "requires"),
                ("B", "C", "depends_on")
            ]
        }

        detector = DeadlockDetector()
        detector.import_graph(graph_data)

        assert len(detector.nodes) == 3
        assert "B" in detector.graph["A"]["requires"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])