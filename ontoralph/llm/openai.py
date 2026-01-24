"""OpenAI LLM provider.

This module implements the LLM provider interface for OpenAI's models.
"""

import asyncio
import os
import time
from typing import Any

from ontoralph.core.models import CheckResult, ClassInfo
from ontoralph.llm.base import (
    LLMAuthenticationError,
    LLMProvider,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LoopPhase,
    UsageStats,
)
from ontoralph.llm.parser import ResponseParser
from ontoralph.llm.prompts import (
    SYSTEM_PROMPT,
    format_critique_prompt,
    format_generate_prompt,
    format_refine_prompt,
)

try:
    import openai
    from openai import APIConnectionError, APIStatusError, APITimeoutError

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None  # type: ignore
    APIConnectionError = Exception  # type: ignore
    APIStatusError = Exception  # type: ignore
    APITimeoutError = Exception  # type: ignore


class OpenAIProvider(LLMProvider):
    """LLM provider implementation for OpenAI.

    Supports GPT-4 and other OpenAI models with:
    - Automatic retry with exponential backoff
    - Token usage tracking
    - Graceful error handling
    """

    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_TIMEOUT = 60.0
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: Model identifier to use.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0-1.0).
            timeout: Request timeout in seconds.

        Raises:
            ImportError: If openai package is not installed.
            LLMAuthenticationError: If no API key is provided or found.
        """
        super().__init__()

        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required for OpenAIProvider. "
                "Install it with: pip install openai"
            )

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError(
                "No API key provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        self.temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        self.timeout = timeout or self.DEFAULT_TIMEOUT

        self._client = openai.AsyncOpenAI(
            api_key=self.api_key,
            timeout=self.timeout,
        )
        self._parser = ResponseParser()

    async def generate(self, class_info: ClassInfo) -> str:
        """Generate an initial definition for a class.

        Args:
            class_info: Information about the class to define.

        Returns:
            A generated definition string.
        """
        prompt = format_generate_prompt(class_info)
        response = await self._call_api(prompt, LoopPhase.GENERATE)
        return self._parser.parse_definition(response)

    async def critique(
        self, class_info: ClassInfo, definition: str
    ) -> list[CheckResult]:
        """Critique a definition using the checklist.

        Args:
            class_info: Information about the class.
            definition: The definition to critique.

        Returns:
            List of check results from the critique.
        """
        prompt = format_critique_prompt(class_info, definition)
        response = await self._call_api(prompt, LoopPhase.CRITIQUE)
        return self._parser.parse_critique(response)

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
        """
        prompt = format_refine_prompt(class_info, definition, issues)
        response = await self._call_api(prompt, LoopPhase.REFINE)
        return self._parser.parse_definition(response)

    async def _call_api(self, prompt: str, phase: LoopPhase) -> str:
        """Make an API call with retry logic.

        Args:
            prompt: The user prompt to send.
            phase: The current loop phase (for usage tracking).

        Returns:
            The response text.

        Raises:
            LLMAuthenticationError: If authentication fails.
            LLMRateLimitError: If rate limit is exceeded.
            LLMTimeoutError: If request times out.
            LLMResponseError: If response is invalid.
        """
        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()

                response = await self._client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )

                latency_ms = (time.time() - start_time) * 1000

                # Record usage
                if response.usage:
                    self._record_usage(
                        UsageStats(
                            input_tokens=response.usage.prompt_tokens,
                            output_tokens=response.usage.completion_tokens,
                            total_tokens=response.usage.total_tokens,
                            model=self.model,
                            phase=phase,
                            latency_ms=latency_ms,
                        )
                    )

                # Extract text from response
                if not response.choices:
                    raise LLMResponseError("No choices in response")

                message = response.choices[0].message
                if not message.content:
                    raise LLMResponseError("Empty message content")

                return message.content

            except APITimeoutError as e:
                last_error = LLMTimeoutError(f"Request timed out after {self.timeout}s: {e}")
                # Don't retry timeouts
                raise last_error

            except APIStatusError as e:
                if e.status_code == 401:
                    raise LLMAuthenticationError(f"Authentication failed: {e.message}")
                elif e.status_code == 429:
                    retry_after = self._get_retry_after(e)
                    last_error = LLMRateLimitError(
                        f"Rate limit exceeded: {e.message}",
                        retry_after=retry_after,
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(retry_after or self._get_backoff_delay(attempt))
                        continue
                    raise last_error
                elif e.status_code >= 500:
                    # Server errors are retryable
                    last_error = LLMResponseError(f"Server error: {e.message}")
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self._get_backoff_delay(attempt))
                        continue
                    raise last_error
                else:
                    raise LLMResponseError(f"API error ({e.status_code}): {e.message}")

            except APIConnectionError as e:
                last_error = LLMResponseError(f"Connection error: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self._get_backoff_delay(attempt))
                    continue
                raise last_error

            except Exception as e:
                if isinstance(e, (LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError, LLMResponseError)):
                    raise
                raise LLMResponseError(f"Unexpected error: {e}")

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise LLMResponseError("Unknown error occurred")

    def _get_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        return self.BASE_RETRY_DELAY * (2**attempt)

    def _get_retry_after(self, error: Any) -> float | None:
        """Extract retry-after header from error if present.

        Args:
            error: The API error.

        Returns:
            Retry delay in seconds, or None if not specified.
        """
        try:
            if hasattr(error, "response") and error.response:
                retry_after = error.response.headers.get("retry-after")
                if retry_after:
                    return float(retry_after)
        except (ValueError, AttributeError):
            pass
        return None
