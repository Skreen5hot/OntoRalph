"""Base LLM provider interface.

This module defines the abstract base class for LLM providers,
along with usage tracking and error handling utilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ontoralph.core.models import CheckResult, ClassInfo


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMAuthenticationError(LLMError):
    """Raised when API authentication fails."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Raised when API request times out."""

    pass


class LLMResponseError(LLMError):
    """Raised when API response cannot be parsed."""

    pass


class LoopPhase(str, Enum):
    """Phases of the Ralph Loop that use LLM."""

    GENERATE = "generate"
    CRITIQUE = "critique"
    REFINE = "refine"


@dataclass
class UsageStats:
    """Token usage statistics for a single LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    phase: LoopPhase | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    latency_ms: float = 0.0

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost based on model and tokens.

        Note: These are approximate costs and may change.
        """
        # Approximate costs per 1M tokens (as of 2024)
        cost_per_1m = {
            # Claude models
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            # OpenAI models
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        }

        rates = cost_per_1m.get(self.model, {"input": 5.0, "output": 15.0})
        input_cost = (self.input_tokens / 1_000_000) * rates["input"]
        output_cost = (self.output_tokens / 1_000_000) * rates["output"]
        return input_cost + output_cost


@dataclass
class SessionUsage:
    """Aggregated usage statistics for a session."""

    calls: list[UsageStats] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.estimated_cost_usd for c in self.calls)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def by_phase(self, phase: LoopPhase) -> list[UsageStats]:
        """Get usage stats for a specific phase."""
        return [c for c in self.calls if c.phase == phase]

    def summary(self) -> dict[str, Any]:
        """Get a summary of usage statistics."""
        return {
            "total_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.total_cost_usd, 6),
            "by_phase": {
                phase.value: len(self.by_phase(phase)) for phase in LoopPhase
            },
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM integrations (Claude, OpenAI, etc.) must implement this interface.
    Provides common functionality for usage tracking and error handling.
    """

    def __init__(self) -> None:
        """Initialize the provider with usage tracking."""
        self._usage = SessionUsage()

    @property
    def usage(self) -> SessionUsage:
        """Get the session usage statistics."""
        return self._usage

    def reset_usage(self) -> None:
        """Reset usage statistics."""
        self._usage = SessionUsage()

    def _record_usage(self, stats: UsageStats) -> None:
        """Record usage statistics from an API call."""
        self._usage.calls.append(stats)

    @abstractmethod
    async def generate(self, class_info: ClassInfo) -> str:
        """Generate an initial definition for a class.

        Args:
            class_info: Information about the class to define.

        Returns:
            A generated definition string.

        Raises:
            LLMAuthenticationError: If API authentication fails.
            LLMRateLimitError: If rate limit is exceeded.
            LLMTimeoutError: If request times out.
            LLMResponseError: If response cannot be parsed.
        """
        ...

    @abstractmethod
    async def critique(
        self, class_info: ClassInfo, definition: str
    ) -> list[CheckResult]:
        """Critique a definition using the checklist.

        Args:
            class_info: Information about the class.
            definition: The definition to critique.

        Returns:
            List of check results from the critique.

        Raises:
            LLMAuthenticationError: If API authentication fails.
            LLMRateLimitError: If rate limit is exceeded.
            LLMTimeoutError: If request times out.
            LLMResponseError: If response cannot be parsed.
        """
        ...

    @abstractmethod
    async def refine(
        self, class_info: ClassInfo, definition: str, issues: list[CheckResult]
    ) -> str:
        """Refine a definition based on identified issues.

        Args:
            class_info: Information about the class.
            definition: The current definition.
            issues: List of failed checks to address.

        Returns:
            A refined definition string.

        Raises:
            LLMAuthenticationError: If API authentication fails.
            LLMRateLimitError: If rate limit is exceeded.
            LLMTimeoutError: If request times out.
            LLMResponseError: If response cannot be parsed.
        """
        ...
