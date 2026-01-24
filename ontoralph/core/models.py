"""Data models for OntoRalph.

This module defines the core Pydantic models used throughout OntoRalph
for representing class information, check results, and loop state.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for checklist items."""

    REQUIRED = "required"  # Core requirements (C1-C4)
    ICE_REQUIRED = "ice_required"  # ICE-specific requirements (I1-I3)
    QUALITY = "quality"  # Quality checks (Q1-Q3)
    RED_FLAG = "red_flag"  # Auto-fail patterns (R1-R4)


class VerifyStatus(str, Enum):
    """Result of the VERIFY phase."""

    PASS = "pass"  # All required checks pass, no red flags
    FAIL = "fail"  # Core check fails or red flag present
    ITERATE = "iterate"  # Quality checks fail but core passes


class ClassInfo(BaseModel):
    """Information about an ontology class to be refined.

    This is the primary input to the Ralph Loop.
    """

    iri: str = Field(description="The IRI of the class, e.g., ':VerbPhrase'")
    label: str = Field(description="Human-readable label, e.g., 'Verb Phrase'")
    parent_class: str = Field(
        description="Parent class IRI, e.g., 'cco:InformationContentEntity'"
    )
    sibling_classes: list[str] = Field(
        default_factory=list,
        description="List of sibling class IRIs for exclusivity checking",
    )
    is_ice: bool = Field(
        default=False,
        description="Whether this is an Information Content Entity",
    )
    current_definition: Optional[str] = Field(
        default=None,
        description="Current definition to improve, or None for new class",
    )

    model_config = {"extra": "forbid"}


class CheckResult(BaseModel):
    """Result of a single checklist item evaluation.

    Each check in the Ralph Loop checklist produces one of these.
    """

    code: str = Field(description="Check code, e.g., 'C1', 'I2', 'R3'")
    name: str = Field(description="Human-readable check name")
    passed: bool = Field(description="Whether the check passed")
    evidence: str = Field(
        description="Evidence supporting the pass/fail determination"
    )
    severity: Severity = Field(description="Severity level of this check")

    model_config = {"extra": "forbid"}


class LoopIteration(BaseModel):
    """Record of a single iteration through the Ralph Loop.

    Captures the definition, critique results, and refinement for one cycle.
    """

    iteration_number: int = Field(ge=1, description="1-indexed iteration number")
    generated_definition: str = Field(
        description="Definition produced in GENERATE phase"
    )
    critique_results: list[CheckResult] = Field(
        description="Results from CRITIQUE phase"
    )
    refined_definition: Optional[str] = Field(
        default=None,
        description="Definition after REFINE phase (if refinement was needed)",
    )
    verify_status: VerifyStatus = Field(description="Result of VERIFY phase")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this iteration completed",
    )

    model_config = {"extra": "forbid"}

    @property
    def final_definition(self) -> str:
        """The definition to use: refined if available, otherwise generated."""
        return self.refined_definition or self.generated_definition

    @property
    def failed_checks(self) -> list[CheckResult]:
        """All checks that did not pass."""
        return [c for c in self.critique_results if not c.passed]

    @property
    def red_flags(self) -> list[CheckResult]:
        """Red flag checks that did not pass."""
        return [
            c
            for c in self.critique_results
            if not c.passed and c.severity == Severity.RED_FLAG
        ]


class LoopState(BaseModel):
    """Current state of the Ralph Loop.

    This is the mutable state passed through each iteration.
    """

    class_info: ClassInfo = Field(description="The class being refined")
    iterations: list[LoopIteration] = Field(
        default_factory=list,
        description="History of all iterations",
    )
    max_iterations: int = Field(
        default=5,
        description="Maximum iterations before giving up",
    )
    started_at: datetime = Field(
        default_factory=datetime.now,
        description="When the loop started",
    )

    model_config = {"extra": "forbid"}

    @property
    def current_iteration(self) -> int:
        """Number of iterations completed."""
        return len(self.iterations)

    @property
    def is_complete(self) -> bool:
        """Whether the loop has terminated (pass or max iterations)."""
        if not self.iterations:
            return False
        last = self.iterations[-1]
        return (
            last.verify_status == VerifyStatus.PASS
            or self.current_iteration >= self.max_iterations
        )

    @property
    def latest_definition(self) -> Optional[str]:
        """Most recent definition, or the initial definition if no iterations."""
        if self.iterations:
            return self.iterations[-1].final_definition
        return self.class_info.current_definition


class LoopResult(BaseModel):
    """Final result of the Ralph Loop.

    This is returned when the loop completes.
    """

    class_info: ClassInfo = Field(description="The class that was refined")
    final_definition: str = Field(description="The final refined definition")
    status: VerifyStatus = Field(description="Final status (PASS or FAIL)")
    iterations: list[LoopIteration] = Field(description="All iterations performed")
    total_iterations: int = Field(description="Number of iterations performed")
    started_at: datetime = Field(description="When the loop started")
    completed_at: datetime = Field(
        default_factory=datetime.now,
        description="When the loop completed",
    )

    model_config = {"extra": "forbid"}

    @property
    def duration_seconds(self) -> float:
        """Total time taken for the loop."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def converged(self) -> bool:
        """Whether the loop achieved a passing definition."""
        return self.status == VerifyStatus.PASS
