"""Parallel batch processor for OntoRalph.

This module provides concurrent processing of multiple ontology classes
through the Ralph Loop with configurable concurrency and error handling.
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ontoralph.core.loop import LoopConfig, LoopHooks, RalphLoop
from ontoralph.core.models import ClassInfo, LoopResult
from ontoralph.llm.base import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    max_concurrency: int = 3
    continue_on_error: bool = True
    respect_rate_limits: bool = True
    rate_limit_delay: float = 1.0  # seconds between API calls
    enable_resume: bool = False
    state_file: Path | None = None
    loop_config: LoopConfig = field(default_factory=LoopConfig)


@dataclass
class BatchProgress:
    """Progress tracking for batch processing."""

    total: int
    completed: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def remaining(self) -> int:
        """Number of classes remaining to process."""
        return self.total - self.completed - self.skipped

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)."""
        if self.completed == 0:
            return 0.0
        return self.passed / self.completed * 100


@dataclass
class BatchResult:
    """Result of batch processing."""

    results: list[LoopResult]
    progress: BatchProgress
    started_at: datetime
    completed_at: datetime
    errors: list[tuple[ClassInfo, Exception]] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Total processing duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def passed_results(self) -> list[LoopResult]:
        """Results that converged successfully."""
        return [r for r in self.results if r.converged]

    @property
    def failed_results(self) -> list[LoopResult]:
        """Results that failed to converge."""
        return [r for r in self.results if not r.converged]


class BatchState:
    """Persistent state for batch resume functionality."""

    def __init__(self, state_file: Path | None = None):
        self.state_file = state_file
        self._completed: set[str] = set()
        self._results: dict[str, dict[str, Any]] = {}

        if state_file and state_file.exists():
            self._load()

    def _class_key(self, class_info: ClassInfo) -> str:
        """Generate unique key for a class."""
        content = f"{class_info.iri}|{class_info.label}|{class_info.parent_class}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def is_completed(self, class_info: ClassInfo) -> bool:
        """Check if a class has already been processed."""
        return self._class_key(class_info) in self._completed

    def mark_completed(self, class_info: ClassInfo, result: LoopResult) -> None:
        """Mark a class as completed and save state."""
        key = self._class_key(class_info)
        self._completed.add(key)
        self._results[key] = {
            "iri": class_info.iri,
            "label": class_info.label,
            "status": result.status.value,
            "definition": result.final_definition,
            "iterations": result.total_iterations,
            "completed_at": datetime.now().isoformat(),
        }
        self._save()

    def _load(self) -> None:
        """Load state from file."""
        if not self.state_file or not self.state_file.exists():
            return

        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._completed = set(data.get("completed", []))
            self._results = data.get("results", {})
            logger.info(f"Loaded batch state: {len(self._completed)} classes completed")
        except Exception as e:
            logger.warning(f"Failed to load batch state: {e}")

    def _save(self) -> None:
        """Save state to file."""
        if not self.state_file:
            return

        try:
            data = {
                "completed": list(self._completed),
                "results": self._results,
                "updated_at": datetime.now().isoformat(),
            }
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save batch state: {e}")

    def clear(self) -> None:
        """Clear saved state."""
        self._completed.clear()
        self._results.clear()
        if self.state_file and self.state_file.exists():
            self.state_file.unlink()


class BatchProcessor:
    """Processes multiple classes through the Ralph Loop concurrently.

    Supports:
    - Configurable concurrency limits
    - Rate limit respect for API calls
    - Partial failure handling
    - Resume from interrupted batch
    - Progress callbacks
    """

    def __init__(
        self,
        llm: LLMProvider,
        config: BatchConfig | None = None,
    ) -> None:
        """Initialize the batch processor.

        Args:
            llm: LLM provider to use for all classes.
            config: Batch processing configuration.
        """
        self.llm = llm
        self.config = config or BatchConfig()
        self._state = BatchState(self.config.state_file) if self.config.enable_resume else None

        # Progress callbacks
        self._on_class_start: Callable[[ClassInfo], None] | None = None
        self._on_class_complete: Callable[[ClassInfo, LoopResult], None] | None = None
        self._on_class_error: Callable[[ClassInfo, Exception], None] | None = None
        self._on_progress: Callable[[BatchProgress], None] | None = None

    def set_callbacks(
        self,
        on_class_start: Callable[[ClassInfo], None] | None = None,
        on_class_complete: Callable[[ClassInfo, LoopResult], None] | None = None,
        on_class_error: Callable[[ClassInfo, Exception], None] | None = None,
        on_progress: Callable[[BatchProgress], None] | None = None,
    ) -> None:
        """Set progress callbacks.

        Args:
            on_class_start: Called when processing starts for a class.
            on_class_complete: Called when a class is successfully processed.
            on_class_error: Called when an error occurs processing a class.
            on_progress: Called after each class to report progress.
        """
        self._on_class_start = on_class_start
        self._on_class_complete = on_class_complete
        self._on_class_error = on_class_error
        self._on_progress = on_progress

    async def process(
        self,
        classes: list[ClassInfo],
        hooks: LoopHooks | None = None,
    ) -> BatchResult:
        """Process multiple classes through the Ralph Loop.

        Args:
            classes: List of classes to process.
            hooks: Optional hooks for individual loop iterations.

        Returns:
            Combined results from all classes.
        """
        started_at = datetime.now()
        results: list[LoopResult] = []
        errors: list[tuple[ClassInfo, Exception]] = []

        # Filter out already-completed classes if resuming
        to_process = classes
        skipped = 0
        if self._state:
            to_process = [c for c in classes if not self._state.is_completed(c)]
            skipped = len(classes) - len(to_process)
            if skipped > 0:
                logger.info(f"Resuming batch: skipping {skipped} completed classes")

        progress = BatchProgress(total=len(classes), skipped=skipped)

        if not to_process:
            logger.info("No classes to process (all completed)")
            return BatchResult(
                results=results,
                progress=progress,
                started_at=started_at,
                completed_at=datetime.now(),
                errors=errors,
            )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.max_concurrency)

        async def process_one(class_info: ClassInfo) -> LoopResult | None:
            async with semaphore:
                if self._on_class_start:
                    self._on_class_start(class_info)

                try:
                    # Rate limiting
                    if self.config.respect_rate_limits:
                        await asyncio.sleep(self.config.rate_limit_delay)

                    loop = RalphLoop(
                        llm=self.llm,
                        config=self.config.loop_config,
                        hooks=hooks,
                    )
                    result = await loop.run(class_info)

                    if self._state:
                        self._state.mark_completed(class_info, result)

                    if self._on_class_complete:
                        self._on_class_complete(class_info, result)

                    return result

                except Exception as e:
                    logger.error(f"Error processing {class_info.label}: {e}")
                    errors.append((class_info, e))

                    if self._on_class_error:
                        self._on_class_error(class_info, e)

                    if not self.config.continue_on_error:
                        raise

                    return None

        # Process all classes concurrently
        tasks = [process_one(c) for c in to_process]

        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                results.append(result)
                progress.completed += 1
                if result.converged:
                    progress.passed += 1
                else:
                    progress.failed += 1
            else:
                progress.errors += 1

            if self._on_progress:
                self._on_progress(progress)

        return BatchResult(
            results=results,
            progress=progress,
            started_at=started_at,
            completed_at=datetime.now(),
            errors=errors,
        )

    def clear_state(self) -> None:
        """Clear saved batch state."""
        if self._state:
            self._state.clear()


async def process_batch(
    classes: list[ClassInfo],
    llm: LLMProvider,
    config: BatchConfig | None = None,
    hooks: LoopHooks | None = None,
) -> BatchResult:
    """Convenience function to process a batch of classes.

    Args:
        classes: Classes to process.
        llm: LLM provider.
        config: Batch configuration.
        hooks: Loop hooks.

    Returns:
        Batch processing result.
    """
    processor = BatchProcessor(llm, config)
    return await processor.process(classes, hooks)
