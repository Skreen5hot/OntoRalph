"""Batch processing endpoints."""

import asyncio
import io
import json
import logging
import zipfile
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ontoralph.core.models import ClassInfo
from ontoralph.llm import ClaudeProvider, MockProvider, OpenAIProvider
from ontoralph.web.batch_manager import (
    BatchJob,
    JobStatus,
    get_batch_manager,
)
from ontoralph.web.models import (
    BatchClassResult,
    BatchJobStatus,
    BatchRequest,
    BatchResponse,
    BatchStatusResponse,
    ErrorCode,
)
from ontoralph.web.session_store import get_session_store

router = APIRouter(tags=["batch"])
logger = logging.getLogger(__name__)


def get_llm_provider(provider: str, api_key: str) -> Any:
    """Create an LLM provider instance."""
    if provider == "mock":
        return MockProvider()
    elif provider == "claude":
        return ClaudeProvider(api_key=api_key)
    elif provider == "openai":
        return OpenAIProvider(api_key=api_key)
    else:
        raise ValueError(f"Invalid provider: {provider}")


def job_to_status_response(job: BatchJob) -> BatchStatusResponse:
    """Convert a BatchJob to API response."""
    return BatchStatusResponse(
        job_id=job.job_id,
        status=BatchJobStatus(job.status.value),
        total_classes=job.total_classes,
        completed=job.completed_count,
        passed=job.passed_count,
        failed=job.failed_count,
        current_class=job.current_class,
        duration_seconds=job.duration_seconds,
        results=[
            BatchClassResult(
                iri=r.iri,
                status=r.status,
                final_definition=r.final_definition,
                error=r.error,
                total_iterations=r.total_iterations,
            )
            for r in job.results
        ],
        cancelled_at=job.cancelled_at,
    )


@router.post("/batch", response_model=BatchResponse)
async def create_batch_job(request: BatchRequest) -> BatchResponse:
    """Create a new batch processing job.

    The job starts processing immediately in the background.
    Use GET /api/batch/{job_id} to poll status or
    GET /api/batch/{job_id}/stream for SSE updates.

    Args:
        request: Batch job configuration

    Returns:
        Job ID and initial status
    """
    # Validate API key for non-mock providers
    if request.provider != "mock" and (
        not request.api_key or not request.api_key.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key is required for provider '{request.provider}'",
        )

    # Validate provider
    if request.provider not in ("claude", "openai", "mock"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}",
        )

    # Convert request classes to ClassInfo
    class_infos = [
        ClassInfo(
            iri=c.iri,
            label=c.label,
            parent_class=c.parent_class,
            sibling_classes=c.sibling_classes,
            is_ice=c.is_ice,
            current_definition=c.current_definition,
        )
        for c in request.classes
    ]

    # Create job
    manager = get_batch_manager()
    job = await manager.create_job(
        classes=class_infos,
        provider=request.provider,
        api_key=request.api_key or "",
        max_iterations=request.max_iterations,
    )

    # Start processing in background
    llm = get_llm_provider(request.provider, request.api_key or "")
    await manager.start_job(job.job_id, llm)

    return BatchResponse(
        job_id=job.job_id,
        status=BatchJobStatus(job.status.value),
        total_classes=job.total_classes,
        created_at=job.created_at,
    )


@router.get("/batch/{job_id}", response_model=BatchStatusResponse)
async def get_batch_status(job_id: str) -> BatchStatusResponse:
    """Get the status of a batch job.

    Args:
        job_id: The job ID

    Returns:
        Current job status and results
    """
    manager = get_batch_manager()
    job = await manager.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Job not found: {job_id}",
            },
        )

    return job_to_status_response(job)


@router.delete("/batch/{job_id}")
async def cancel_batch_job(job_id: str) -> dict[str, str]:
    """Cancel a running batch job.

    Args:
        job_id: The job ID to cancel

    Returns:
        Cancellation confirmation
    """
    manager = get_batch_manager()
    cancelled = await manager.cancel_job(job_id)

    if not cancelled:
        job = await manager.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": ErrorCode.NOT_FOUND.value,
                    "message": f"Job not found: {job_id}",
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not running (status: {job.status.value})",
            )

    return {"status": "cancelled", "job_id": job_id}


@router.get("/batch/{job_id}/stream")
async def stream_batch_progress(
    request: Request,
    job_id: str,
    token: str = Query(..., description="Session token"),
) -> EventSourceResponse:
    """Stream batch job progress via SSE.

    Event types:
    - class_start: Starting to process a class
    - class_complete: Class processing complete
    - class_error: Class processing failed
    - job_complete: All classes processed
    - job_error: Job failed

    Args:
        job_id: The job ID to stream
        token: Session token for authentication

    Returns:
        SSE event stream
    """
    # Validate session token
    session_store = get_session_store()
    session = session_store.validate_session(token)

    if session is None:

        async def error_generator() -> AsyncGenerator[dict[str, str], None]:
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "code": ErrorCode.INVALID_TOKEN.value,
                        "message": "Invalid or expired session token",
                    }
                ),
            }

        return EventSourceResponse(error_generator())

    manager = get_batch_manager()
    job = await manager.get_job(job_id)

    if job is None:

        async def not_found_generator() -> AsyncGenerator[dict[str, str], None]:
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "code": ErrorCode.NOT_FOUND.value,
                        "message": f"Job not found: {job_id}",
                    }
                ),
            }

        return EventSourceResponse(not_found_generator())

    async def stream_generator() -> AsyncGenerator[dict[str, str], None]:
        # Send initial status
        yield {
            "event": "status",
            "data": json.dumps(
                {
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "total": job.total_classes,
                    "completed": job.completed_count,
                }
            ),
        }

        # If job is already complete, send final status
        if job.status in (JobStatus.COMPLETE, JobStatus.CANCELLED, JobStatus.FAILED):
            yield {
                "event": "job_complete",
                "data": json.dumps(
                    {
                        "status": job.status.value,
                        "total": job.total_classes,
                        "passed": job.passed_count,
                        "failed": job.failed_count,
                        "duration_seconds": job.duration_seconds,
                    }
                ),
            }
            return

        # Poll for updates until complete
        last_completed = job.completed_count
        while job.status == JobStatus.RUNNING:
            # Check for client disconnect
            if await request.is_disconnected():
                break

            # Check for new completions
            current_completed = job.completed_count
            if current_completed > last_completed:
                # Send updates for newly completed classes
                for i in range(last_completed, current_completed):
                    result = job.results[i]
                    yield {
                        "event": "class_complete",
                        "data": json.dumps(
                            {
                                "index": i,
                                "iri": result.iri,
                                "label": result.label,
                                "status": result.status,
                                "final_definition": result.final_definition,
                            }
                        ),
                    }
                last_completed = current_completed

            # Send progress update
            yield {
                "event": "progress",
                "data": json.dumps(
                    {
                        "completed": job.completed_count,
                        "total": job.total_classes,
                        "current_class": job.current_class,
                    }
                ),
            }

            await asyncio.sleep(0.5)

        # Send final status
        yield {
            "event": "job_complete",
            "data": json.dumps(
                {
                    "status": job.status.value,
                    "total": job.total_classes,
                    "passed": job.passed_count,
                    "failed": job.failed_count,
                    "duration_seconds": job.duration_seconds,
                }
            ),
        }

    return EventSourceResponse(stream_generator())


@router.get("/batch/{job_id}/download")
async def download_batch_results(job_id: str) -> StreamingResponse:
    """Download batch results as a ZIP file.

    The ZIP contains:
    - SUMMARY.md: Overview of all results
    - One file per class with the definition

    Args:
        job_id: The job ID

    Returns:
        ZIP file download
    """
    manager = get_batch_manager()
    job = await manager.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": ErrorCode.NOT_FOUND.value, "message": "Job not found"},
        )

    if job.status not in (JobStatus.COMPLETE, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not complete",
        )

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Create summary
        summary_lines = [
            "# Batch Processing Summary",
            "",
            f"**Job ID:** {job.job_id}",
            f"**Status:** {job.status.value}",
            f"**Created:** {job.created_at.isoformat()}",
            f"**Duration:** {job.duration_seconds:.1f}s"
            if job.duration_seconds
            else "",
            "",
            "## Results",
            "",
            f"- **Total:** {job.total_classes}",
            f"- **Passed:** {job.passed_count}",
            f"- **Failed:** {job.failed_count}",
            "",
            "## Classes",
            "",
        ]

        for result in job.results:
            status_emoji = {
                "pass": "[PASS]",
                "fail": "[FAIL]",
                "error": "[ERROR]",
                "cancelled": "[CANCELLED]",
            }.get(result.status, "[?]")

            summary_lines.append(f"### {status_emoji} {result.label} (`{result.iri}`)")
            summary_lines.append("")

            if result.original_definition:
                summary_lines.append(f"**Original Definition:**  ")
                summary_lines.append(f'"{result.original_definition}"')
                summary_lines.append("")

            if result.final_definition:
                summary_lines.append(f"**Ralph:**  ")
                summary_lines.append(f"> {result.final_definition}")
            elif result.error:
                summary_lines.append(f"Error: {result.error}")
            else:
                summary_lines.append("No definition generated.")

            summary_lines.append("")

            if result.status == "fail" and result.failed_checks:
                summary_lines.append("**Failed Checks:**")
                for check in result.failed_checks:
                    summary_lines.append(
                        f"- **{check['code']}** {check['name']}: {check['evidence']}"
                    )
                summary_lines.append("")

        zf.writestr("SUMMARY.md", "\n".join(summary_lines))

        # Add individual files for successful results
        for result in job.results:
            if result.status == "pass" and result.final_definition:
                # Sanitize filename
                safe_name = (
                    result.iri.replace(":", "_")
                    .replace("/", "_")
                    .replace("\\", "_")
                    .replace("<", "")
                    .replace(">", "")
                )

                # Markdown file
                md_content = [
                    f"# {result.label}",
                    "",
                    f"**IRI:** `{result.iri}`",
                    "",
                    "## Definition",
                    "",
                    result.final_definition,
                    "",
                ]
                zf.writestr(f"definitions/{safe_name}.md", "\n".join(md_content))

                # JSON file
                json_content = {
                    "iri": result.iri,
                    "label": result.label,
                    "definition": result.final_definition,
                    "status": result.status,
                    "iterations": result.total_iterations,
                }
                zf.writestr(
                    f"definitions/{safe_name}.json",
                    json.dumps(json_content, indent=2),
                )

    zip_buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ontoralph_batch_{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
