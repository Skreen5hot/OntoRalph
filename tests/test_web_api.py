"""Tests for web API endpoints."""

import pytest
from fastapi.testclient import TestClient

from ontoralph.web.batch_manager import reset_batch_manager
from ontoralph.web.server import create_app
from ontoralph.web.session_store import reset_session_store


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    reset_session_store()
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Test health endpoint returns ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_returns_version(self, client: TestClient) -> None:
        """Test health endpoint returns version."""
        response = client.get("/api/health")
        data = response.json()
        # Version should be a string like "1.0.0"
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0


class TestSessionEndpoint:
    """Tests for /api/session endpoint."""

    def test_create_session_success(self, client: TestClient) -> None:
        """Test creating a session with valid data."""
        response = client.post(
            "/api/session",
            json={"provider": "claude", "api_key": "sk-ant-test123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_token" in data
        assert data["session_token"].startswith("ort_")
        assert data["provider"] == "claude"
        assert "expires_at" in data

    def test_create_session_mock_provider(self, client: TestClient) -> None:
        """Test creating a session with mock provider."""
        response = client.post(
            "/api/session",
            json={"provider": "mock", "api_key": "any-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "mock"

    def test_create_session_invalid_provider(self, client: TestClient) -> None:
        """Test creating a session with invalid provider."""
        response = client.post(
            "/api/session",
            json={"provider": "invalid", "api_key": "key"},
        )
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    def test_create_session_empty_api_key(self, client: TestClient) -> None:
        """Test creating a session with empty API key."""
        response = client.post(
            "/api/session",
            json={"provider": "claude", "api_key": ""},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_create_session_whitespace_api_key(self, client: TestClient) -> None:
        """Test creating a session with whitespace-only API key."""
        response = client.post(
            "/api/session",
            json={"provider": "claude", "api_key": "   "},
        )
        assert response.status_code == 400


class TestValidateEndpoint:
    """Tests for /api/validate endpoint."""

    def test_validate_single_definition(self, client: TestClient) -> None:
        """Test validating a single definition."""
        response = client.post(
            "/api/validate",
            json={
                "definition": "An ICE that is about the temporal instant at which an event occurs.",
                "term": "Event Time",
                "is_ice": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "results" in data
        assert "passed_count" in data
        assert "failed_count" in data
        assert isinstance(data["results"], list)

    def test_validate_non_ice_definition(self, client: TestClient) -> None:
        """Test validating a non-ICE definition."""
        response = client.post(
            "/api/validate",
            json={
                "definition": "A sensor is an artifact that detects physical phenomena.",
                "term": "Sensor",
                "is_ice": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_validate_empty_definition(self, client: TestClient) -> None:
        """Test validating empty definition returns error."""
        response = client.post(
            "/api/validate",
            json={
                "definition": "",
                "term": "Test",
                "is_ice": True,
            },
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_validate_batch_comparison(self, client: TestClient) -> None:
        """Test validating multiple definitions for comparison."""
        response = client.post(
            "/api/validate",
            json={
                "definitions": [
                    {
                        "label": "Original",
                        "definition": "An event time is the time of an event.",
                        "term": "Event Time",
                        "is_ice": True,
                    },
                    {
                        "label": "Improved",
                        "definition": "An ICE that is about the temporal instant at which an event occurs.",
                        "term": "Event Time",
                        "is_ice": True,
                    },
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data
        assert len(data["comparisons"]) == 2
        assert data["comparisons"][0]["label"] == "Original"
        assert data["comparisons"][1]["label"] == "Improved"

    def test_validate_check_results_structure(self, client: TestClient) -> None:
        """Test that check results have correct structure."""
        response = client.post(
            "/api/validate",
            json={
                "definition": "An ICE that is about something.",
                "term": "Test",
                "is_ice": True,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check result structure
        for result in data["results"]:
            assert "code" in result
            assert "name" in result
            assert "passed" in result
            assert "severity" in result
            assert "evidence" in result
            assert isinstance(result["passed"], bool)


class TestRunEndpoint:
    """Tests for /api/run endpoint."""

    def test_run_with_mock_provider(self, client: TestClient) -> None:
        """Test running Ralph Loop with mock provider."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
                "is_ice": False,
                "provider": "mock",
                "api_key": "not-needed",
                "max_iterations": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "converged" in data
        assert "final_definition" in data
        assert "total_iterations" in data
        assert "duration_seconds" in data
        assert "iterations" in data
        assert "final_checks" in data

    def test_run_with_ice_class(self, client: TestClient) -> None:
        """Test running Ralph Loop with ICE class."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":EventTime",
                "label": "Event Time",
                "parent_class": "cco:InformationContentEntity",
                "is_ice": True,
                "provider": "mock",
                "api_key": "not-needed",
                "max_iterations": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_iterations"] >= 1

    def test_run_with_siblings(self, client: TestClient) -> None:
        """Test running with sibling classes."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":EventTime",
                "label": "Event Time",
                "parent_class": "cco:ICE",
                "sibling_classes": [":StartTime", ":EndTime"],
                "is_ice": True,
                "provider": "mock",
                "api_key": "not-needed",
                "max_iterations": 1,
            },
        )
        assert response.status_code == 200

    def test_run_with_current_definition(self, client: TestClient) -> None:
        """Test running with an existing definition to improve."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
                "current_definition": "An existing definition to improve.",
                "provider": "mock",
                "api_key": "not-needed",
                "max_iterations": 1,
            },
        )
        assert response.status_code == 200

    def test_run_without_api_key_for_claude(self, client: TestClient) -> None:
        """Test that Claude provider requires API key."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
                "provider": "claude",
                # Missing api_key
            },
        )
        assert response.status_code == 400
        assert "API key" in response.json()["detail"]

    def test_run_without_api_key_for_openai(self, client: TestClient) -> None:
        """Test that OpenAI provider requires API key."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
                "provider": "openai",
                # Missing api_key
            },
        )
        assert response.status_code == 400
        assert "API key" in response.json()["detail"]

    def test_run_invalid_provider(self, client: TestClient) -> None:
        """Test that invalid provider returns error."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
                "provider": "invalid",
                "api_key": "key",
            },
        )
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    def test_run_iteration_structure(self, client: TestClient) -> None:
        """Test that iteration summaries have correct structure."""
        response = client.post(
            "/api/run",
            json={
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
                "provider": "mock",
                "api_key": "not-needed",
                "max_iterations": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()

        for iteration in data["iterations"]:
            assert "iteration" in iteration
            assert "definition" in iteration
            assert "status" in iteration
            assert "failed_checks" in iteration
            assert isinstance(iteration["failed_checks"], list)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_content(self, client: TestClient) -> None:
        """Test that root endpoint returns something."""
        response = client.get("/")
        # Could be 200 (index.html) or 200 (JSON message)
        assert response.status_code == 200


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client: TestClient) -> None:
        """Test that CORS headers are present for allowed origins."""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:8765",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI returns 200 for OPTIONS
        assert response.status_code == 200


class TestRunStreamEndpoint:
    """Tests for /api/run/stream SSE endpoint."""

    def test_stream_requires_token(self, client: TestClient) -> None:
        """Test that SSE endpoint requires a session token."""
        # Note: Without a valid token, the SSE endpoint returns an error event
        # We can't easily test SSE with the sync TestClient, but we can verify
        # the endpoint exists and responds
        response = client.get(
            "/api/run/stream",
            params={
                "token": "invalid-token",
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
            },
        )
        # SSE responses have content-type text/event-stream
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_with_valid_session(self, client: TestClient) -> None:
        """Test SSE endpoint with a valid session token."""
        # First create a session
        session_response = client.post(
            "/api/session",
            json={"provider": "mock", "api_key": "test-key"},
        )
        assert session_response.status_code == 200
        token = session_response.json()["session_token"]

        # Now try the stream endpoint
        response = client.get(
            "/api/run/stream",
            params={
                "token": token,
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
                "is_ice": "false",
                "max_iterations": "2",
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # The response body should contain SSE events
        content = response.text
        # Should have at least iteration_start and complete events
        assert "event:" in content or "data:" in content

    def test_stream_invalid_token_returns_error_event(
        self, client: TestClient
    ) -> None:
        """Test that invalid token returns an error SSE event."""
        response = client.get(
            "/api/run/stream",
            params={
                "token": "invalid-token-here",
                "iri": ":TestClass",
                "label": "Test Class",
                "parent_class": "owl:Thing",
            },
        )
        assert response.status_code == 200
        content = response.text
        # Should contain error event with INVALID_TOKEN
        assert "error" in content
        assert "INVALID_TOKEN" in content


class TestBatchEndpoints:
    """Tests for /api/batch endpoints."""

    @pytest.fixture(autouse=True)
    def reset_manager(self) -> None:
        """Reset batch manager before each test."""
        reset_batch_manager()

    def test_create_batch_job_with_mock(self, client: TestClient) -> None:
        """Test creating a batch job with mock provider."""
        response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": ":TestClass1",
                        "label": "Test Class 1",
                        "parent_class": "owl:Thing",
                        "is_ice": False,
                    },
                    {
                        "iri": ":TestClass2",
                        "label": "Test Class 2",
                        "parent_class": "owl:Thing",
                        "is_ice": False,
                    },
                ],
                "provider": "mock",
                "max_iterations": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["job_id"].startswith("batch_")
        assert data["status"] == "running"
        assert data["total_classes"] == 2
        assert "created_at" in data

    def test_create_batch_job_requires_api_key_for_claude(
        self, client: TestClient
    ) -> None:
        """Test that Claude provider requires API key."""
        response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": ":TestClass",
                        "label": "Test Class",
                        "parent_class": "owl:Thing",
                    }
                ],
                "provider": "claude",
            },
        )
        assert response.status_code == 400
        assert "API key" in response.json()["detail"]

    def test_create_batch_job_invalid_provider(self, client: TestClient) -> None:
        """Test that invalid provider returns error."""
        response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": ":TestClass",
                        "label": "Test Class",
                        "parent_class": "owl:Thing",
                    }
                ],
                "provider": "invalid",
                "api_key": "key",
            },
        )
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    def test_get_batch_status(self, client: TestClient) -> None:
        """Test getting batch job status."""
        # Create a job first
        create_response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": ":TestClass",
                        "label": "Test Class",
                        "parent_class": "owl:Thing",
                    }
                ],
                "provider": "mock",
                "max_iterations": 1,
            },
        )
        job_id = create_response.json()["job_id"]

        # Get status
        response = client.get(f"/api/batch/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "total_classes" in data
        assert "completed" in data
        assert "passed" in data
        assert "failed" in data

    def test_get_batch_status_not_found(self, client: TestClient) -> None:
        """Test getting status of non-existent job."""
        response = client.get("/api/batch/nonexistent-job-id")
        assert response.status_code == 404
        assert "NOT_FOUND" in response.json()["detail"]["code"]

    def test_cancel_batch_job(self, client: TestClient) -> None:
        """Test cancelling a batch job."""
        # Create a job
        create_response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": f":TestClass{i}",
                        "label": f"Test Class {i}",
                        "parent_class": "owl:Thing",
                    }
                    for i in range(5)
                ],
                "provider": "mock",
                "max_iterations": 5,
            },
        )
        job_id = create_response.json()["job_id"]

        # Cancel it - may succeed (200) if still running,
        # or fail (400) if already completed
        response = client.delete(f"/api/batch/{job_id}")
        # Accept either outcome since mock provider is very fast
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            assert response.json()["status"] == "cancelled"
            assert response.json()["job_id"] == job_id

    def test_cancel_nonexistent_job(self, client: TestClient) -> None:
        """Test cancelling a non-existent job."""
        response = client.delete("/api/batch/nonexistent-job-id")
        assert response.status_code == 404

    def test_batch_stream_requires_token(self, client: TestClient) -> None:
        """Test that batch stream endpoint requires a session token."""
        # Create a job first
        create_response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": ":TestClass",
                        "label": "Test Class",
                        "parent_class": "owl:Thing",
                    }
                ],
                "provider": "mock",
            },
        )
        job_id = create_response.json()["job_id"]

        # Try to stream with invalid token
        response = client.get(
            f"/api/batch/{job_id}/stream",
            params={"token": "invalid-token"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        assert "error" in content
        assert "INVALID_TOKEN" in content

    def test_batch_stream_with_valid_session(self, client: TestClient) -> None:
        """Test batch stream endpoint with valid session."""
        # Create session
        session_response = client.post(
            "/api/session",
            json={"provider": "mock", "api_key": "test-key"},
        )
        token = session_response.json()["session_token"]

        # Create a job
        create_response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": ":TestClass",
                        "label": "Test Class",
                        "parent_class": "owl:Thing",
                    }
                ],
                "provider": "mock",
                "max_iterations": 1,
            },
        )
        job_id = create_response.json()["job_id"]

        # Stream progress
        response = client.get(
            f"/api/batch/{job_id}/stream",
            params={"token": token},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        # Should contain status or job_complete events
        assert "event:" in content or "data:" in content

    def test_batch_download_not_ready(self, client: TestClient) -> None:
        """Test downloading results before job is complete."""
        # Create a job with many classes so it won't complete instantly
        create_response = client.post(
            "/api/batch",
            json={
                "classes": [
                    {
                        "iri": f":TestClass{i}",
                        "label": f"Test Class {i}",
                        "parent_class": "owl:Thing",
                    }
                    for i in range(10)
                ],
                "provider": "mock",
                "max_iterations": 5,
            },
        )
        job_id = create_response.json()["job_id"]

        # Try to download immediately (should fail if still running)
        response = client.get(f"/api/batch/{job_id}/download")
        # Either 400 (not complete) or 200 (if it completed very fast)
        assert response.status_code in (200, 400)

    def test_batch_download_not_found(self, client: TestClient) -> None:
        """Test downloading results for non-existent job."""
        response = client.get("/api/batch/nonexistent-job/download")
        assert response.status_code == 404
