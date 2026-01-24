"""Pydantic models for the OntoRalph Web API.

These models define the request/response schemas for all API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Error Codes
# =============================================================================


class ErrorCode(str, Enum):
    """Structured error codes for API responses."""

    RATE_LIMIT = "RATE_LIMIT"
    API_ERROR = "API_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """Structured error response."""

    code: ErrorCode = Field(description="Error code for programmatic handling")
    message: str = Field(description="Human-readable error message")
    retryable: bool = Field(
        default=False, description="Whether the request can be retried"
    )
    retry_after: int | None = Field(
        default=None, description="Seconds to wait before retry (if retryable)"
    )
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )


# =============================================================================
# Health Endpoint
# =============================================================================


class HealthResponse(BaseModel):
    """Response from /api/health."""

    status: str = Field(default="ok", description="Service status")
    version: str = Field(description="OntoRalph version")


# =============================================================================
# Session Endpoint
# =============================================================================


class SessionRequest(BaseModel):
    """Request to create a session token."""

    provider: str = Field(description="LLM provider: 'claude', 'openai', or 'mock'")
    api_key: str = Field(description="API key for the provider")


class SessionResponse(BaseModel):
    """Response with session token."""

    session_token: str = Field(description="Session token for SSE endpoints")
    expires_at: datetime = Field(description="Token expiration time")
    provider: str = Field(description="The provider this token is for")


# =============================================================================
# Validate Endpoint
# =============================================================================


class ValidateRequest(BaseModel):
    """Request to validate a single definition."""

    definition: str = Field(description="The definition to validate")
    term: str = Field(description="The term being defined (for circularity check)")
    is_ice: bool = Field(default=True, description="Whether this is an ICE definition")


class ValidateDefinitionItem(BaseModel):
    """A single definition in a batch comparison request."""

    label: str = Field(description="Label for this definition (e.g., 'Original')")
    definition: str = Field(description="The definition to validate")
    term: str = Field(description="The term being defined")
    is_ice: bool = Field(default=True, description="Whether this is an ICE definition")


class ValidateBatchRequest(BaseModel):
    """Request to validate multiple definitions for comparison."""

    definitions: list[ValidateDefinitionItem] = Field(
        min_length=2,
        max_length=10,
        description="List of definitions to compare",
    )


class CheckResultResponse(BaseModel):
    """A single check result."""

    code: str = Field(description="Check code, e.g., 'C1', 'I2', 'R3'")
    name: str = Field(description="Human-readable check name")
    passed: bool = Field(description="Whether the check passed")
    severity: str = Field(
        description="Severity level: required, ice_required, quality, red_flag"
    )
    evidence: str = Field(description="Evidence supporting the pass/fail determination")


class ValidateResponse(BaseModel):
    """Response from single definition validation."""

    status: str = Field(description="Overall status: pass, fail, or iterate")
    results: list[CheckResultResponse] = Field(description="All check results")
    passed_count: int = Field(description="Number of checks that passed")
    failed_count: int = Field(description="Number of checks that failed")


class ValidateComparisonItem(BaseModel):
    """Validation result for one definition in a comparison."""

    label: str = Field(description="Label for this definition")
    status: str = Field(description="Overall status: pass, fail, or iterate")
    passed_count: int = Field(description="Number of checks that passed")
    failed_count: int = Field(description="Number of checks that failed")
    results: list[CheckResultResponse] = Field(description="All check results")


class ValidateBatchResponse(BaseModel):
    """Response from batch validation comparison."""

    comparisons: list[ValidateComparisonItem] = Field(
        description="Results for each definition"
    )


# =============================================================================
# Run Endpoint
# =============================================================================


class RunRequest(BaseModel):
    """Request to run the Ralph Loop for a single class."""

    iri: str = Field(description="The IRI of the class, e.g., ':VerbPhrase'")
    label: str = Field(description="Human-readable label, e.g., 'Verb Phrase'")
    parent_class: str = Field(
        description="Parent class IRI, e.g., 'cco:InformationContentEntity'"
    )
    sibling_classes: list[str] = Field(
        default_factory=list,
        description="List of sibling class IRIs",
    )
    is_ice: bool = Field(
        default=False, description="Whether this is an Information Content Entity"
    )
    current_definition: str | None = Field(
        default=None, description="Current definition to improve, or None for new"
    )
    max_iterations: int = Field(
        default=5, ge=1, le=10, description="Maximum iterations before giving up"
    )
    provider: str = Field(
        default="claude", description="LLM provider: 'claude', 'openai', or 'mock'"
    )
    api_key: str | None = Field(
        default=None, description="API key (not needed for mock provider)"
    )
    custom_prompts: dict[str, str] | None = Field(
        default=None, description="Custom prompt templates (advanced)"
    )


class IterationSummary(BaseModel):
    """Summary of a single loop iteration."""

    iteration: int = Field(description="1-indexed iteration number")
    definition: str = Field(description="Definition at end of this iteration")
    status: str = Field(description="Verify status: pass, fail, or iterate")
    failed_checks: list[str] = Field(
        description="Codes of failed checks, e.g., ['I2', 'Q1']"
    )


class RunResponse(BaseModel):
    """Response from running the Ralph Loop."""

    status: str = Field(description="Final status: pass or fail")
    converged: bool = Field(description="Whether a passing definition was achieved")
    final_definition: str = Field(description="The final refined definition")
    total_iterations: int = Field(description="Number of iterations performed")
    duration_seconds: float = Field(description="Total time taken in seconds")
    iterations: list[IterationSummary] = Field(description="Summary of each iteration")
    final_checks: list[CheckResultResponse] = Field(description="Final check results")


# =============================================================================
# Batch Endpoint
# =============================================================================


class BatchClassInput(BaseModel):
    """Input for a single class in a batch job."""

    iri: str = Field(description="The IRI of the class")
    label: str = Field(description="Human-readable label")
    parent_class: str = Field(description="Parent class IRI")
    sibling_classes: list[str] = Field(
        default_factory=list, description="Sibling class IRIs"
    )
    is_ice: bool = Field(default=False, description="Whether this is an ICE")
    current_definition: str | None = Field(
        default=None, description="Current definition to improve"
    )


class BatchRequest(BaseModel):
    """Request to start a batch processing job."""

    classes: list[BatchClassInput] = Field(
        min_length=1, description="List of classes to process"
    )
    max_iterations: int = Field(
        default=5, ge=1, le=10, description="Max iterations per class"
    )
    provider: str = Field(default="claude", description="LLM provider")
    api_key: str | None = Field(
        default=None, description="API key (not needed for mock)"
    )


class BatchJobStatus(str, Enum):
    """Status of a batch job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BatchClassResult(BaseModel):
    """Result for a single class in a batch job."""

    iri: str = Field(description="The class IRI")
    status: str = Field(description="Final status: pass, fail, or error")
    final_definition: str | None = Field(
        default=None, description="Final definition (if processed)"
    )
    error: str | None = Field(default=None, description="Error message (if failed)")
    total_iterations: int | None = Field(
        default=None, description="Iterations performed"
    )


class BatchResponse(BaseModel):
    """Response when creating a batch job."""

    job_id: str = Field(description="Unique job identifier")
    status: BatchJobStatus = Field(description="Initial job status")
    total_classes: int = Field(description="Number of classes to process")
    created_at: datetime = Field(description="Job creation timestamp")


class BatchStatusResponse(BaseModel):
    """Response for batch job status query."""

    job_id: str = Field(description="Job identifier")
    status: BatchJobStatus = Field(description="Current job status")
    total_classes: int = Field(description="Total classes to process")
    completed: int = Field(description="Number of classes completed")
    passed: int = Field(description="Number that passed")
    failed: int = Field(description="Number that failed")
    current_class: str | None = Field(
        default=None, description="Currently processing class IRI"
    )
    duration_seconds: float | None = Field(
        default=None, description="Total duration (if complete)"
    )
    results: list[BatchClassResult] = Field(
        default_factory=list, description="Results for completed classes"
    )
    cancelled_at: datetime | None = Field(
        default=None, description="Cancellation timestamp (if cancelled)"
    )


# =============================================================================
# SSE Event Models (for documentation/typing)
# =============================================================================


class SSEIterationStart(BaseModel):
    """SSE event: iteration starting."""

    iteration: int
    max_iterations: int


class SSEGenerate(BaseModel):
    """SSE event: definition generated."""

    definition: str


class SSECritique(BaseModel):
    """SSE event: critique complete."""

    status: str
    failed_checks: list[str]
    failed_count: int


class SSERefine(BaseModel):
    """SSE event: refinement complete."""

    definition: str


class SSEVerify(BaseModel):
    """SSE event: verification complete."""

    status: str
    passed_count: int
    failed_count: int


class SSEComplete(BaseModel):
    """SSE event: loop complete."""

    result: RunResponse


class SSEError(BaseModel):
    """SSE event: error occurred."""

    code: str
    message: str
    retryable: bool
    retry_after: int | None = None
