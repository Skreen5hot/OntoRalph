"""Ralph Loop controller.

This module contains the main loop orchestration logic for the
Generate -> Critique -> Refine -> Verify cycle.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

from ontoralph.core.checklist import ChecklistEvaluator
from ontoralph.core.models import (
    CheckResult,
    ClassInfo,
    LoopIteration,
    LoopResult,
    LoopState,
    Severity,
    VerifyStatus,
)
from ontoralph.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class LoopHookProtocol(Protocol):
    """Protocol for loop event hooks."""

    def on_loop_start(self, state: LoopState) -> None:
        """Called when the loop starts."""
        ...

    def on_iteration_start(self, iteration: int, state: LoopState) -> None:
        """Called at the start of each iteration."""
        ...

    def on_generate(self, definition: str) -> None:
        """Called after definition generation."""
        ...

    def on_critique(self, results: list[CheckResult]) -> None:
        """Called after critique phase."""
        ...

    def on_refine(self, definition: str) -> None:
        """Called after refinement."""
        ...

    def on_verify(self, status: VerifyStatus, results: list[CheckResult]) -> None:
        """Called after verification."""
        ...

    def on_iteration_end(self, iteration: LoopIteration) -> None:
        """Called at the end of each iteration."""
        ...

    def on_loop_end(self, result: LoopResult) -> None:
        """Called when the loop completes."""
        ...


@dataclass
class LoopHooks:
    """Container for loop event callbacks.

    All callbacks are optional. Unset callbacks are no-ops.
    """

    on_loop_start: Callable[[LoopState], None] | None = None
    on_iteration_start: Callable[[int, LoopState], None] | None = None
    on_generate: Callable[[str], None] | None = None
    on_critique: Callable[[list[CheckResult]], None] | None = None
    on_refine: Callable[[str], None] | None = None
    on_verify: Callable[[VerifyStatus, list[CheckResult]], None] | None = None
    on_iteration_end: Callable[[LoopIteration], None] | None = None
    on_loop_end: Callable[[LoopResult], None] | None = None


@dataclass
class LoopConfig:
    """Configuration for the Ralph Loop."""

    max_iterations: int = 5
    use_hybrid_checking: bool = True
    fail_fast_on_red_flags: bool = True
    log_iterations: bool = True


@dataclass
class HybridCheckResult:
    """Result of hybrid checking combining automated and LLM checks."""

    automated_results: list[CheckResult] = field(default_factory=list)
    llm_results: list[CheckResult] = field(default_factory=list)
    combined_results: list[CheckResult] = field(default_factory=list)
    skipped_llm: bool = False
    skip_reason: str | None = None

    @property
    def all_passed(self) -> bool:
        """Check if all combined results passed."""
        return all(r.passed for r in self.combined_results)

    @property
    def has_red_flags(self) -> bool:
        """Check if any red flags are present."""
        return any(
            not r.passed and r.severity == Severity.RED_FLAG
            for r in self.combined_results
        )

    @property
    def failed_checks(self) -> list[CheckResult]:
        """Get all failed checks."""
        return [r for r in self.combined_results if not r.passed]


class RalphLoop:
    """Orchestrates the Generate -> Critique -> Refine -> Verify loop.

    The loop continues until either:
    1. All required checks pass (PASS status)
    2. Maximum iterations are reached (FAIL status)
    3. No improvement is detected after multiple iterations

    Supports hybrid checking where automated checks (red flags, circularity)
    run before LLM-based semantic checks, potentially saving API calls.
    """

    def __init__(
        self,
        llm: LLMProvider,
        config: LoopConfig | None = None,
        hooks: LoopHooks | None = None,
    ) -> None:
        """Initialize the Ralph Loop.

        Args:
            llm: The LLM provider to use for generation and refinement.
            config: Loop configuration options.
            hooks: Event callbacks for monitoring loop progress.
        """
        self.llm = llm
        self.config = config or LoopConfig()
        self.hooks = hooks or LoopHooks()
        self._evaluator = ChecklistEvaluator()

    async def run(self, class_info: ClassInfo) -> LoopResult:
        """Execute the full loop until PASS or max iterations.

        Args:
            class_info: Information about the class to refine.

        Returns:
            The final result of the loop.
        """
        # Initialize state
        state = LoopState(
            class_info=class_info,
            max_iterations=self.config.max_iterations,
        )

        logger.info(
            f"Starting Ralph Loop for {class_info.label} ({class_info.iri}), "
            f"max_iterations={self.config.max_iterations}"
        )
        self._call_hook("on_loop_start", state)

        # Run iterations until complete
        while not state.is_complete:
            state = await self.step(state)

        # Build final result
        final_iteration = state.iterations[-1] if state.iterations else None
        result = LoopResult(
            class_info=class_info,
            final_definition=state.latest_definition or "",
            status=final_iteration.verify_status if final_iteration else VerifyStatus.FAIL,
            iterations=state.iterations,
            total_iterations=len(state.iterations),
            started_at=state.started_at,
        )

        logger.info(
            f"Ralph Loop completed for {class_info.label}: "
            f"status={result.status.value}, iterations={result.total_iterations}"
        )
        self._call_hook("on_loop_end", result)

        return result

    async def step(self, state: LoopState) -> LoopState:
        """Execute one iteration of the loop.

        Each iteration consists of:
        1. GENERATE: Create or refine a definition
        2. CRITIQUE: Evaluate against checklist (hybrid: automated + LLM)
        3. REFINE: If issues found, attempt to fix them
        4. VERIFY: Determine if definition passes

        Args:
            state: Current loop state.

        Returns:
            Updated loop state after one iteration.
        """
        iteration_num = state.current_iteration + 1
        logger.info(f"Starting iteration {iteration_num}/{state.max_iterations}")
        self._call_hook("on_iteration_start", iteration_num, state)

        # GENERATE phase
        if state.latest_definition:
            # We have a previous definition, use it as starting point
            generated_definition = state.latest_definition
        else:
            # First iteration: generate from scratch
            generated_definition = await self._generate(state.class_info)

        self._call_hook("on_generate", generated_definition)
        logger.debug(f"Generated definition: {generated_definition}")

        # CRITIQUE phase (hybrid checking)
        hybrid_result = await self._critique_hybrid(
            state.class_info, generated_definition
        )
        critique_results = hybrid_result.combined_results

        self._call_hook("on_critique", critique_results)
        logger.debug(f"Critique: {len(hybrid_result.failed_checks)} issues found")

        # Determine initial status
        status = self._evaluator.determine_status(
            critique_results, state.class_info.is_ice
        )

        # REFINE phase (if needed)
        refined_definition: str | None = None
        if status != VerifyStatus.PASS and hybrid_result.failed_checks:
            refined_definition = await self._refine(
                state.class_info,
                generated_definition,
                hybrid_result.failed_checks,
            )
            self._call_hook("on_refine", refined_definition)
            logger.debug(f"Refined definition: {refined_definition}")

            # Re-evaluate after refinement
            if refined_definition != generated_definition:
                re_check = await self._critique_hybrid(
                    state.class_info, refined_definition
                )
                critique_results = re_check.combined_results
                status = self._evaluator.determine_status(
                    critique_results, state.class_info.is_ice
                )

        # VERIFY phase
        self._call_hook("on_verify", status, critique_results)
        logger.info(f"Iteration {iteration_num} result: {status.value}")

        # Create iteration record
        iteration = LoopIteration(
            iteration_number=iteration_num,
            generated_definition=generated_definition,
            critique_results=critique_results,
            refined_definition=refined_definition,
            verify_status=status,
        )

        self._call_hook("on_iteration_end", iteration)

        # Update state with new iteration
        new_iterations = list(state.iterations)
        new_iterations.append(iteration)

        return LoopState(
            class_info=state.class_info,
            iterations=new_iterations,
            max_iterations=state.max_iterations,
            started_at=state.started_at,
        )

    async def _generate(self, class_info: ClassInfo) -> str:
        """Generate a definition using the LLM.

        Args:
            class_info: Information about the class.

        Returns:
            Generated definition string.
        """
        logger.debug(f"Generating definition for {class_info.label}")
        return await self.llm.generate(class_info)

    async def _critique_hybrid(
        self, class_info: ClassInfo, definition: str
    ) -> HybridCheckResult:
        """Perform hybrid critique: automated checks first, then LLM if needed.

        This approach can save API calls by catching red flags and other
        issues with automated checks before invoking the LLM.

        Args:
            class_info: Information about the class.
            definition: The definition to critique.

        Returns:
            Combined results from automated and LLM checks.
        """
        result = HybridCheckResult()

        # Step 1: Run automated checks
        automated = self._evaluator.evaluate(
            definition=definition,
            term=class_info.label,
            is_ice=class_info.is_ice,
            parent_class=class_info.parent_class,
        )
        result.automated_results = automated

        # Check for red flags (auto-fail)
        red_flags = [
            r for r in automated
            if not r.passed and r.severity == Severity.RED_FLAG
        ]

        if red_flags and self.config.fail_fast_on_red_flags:
            # Skip LLM check if we already found red flags
            result.combined_results = automated
            result.skipped_llm = True
            result.skip_reason = f"Red flags detected: {[r.code for r in red_flags]}"
            logger.debug(f"Skipped LLM critique: {result.skip_reason}")
            return result

        # Check for core failures
        core_failures = [
            r for r in automated
            if not r.passed and r.severity == Severity.REQUIRED
        ]

        if core_failures and self.config.use_hybrid_checking:
            # We have core failures from automated checks
            # Still use automated results but could enhance with LLM later
            result.combined_results = automated
            result.skipped_llm = True
            result.skip_reason = f"Core failures detected: {[r.code for r in core_failures]}"
            logger.debug(f"Skipped LLM critique: {result.skip_reason}")
            return result

        # Step 2: Run LLM critique for semantic checks
        if not self.config.use_hybrid_checking:
            # If hybrid checking is disabled, use LLM for everything
            try:
                llm_results = await self.llm.critique(class_info, definition)
                result.llm_results = llm_results
                result.combined_results = self._merge_results(automated, llm_results)
            except Exception as e:
                logger.warning(f"LLM critique failed, using automated only: {e}")
                result.combined_results = automated
                result.skipped_llm = True
                result.skip_reason = f"LLM error: {e}"
        else:
            # Hybrid mode: automated checks are sufficient for now
            result.combined_results = automated
            result.skipped_llm = True
            result.skip_reason = "Automated checks sufficient"

        return result

    async def _refine(
        self,
        class_info: ClassInfo,
        definition: str,
        issues: list[CheckResult],
    ) -> str:
        """Refine a definition to address identified issues.

        Args:
            class_info: Information about the class.
            definition: Current definition.
            issues: List of failed checks.

        Returns:
            Refined definition string.
        """
        logger.debug(f"Refining definition to address {len(issues)} issues")
        return await self.llm.refine(class_info, definition, issues)

    def _merge_results(
        self,
        automated: list[CheckResult],
        llm: list[CheckResult],
    ) -> list[CheckResult]:
        """Merge automated and LLM check results.

        Automated results take precedence for checks they cover.

        Args:
            automated: Results from automated checking.
            llm: Results from LLM checking.

        Returns:
            Merged list of check results.
        """
        # Build a map of automated results by code
        automated_map = {r.code: r for r in automated}

        # Start with automated results
        merged = list(automated)

        # Add LLM results for checks not covered by automated
        for llm_result in llm:
            if llm_result.code not in automated_map:
                merged.append(llm_result)

        return merged

    def _call_hook(self, hook_name: str, *args) -> None:
        """Safely call a hook if it's defined.

        Args:
            hook_name: Name of the hook to call.
            *args: Arguments to pass to the hook.
        """
        hook = getattr(self.hooks, hook_name, None)
        if hook is not None:
            try:
                hook(*args)
            except Exception as e:
                logger.warning(f"Hook {hook_name} raised exception: {e}")


class LoggingHooks(LoopHooks):
    """Pre-configured hooks that log all events."""

    def __init__(self, log_level: int = logging.INFO) -> None:
        """Initialize logging hooks.

        Args:
            log_level: Logging level to use.
        """
        self._logger = logging.getLogger(f"{__name__}.hooks")
        self._level = log_level

        super().__init__(
            on_loop_start=self._on_loop_start,
            on_iteration_start=self._on_iteration_start,
            on_generate=self._on_generate,
            on_critique=self._on_critique,
            on_refine=self._on_refine,
            on_verify=self._on_verify,
            on_iteration_end=self._on_iteration_end,
            on_loop_end=self._on_loop_end,
        )

    def _on_loop_start(self, state: LoopState) -> None:
        self._logger.log(
            self._level,
            f"Loop started for {state.class_info.label}",
        )

    def _on_iteration_start(self, iteration: int, state: LoopState) -> None:
        self._logger.log(
            self._level,
            f"Iteration {iteration} started",
        )

    def _on_generate(self, definition: str) -> None:
        self._logger.log(
            self._level,
            f"Generated: {definition[:100]}..." if len(definition) > 100 else f"Generated: {definition}",
        )

    def _on_critique(self, results: list[CheckResult]) -> None:
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        self._logger.log(
            self._level,
            f"Critique: {passed} passed, {failed} failed",
        )

    def _on_refine(self, definition: str) -> None:
        self._logger.log(
            self._level,
            f"Refined: {definition[:100]}..." if len(definition) > 100 else f"Refined: {definition}",
        )

    def _on_verify(self, status: VerifyStatus, results: list[CheckResult]) -> None:
        self._logger.log(
            self._level,
            f"Verify: {status.value}",
        )

    def _on_iteration_end(self, iteration: LoopIteration) -> None:
        self._logger.log(
            self._level,
            f"Iteration {iteration.iteration_number} ended: {iteration.verify_status.value}",
        )

    def _on_loop_end(self, result: LoopResult) -> None:
        self._logger.log(
            self._level,
            f"Loop ended: {result.status.value} after {result.total_iterations} iterations",
        )


class CountingHooks(LoopHooks):
    """Hooks that count events for testing."""

    def __init__(self) -> None:
        """Initialize counting hooks."""
        self.loop_start_count = 0
        self.iteration_start_count = 0
        self.generate_count = 0
        self.critique_count = 0
        self.refine_count = 0
        self.verify_count = 0
        self.iteration_end_count = 0
        self.loop_end_count = 0

        super().__init__(
            on_loop_start=lambda _: self._inc("loop_start_count"),
            on_iteration_start=lambda *_: self._inc("iteration_start_count"),
            on_generate=lambda _: self._inc("generate_count"),
            on_critique=lambda _: self._inc("critique_count"),
            on_refine=lambda _: self._inc("refine_count"),
            on_verify=lambda *_: self._inc("verify_count"),
            on_iteration_end=lambda _: self._inc("iteration_end_count"),
            on_loop_end=lambda _: self._inc("loop_end_count"),
        )

    def _inc(self, attr: str) -> None:
        setattr(self, attr, getattr(self, attr) + 1)

    def reset(self) -> None:
        """Reset all counters."""
        self.loop_start_count = 0
        self.iteration_start_count = 0
        self.generate_count = 0
        self.critique_count = 0
        self.refine_count = 0
        self.verify_count = 0
        self.iteration_end_count = 0
        self.loop_end_count = 0
