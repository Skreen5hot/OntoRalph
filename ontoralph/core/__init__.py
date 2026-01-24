"""Core OntoRalph functionality: loop controller, checklist, and data models."""

from ontoralph.core.checklist import (
    ChecklistEvaluator,
    CircularityChecker,
    RedFlagDetector,
)
from ontoralph.core.loop import (
    CountingHooks,
    HybridCheckResult,
    LoggingHooks,
    LoopConfig,
    LoopHooks,
    RalphLoop,
)
from ontoralph.core.models import (
    CheckResult,
    ClassInfo,
    LoopIteration,
    LoopResult,
    LoopState,
    Severity,
    VerifyStatus,
)

__all__ = [
    # Models
    "ClassInfo",
    "CheckResult",
    "LoopIteration",
    "LoopResult",
    "LoopState",
    "Severity",
    "VerifyStatus",
    # Checklist
    "ChecklistEvaluator",
    "CircularityChecker",
    "RedFlagDetector",
    # Loop
    "RalphLoop",
    "LoopConfig",
    "LoopHooks",
    "LoggingHooks",
    "CountingHooks",
    "HybridCheckResult",
]
