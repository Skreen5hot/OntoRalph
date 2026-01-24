"""LLM integration for OntoRalph.

This module provides a provider-agnostic interface for LLM interactions,
with implementations for Claude and OpenAI.
"""

from ontoralph.llm.base import (
    LLMAuthenticationError,
    LLMError,
    LLMProvider,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LoopPhase,
    SessionUsage,
    UsageStats,
)
from ontoralph.llm.claude import ClaudeProvider
from ontoralph.llm.mock import FailingMockProvider, MockProvider
from ontoralph.llm.openai import OpenAIProvider
from ontoralph.llm.parser import ResponseParser

__all__ = [
    # Base classes and types
    "LLMProvider",
    "LLMError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMResponseError",
    "LoopPhase",
    "UsageStats",
    "SessionUsage",
    # Providers
    "ClaudeProvider",
    "OpenAIProvider",
    "MockProvider",
    "FailingMockProvider",
    # Utilities
    "ResponseParser",
]
