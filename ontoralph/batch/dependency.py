"""Dependency ordering for batch processing.

This module provides topological sorting of classes based on parent-child
relationships to ensure parents are processed before children.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass

from ontoralph.core.models import ClassInfo

logger = logging.getLogger(__name__)


@dataclass
class DependencyIssue:
    """Represents a dependency ordering issue."""

    class_iri: str
    issue_type: str  # "circular", "missing_parent", "self_reference"
    message: str
    related_iris: list[str]


class DependencyGraph:
    """Manages class dependency relationships for ordering."""

    def __init__(self) -> None:
        self._nodes: dict[str, ClassInfo] = {}
        self._edges: dict[str, set[str]] = defaultdict(set)  # child -> parents
        self._reverse_edges: dict[str, set[str]] = defaultdict(set)  # parent -> children

    def add_class(self, class_info: ClassInfo) -> None:
        """Add a class to the dependency graph.

        Args:
            class_info: Class to add.
        """
        self._nodes[class_info.iri] = class_info

        # Add edge from child to parent
        if class_info.parent_class:
            self._edges[class_info.iri].add(class_info.parent_class)
            self._reverse_edges[class_info.parent_class].add(class_info.iri)

    def add_classes(self, classes: list[ClassInfo]) -> None:
        """Add multiple classes to the graph.

        Args:
            classes: List of classes to add.
        """
        for class_info in classes:
            self.add_class(class_info)

    def get_dependencies(self, iri: str) -> set[str]:
        """Get immediate dependencies (parents) of a class.

        Args:
            iri: Class IRI.

        Returns:
            Set of parent IRIs.
        """
        return self._edges.get(iri, set())

    def get_dependents(self, iri: str) -> set[str]:
        """Get immediate dependents (children) of a class.

        Args:
            iri: Class IRI.

        Returns:
            Set of child IRIs.
        """
        return self._reverse_edges.get(iri, set())

    def validate(self) -> list[DependencyIssue]:
        """Validate the dependency graph for issues.

        Returns:
            List of dependency issues found.
        """
        issues: list[DependencyIssue] = []

        # Check for self-references
        for iri, parents in self._edges.items():
            if iri in parents:
                issues.append(DependencyIssue(
                    class_iri=iri,
                    issue_type="self_reference",
                    message=f"Class {iri} has itself as parent",
                    related_iris=[iri],
                ))

        # Check for circular dependencies
        cycles = self._find_cycles()
        for cycle in cycles:
            issues.append(DependencyIssue(
                class_iri=cycle[0],
                issue_type="circular",
                message=f"Circular dependency detected: {' -> '.join(cycle)}",
                related_iris=cycle,
            ))

        # Check for missing parents (only within the batch)
        internal_iris = set(self._nodes.keys())
        for iri, parents in self._edges.items():
            for parent in parents:
                # Only flag if parent looks like a local IRI (starts with :)
                if parent.startswith(":") and parent not in internal_iris:
                    issues.append(DependencyIssue(
                        class_iri=iri,
                        issue_type="missing_parent",
                        message=f"Class {iri} has parent {parent} not in batch",
                        related_iris=[parent],
                    ))

        return issues

    def _find_cycles(self) -> list[list[str]]:
        """Find all cycles in the dependency graph using DFS.

        Returns:
            List of cycles (each cycle is a list of IRIs).
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for parent in self._edges.get(node, set()):
                if parent not in self._nodes:
                    # External dependency, skip
                    continue
                if parent not in visited:
                    dfs(parent)
                elif parent in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(parent)
                    cycle = path[cycle_start:] + [parent]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in self._nodes:
            if node not in visited:
                dfs(node)

        return cycles


class DependencyOrderer:
    """Orders classes based on their dependency relationships.

    Uses topological sorting to ensure parents are processed before children.
    External dependencies (classes not in the batch) are ignored for ordering.
    """

    def order(self, classes: list[ClassInfo]) -> list[ClassInfo]:
        """Order classes so parents come before children.

        Uses Kahn's algorithm for topological sorting.

        Args:
            classes: List of classes to order.

        Returns:
            Ordered list of classes.

        Raises:
            ValueError: If circular dependencies are detected.
        """
        if not classes:
            return []

        # Build the graph
        graph = DependencyGraph()
        graph.add_classes(classes)

        # Validate first
        issues = graph.validate()
        circular = [i for i in issues if i.issue_type == "circular"]
        if circular:
            raise ValueError(
                f"Cannot order classes with circular dependencies: "
                f"{circular[0].message}"
            )

        # Build in-degree map (only considering internal dependencies)
        internal_iris = {c.iri for c in classes}
        in_degree: dict[str, int] = {c.iri: 0 for c in classes}

        for class_info in classes:
            for parent in graph.get_dependencies(class_info.iri):
                if parent in internal_iris:
                    in_degree[class_info.iri] += 1

        # Find all classes with no internal dependencies
        queue = [c.iri for c, deg in zip(classes, [in_degree[c.iri] for c in classes], strict=False) if deg == 0]
        ordered: list[str] = []

        while queue:
            node = queue.pop(0)
            ordered.append(node)

            # Decrease in-degree for all dependents
            for child in graph.get_dependents(node):
                if child in internal_iris:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)

        # Check if all nodes were processed
        if len(ordered) != len(classes):
            # This shouldn't happen if validation passed, but just in case
            remaining = [c.iri for c in classes if c.iri not in ordered]
            logger.warning(f"Could not order all classes: {remaining}")
            # Add remaining classes at the end
            ordered.extend(remaining)

        # Build result list maintaining ClassInfo objects
        iri_to_class = {c.iri: c for c in classes}
        return [iri_to_class[iri] for iri in ordered]

    def get_levels(self, classes: list[ClassInfo]) -> list[list[ClassInfo]]:
        """Group classes into processing levels.

        Classes in the same level can be processed in parallel.

        Args:
            classes: List of classes to group.

        Returns:
            List of levels, where each level is a list of classes.
        """
        if not classes:
            return []

        # Build graph
        graph = DependencyGraph()
        graph.add_classes(classes)

        internal_iris = {c.iri for c in classes}
        iri_to_class = {c.iri: c for c in classes}

        # Calculate levels using BFS
        in_degree: dict[str, int] = {c.iri: 0 for c in classes}
        for class_info in classes:
            for parent in graph.get_dependencies(class_info.iri):
                if parent in internal_iris:
                    in_degree[class_info.iri] += 1

        levels: list[list[ClassInfo]] = []
        current_level = [c.iri for c in classes if in_degree[c.iri] == 0]

        while current_level:
            levels.append([iri_to_class[iri] for iri in current_level])

            next_level: list[str] = []
            for node in current_level:
                for child in graph.get_dependents(node):
                    if child in internal_iris:
                        in_degree[child] -= 1
                        if in_degree[child] == 0:
                            next_level.append(child)

            current_level = next_level

        return levels


def order_by_dependency(classes: list[ClassInfo]) -> list[ClassInfo]:
    """Convenience function to order classes by dependency.

    Args:
        classes: Classes to order.

    Returns:
        Ordered list of classes.
    """
    orderer = DependencyOrderer()
    return orderer.order(classes)


def get_processing_levels(classes: list[ClassInfo]) -> list[list[ClassInfo]]:
    """Convenience function to get processing levels.

    Args:
        classes: Classes to group.

    Returns:
        List of processing levels.
    """
    orderer = DependencyOrderer()
    return orderer.get_levels(classes)
