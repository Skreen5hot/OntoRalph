"""Batch processing module for OntoRalph.

This module provides advanced batch processing capabilities including:
- Parallel processing with configurable concurrency
- Dependency ordering (parents before children)
- Sibling exclusivity checking
- Cross-class consistency validation
- BFO/CCO pattern validation
- Batch integrity checking
"""

from ontoralph.batch.consistency import (
    ConsistencyIssue,
    ConsistencyIssueType,
    ContradictionDetector,
    CrossClassConsistencyChecker,
    PatternAnalyzer,
    TerminologyAnalyzer,
    check_consistency,
)
from ontoralph.batch.dependency import (
    DependencyGraph,
    DependencyIssue,
    DependencyOrderer,
    get_processing_levels,
    order_by_dependency,
)
from ontoralph.batch.processor import (
    BatchConfig,
    BatchProcessor,
    BatchProgress,
    BatchResult,
    BatchState,
    process_batch,
)
from ontoralph.batch.sibling import (
    ExclusivityIssue,
    OverlapType,
    SiblingExclusivityChecker,
    check_sibling_exclusivity,
)
from ontoralph.batch.validator import (
    BatchIntegrityChecker,
    DuplicateLabelIssue,
    IssueSeverity,
    NamespaceIssue,
    PunningIssue,
    TurtleValidator,
    ValidationIssue,
    check_batch_integrity,
    validate_turtle_output,
)

__all__ = [
    # Processor
    "BatchConfig",
    "BatchProcessor",
    "BatchProgress",
    "BatchResult",
    "BatchState",
    "process_batch",
    # Dependency
    "DependencyGraph",
    "DependencyIssue",
    "DependencyOrderer",
    "get_processing_levels",
    "order_by_dependency",
    # Sibling
    "ExclusivityIssue",
    "OverlapType",
    "SiblingExclusivityChecker",
    "check_sibling_exclusivity",
    # Consistency
    "ConsistencyIssue",
    "ConsistencyIssueType",
    "ContradictionDetector",
    "CrossClassConsistencyChecker",
    "PatternAnalyzer",
    "TerminologyAnalyzer",
    "check_consistency",
    # Validator
    "BatchIntegrityChecker",
    "DuplicateLabelIssue",
    "IssueSeverity",
    "NamespaceIssue",
    "PunningIssue",
    "TurtleValidator",
    "ValidationIssue",
    "check_batch_integrity",
    "validate_turtle_output",
]
