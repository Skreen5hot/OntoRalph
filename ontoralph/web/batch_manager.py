"""Batch job management for async processing.

This module provides background job processing for batch operations
on multiple classes.
"""

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ontoralph.core.loop import LoopConfig, RalphLoop
from ontoralph.core.models import ClassInfo, LoopResult

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status of a batch job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class ClassResult:
    """Result for a single class in a batch job."""

    iri: str
    label: str
    status: str  # 'pass', 'fail', 'error', 'pending', 'running'
    final_definition: str | None = None
    original_definition: str | None = None
    error: str | None = None
    total_iterations: int | None = None
    duration_seconds: float | None = None
    failed_checks: list[dict] | None = None  # [{code, name, evidence}]


@dataclass
class BatchJob:
    """Represents a batch processing job."""

    job_id: str
    status: JobStatus
    classes: list[ClassInfo]
    provider: str
    api_key: str
    max_iterations: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    results: list[ClassResult] = field(default_factory=list)
    current_index: int = 0
    task: asyncio.Task[None] | None = None

    @property
    def total_classes(self) -> int:
        """Total number of classes to process."""
        return len(self.classes)

    @property
    def completed_count(self) -> int:
        """Number of classes completed (passed or failed)."""
        return sum(1 for r in self.results if r.status in ("pass", "fail", "error"))

    @property
    def passed_count(self) -> int:
        """Number of classes that passed."""
        return sum(1 for r in self.results if r.status == "pass")

    @property
    def failed_count(self) -> int:
        """Number of classes that failed or errored."""
        return sum(1 for r in self.results if r.status in ("fail", "error"))

    @property
    def current_class(self) -> str | None:
        """IRI of the currently processing class."""
        if self.status == JobStatus.RUNNING and self.current_index < len(self.classes):
            return self.classes[self.current_index].iri
        return None

    @property
    def duration_seconds(self) -> float | None:
        """Total duration in seconds."""
        if self.started_at is None:
            return None
        end = self.completed_at or self.cancelled_at or datetime.now()
        return (end - self.started_at).total_seconds()


class BatchJobManager:
    """Manages batch processing jobs.

    Jobs are stored in memory and cleaned up after 1 hour.
    """

    def __init__(self, job_retention_seconds: int = 3600) -> None:
        """Initialize the batch job manager.

        Args:
            job_retention_seconds: How long to keep completed jobs (default: 1 hour)
        """
        self._jobs: dict[str, BatchJob] = {}
        self._retention_seconds = job_retention_seconds
        self._lock = asyncio.Lock()

    def _generate_job_id(self) -> str:
        """Generate a unique job ID."""
        return f"batch_{secrets.token_urlsafe(16)}"

    async def create_job(
        self,
        classes: list[ClassInfo],
        provider: str,
        api_key: str,
        max_iterations: int = 5,
    ) -> BatchJob:
        """Create a new batch job.

        Args:
            classes: List of classes to process
            provider: LLM provider name
            api_key: API key for the provider
            max_iterations: Max iterations per class

        Returns:
            The created BatchJob
        """
        await self._cleanup_old_jobs()

        job_id = self._generate_job_id()
        job = BatchJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            classes=classes,
            provider=provider,
            api_key=api_key,
            max_iterations=max_iterations,
            created_at=datetime.now(),
            results=[
                ClassResult(iri=c.iri, label=c.label, status="pending") for c in classes
            ],
        )

        async with self._lock:
            self._jobs[job_id] = job

        return job

    async def get_job(self, job_id: str) -> BatchJob | None:
        """Get a job by ID.

        Args:
            job_id: The job ID

        Returns:
            The BatchJob or None if not found
        """
        async with self._lock:
            return self._jobs.get(job_id)

    async def start_job(
        self,
        job_id: str,
        llm_provider: Any,
        event_callback: Any | None = None,
    ) -> None:
        """Start processing a batch job in the background.

        Args:
            job_id: The job ID to start
            llm_provider: LLM provider instance
            event_callback: Optional callback for progress events
        """
        job = await self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        if job.status != JobStatus.PENDING:
            raise ValueError(f"Job already started: {job_id}")

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()

        # Create background task
        job.task = asyncio.create_task(
            self._process_job(job, llm_provider, event_callback)
        )

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.

        Args:
            job_id: The job ID to cancel

        Returns:
            True if cancelled, False if not running
        """
        job = await self.get_job(job_id)
        if job is None:
            return False

        if job.status != JobStatus.RUNNING:
            return False

        job.status = JobStatus.CANCELLED
        job.cancelled_at = datetime.now()

        if job.task and not job.task.done():
            job.task.cancel()

        return True

    async def _process_job(
        self,
        job: BatchJob,
        llm_provider: Any,
        event_callback: Any | None = None,
    ) -> None:
        """Process all classes in a batch job.

        Args:
            job: The batch job to process
            llm_provider: LLM provider instance
            event_callback: Optional callback for progress events
        """
        config = LoopConfig(max_iterations=job.max_iterations)

        try:
            for i, class_info in enumerate(job.classes):
                # Check if cancelled
                if job.status == JobStatus.CANCELLED:
                    break

                job.current_index = i
                job.results[i].status = "running"

                # Notify event callback
                if event_callback:
                    await event_callback(
                        {
                            "event": "class_start",
                            "data": {
                                "index": i,
                                "iri": class_info.iri,
                                "label": class_info.label,
                                "total": job.total_classes,
                            },
                        }
                    )

                start_time = time.time()

                try:
                    loop = RalphLoop(llm=llm_provider, config=config)
                    result: LoopResult = await loop.run(class_info)

                    # Extract failed checks from last iteration
                    failed_checks = None
                    if not result.converged and result.iterations:
                        last_iter = result.iterations[-1]
                        failed = [c for c in last_iter.critique_results if not c.passed]
                        if failed:
                            failed_checks = [
                                {
                                    "code": c.code,
                                    "name": c.name,
                                    "evidence": c.evidence,
                                }
                                for c in failed
                            ]

                    job.results[i] = ClassResult(
                        iri=class_info.iri,
                        label=class_info.label,
                        status=result.status.value,
                        final_definition=result.final_definition,
                        original_definition=class_info.current_definition,
                        total_iterations=result.total_iterations,
                        duration_seconds=time.time() - start_time,
                        failed_checks=failed_checks,
                    )

                    if event_callback:
                        await event_callback(
                            {
                                "event": "class_complete",
                                "data": {
                                    "index": i,
                                    "iri": class_info.iri,
                                    "status": result.status.value,
                                    "final_definition": result.final_definition,
                                    "original_definition": class_info.current_definition,
                                    "iterations": result.total_iterations,
                                    "failed_checks": failed_checks,
                                },
                            }
                        )

                except asyncio.CancelledError:
                    job.results[i].status = "cancelled"
                    raise
                except Exception as e:
                    logger.exception(f"Error processing {class_info.iri}")
                    job.results[i] = ClassResult(
                        iri=class_info.iri,
                        label=class_info.label,
                        status="error",
                        error=str(e),
                        duration_seconds=time.time() - start_time,
                    )

                    if event_callback:
                        await event_callback(
                            {
                                "event": "class_error",
                                "data": {
                                    "index": i,
                                    "iri": class_info.iri,
                                    "error": str(e),
                                },
                            }
                        )

            # Job complete
            if job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETE
                job.completed_at = datetime.now()

                if event_callback:
                    await event_callback(
                        {
                            "event": "job_complete",
                            "data": {
                                "job_id": job.job_id,
                                "total": job.total_classes,
                                "passed": job.passed_count,
                                "failed": job.failed_count,
                                "duration_seconds": job.duration_seconds,
                            },
                        }
                    )

        except asyncio.CancelledError:
            logger.info(f"Batch job {job.job_id} was cancelled")
            job.status = JobStatus.CANCELLED
            job.cancelled_at = datetime.now()
        except Exception as e:
            logger.exception(f"Batch job {job.job_id} failed")
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()

            if event_callback:
                await event_callback(
                    {
                        "event": "job_error",
                        "data": {
                            "job_id": job.job_id,
                            "error": str(e),
                        },
                    }
                )

    async def _cleanup_old_jobs(self) -> None:
        """Remove jobs older than retention period."""
        now = datetime.now()
        to_remove = []

        async with self._lock:
            for job_id, job in self._jobs.items():
                # Only clean up completed/cancelled/failed jobs
                if job.status in (
                    JobStatus.COMPLETE,
                    JobStatus.CANCELLED,
                    JobStatus.FAILED,
                ):
                    end_time = job.completed_at or job.cancelled_at
                    if (
                        end_time
                        and (now - end_time).total_seconds() > self._retention_seconds
                    ):
                        to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old batch jobs")

    def job_count(self) -> int:
        """Number of jobs currently tracked."""
        return len(self._jobs)


# Global batch job manager instance
_batch_manager: BatchJobManager | None = None


def get_batch_manager() -> BatchJobManager:
    """Get the global batch job manager instance.

    Returns:
        The singleton BatchJobManager instance
    """
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchJobManager()
    return _batch_manager


def reset_batch_manager() -> None:
    """Reset the global batch job manager (for testing)."""
    global _batch_manager
    _batch_manager = None
