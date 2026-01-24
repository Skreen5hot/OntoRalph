"""Settings and configuration models.

This module defines the configuration schema for OntoRalph.
Placeholder for Phase 8 implementation.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    CLAUDE = "claude"
    OPENAI = "openai"


class OutputFormat(str, Enum):
    """Supported output formats."""

    TURTLE = "turtle"
    MARKDOWN = "markdown"
    JSON = "json"


class StrictnessLevel(str, Enum):
    """Checklist strictness levels."""

    LENIENT = "lenient"  # Only core checks required
    STANDARD = "standard"  # Core + quality checks
    STRICT = "strict"  # All checks including style


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""

    provider: LLMProviderType = Field(
        default=LLMProviderType.CLAUDE,
        description="Which LLM provider to use",
    )
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model identifier",
    )
    max_tokens: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="Maximum tokens in response",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Sampling temperature",
    )

    model_config = {"extra": "forbid"}


class LoopConfig(BaseModel):
    """Configuration for the Ralph Loop."""

    max_iterations: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum iterations before giving up",
    )
    fail_fast: bool = Field(
        default=False,
        description="Stop on first red flag instead of completing critique",
    )
    strictness: StrictnessLevel = Field(
        default=StrictnessLevel.STANDARD,
        description="How strict to be with checks",
    )

    model_config = {"extra": "forbid"}


class OutputConfig(BaseModel):
    """Configuration for output generation."""

    format: OutputFormat = Field(
        default=OutputFormat.TURTLE,
        description="Primary output format",
    )
    include_comments: bool = Field(
        default=True,
        description="Include rdfs:comment in Turtle output",
    )
    include_examples: bool = Field(
        default=False,
        description="Include skos:example in Turtle output",
    )

    model_config = {"extra": "forbid"}


class Settings(BaseModel):
    """Root configuration for OntoRalph."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    model_config = {"extra": "forbid"}

    @classmethod
    def load_from_file(cls, path: str) -> "Settings":
        """Load settings from a YAML file.

        Args:
            path: Path to the configuration file.

        Returns:
            Loaded settings.

        Raises:
            NotImplementedError: This is a placeholder.
        """
        raise NotImplementedError(
            "Settings.load_from_file() will be implemented in Phase 8"
        )
