"""Tests for web API models."""

from datetime import datetime, timedelta

import pytest

from ontoralph.web.models import (
    BatchClassInput,
    BatchJobStatus,
    BatchRequest,
    CheckResultResponse,
    ErrorCode,
    ErrorResponse,
    HealthResponse,
    IterationSummary,
    RunRequest,
    RunResponse,
    SessionRequest,
    SessionResponse,
    ValidateBatchRequest,
    ValidateDefinitionItem,
    ValidateRequest,
)


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_default_status(self) -> None:
        """Test default status is 'ok'."""
        response = HealthResponse(version="1.0.0")
        assert response.status == "ok"
        assert response.version == "1.0.0"

    def test_custom_status(self) -> None:
        """Test custom status."""
        response = HealthResponse(status="degraded", version="1.0.0")
        assert response.status == "degraded"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_minimal_error(self) -> None:
        """Test minimal error response."""
        error = ErrorResponse(
            code=ErrorCode.RATE_LIMIT,
            message="Rate limit exceeded",
        )
        assert error.code == ErrorCode.RATE_LIMIT
        assert error.message == "Rate limit exceeded"
        assert error.retryable is False
        assert error.retry_after is None

    def test_retryable_error(self) -> None:
        """Test retryable error with retry_after."""
        error = ErrorResponse(
            code=ErrorCode.RATE_LIMIT,
            message="Rate limit exceeded",
            retryable=True,
            retry_after=60,
        )
        assert error.retryable is True
        assert error.retry_after == 60


class TestSessionModels:
    """Tests for session-related models."""

    def test_session_request(self) -> None:
        """Test SessionRequest validation."""
        request = SessionRequest(
            provider="claude",
            api_key="sk-ant-test123",
        )
        assert request.provider == "claude"
        assert request.api_key == "sk-ant-test123"

    def test_session_response(self) -> None:
        """Test SessionResponse validation."""
        expires = datetime.now() + timedelta(minutes=30)
        response = SessionResponse(
            session_token="ort_abc123",
            expires_at=expires,
            provider="claude",
        )
        assert response.session_token == "ort_abc123"
        assert response.provider == "claude"


class TestValidateModels:
    """Tests for validation-related models."""

    def test_validate_request(self) -> None:
        """Test ValidateRequest validation."""
        request = ValidateRequest(
            definition="An ICE that is about something.",
            term="Test Term",
            is_ice=True,
        )
        assert request.definition == "An ICE that is about something."
        assert request.term == "Test Term"
        assert request.is_ice is True

    def test_validate_batch_request(self) -> None:
        """Test ValidateBatchRequest validation."""
        request = ValidateBatchRequest(
            definitions=[
                ValidateDefinitionItem(
                    label="Original",
                    definition="Def 1",
                    term="Term",
                    is_ice=True,
                ),
                ValidateDefinitionItem(
                    label="Candidate",
                    definition="Def 2",
                    term="Term",
                    is_ice=True,
                ),
            ]
        )
        assert len(request.definitions) == 2
        assert request.definitions[0].label == "Original"

    def test_validate_batch_request_min_length(self) -> None:
        """Test that batch request requires at least 2 definitions."""
        with pytest.raises(ValueError):
            ValidateBatchRequest(
                definitions=[
                    ValidateDefinitionItem(
                        label="Only One",
                        definition="Def",
                        term="Term",
                        is_ice=True,
                    )
                ]
            )

    def test_check_result_response(self) -> None:
        """Test CheckResultResponse validation."""
        result = CheckResultResponse(
            code="C1",
            name="Has Genus",
            passed=True,
            severity="required",
            evidence="Found genus: 'temporal instant'",
        )
        assert result.code == "C1"
        assert result.passed is True


class TestRunModels:
    """Tests for run-related models."""

    def test_run_request_minimal(self) -> None:
        """Test RunRequest with minimal fields."""
        request = RunRequest(
            iri=":TestClass",
            label="Test Class",
            parent_class="owl:Thing",
        )
        assert request.iri == ":TestClass"
        assert request.max_iterations == 5
        assert request.provider == "claude"
        assert request.api_key is None

    def test_run_request_full(self) -> None:
        """Test RunRequest with all fields."""
        request = RunRequest(
            iri=":EventTime",
            label="Event Time",
            parent_class="cco:ICE",
            sibling_classes=[":StartTime", ":EndTime"],
            is_ice=True,
            current_definition="An ICE...",
            max_iterations=3,
            provider="mock",
            api_key="test-key",
        )
        assert request.is_ice is True
        assert len(request.sibling_classes) == 2
        assert request.max_iterations == 3

    def test_run_request_max_iterations_bounds(self) -> None:
        """Test max_iterations bounds (1-10)."""
        # Valid
        request = RunRequest(
            iri=":Test",
            label="Test",
            parent_class="owl:Thing",
            max_iterations=1,
        )
        assert request.max_iterations == 1

        request = RunRequest(
            iri=":Test",
            label="Test",
            parent_class="owl:Thing",
            max_iterations=10,
        )
        assert request.max_iterations == 10

        # Invalid - below min
        with pytest.raises(ValueError):
            RunRequest(
                iri=":Test",
                label="Test",
                parent_class="owl:Thing",
                max_iterations=0,
            )

        # Invalid - above max
        with pytest.raises(ValueError):
            RunRequest(
                iri=":Test",
                label="Test",
                parent_class="owl:Thing",
                max_iterations=11,
            )

    def test_iteration_summary(self) -> None:
        """Test IterationSummary validation."""
        summary = IterationSummary(
            iteration=1,
            definition="An ICE that...",
            status="iterate",
            failed_checks=["I2", "Q1"],
        )
        assert summary.iteration == 1
        assert len(summary.failed_checks) == 2

    def test_run_response(self) -> None:
        """Test RunResponse validation."""
        response = RunResponse(
            status="pass",
            converged=True,
            final_definition="An ICE that is about the temporal instant...",
            total_iterations=3,
            duration_seconds=12.5,
            iterations=[
                IterationSummary(
                    iteration=1,
                    definition="Draft 1",
                    status="iterate",
                    failed_checks=["C2"],
                ),
            ],
            final_checks=[],
        )
        assert response.converged is True
        assert response.total_iterations == 3


class TestBatchModels:
    """Tests for batch-related models."""

    def test_batch_class_input(self) -> None:
        """Test BatchClassInput validation."""
        input_class = BatchClassInput(
            iri=":EventTime",
            label="Event Time",
            parent_class="cco:ICE",
            is_ice=True,
        )
        assert input_class.iri == ":EventTime"
        assert input_class.sibling_classes == []

    def test_batch_request(self) -> None:
        """Test BatchRequest validation."""
        request = BatchRequest(
            classes=[
                BatchClassInput(
                    iri=":A",
                    label="A",
                    parent_class="owl:Thing",
                ),
                BatchClassInput(
                    iri=":B",
                    label="B",
                    parent_class="owl:Thing",
                ),
            ],
            provider="mock",
        )
        assert len(request.classes) == 2
        assert request.max_iterations == 5

    def test_batch_job_status_enum(self) -> None:
        """Test BatchJobStatus enum values."""
        assert BatchJobStatus.PENDING == "pending"
        assert BatchJobStatus.RUNNING == "running"
        assert BatchJobStatus.COMPLETE == "complete"
        assert BatchJobStatus.CANCELLED == "cancelled"


class TestErrorCodeEnum:
    """Tests for ErrorCode enum."""

    def test_all_error_codes_exist(self) -> None:
        """Test all expected error codes exist."""
        expected = [
            "RATE_LIMIT",
            "API_ERROR",
            "TIMEOUT",
            "INVALID_RESPONSE",
            "SESSION_EXPIRED",
            "INVALID_TOKEN",
            "PROVIDER_UNAVAILABLE",
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "INTERNAL_ERROR",
        ]
        for code in expected:
            assert hasattr(ErrorCode, code)
