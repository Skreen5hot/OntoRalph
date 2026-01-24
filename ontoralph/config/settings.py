"""Settings and configuration models.

This module defines the configuration schema for OntoRalph and
implements configuration loading with proper precedence.

Configuration Precedence (highest to lowest):
1. CLI flags
2. Environment variables (ONTORALPH_*)
3. Project config file (./ontoralph.yaml)
4. User config file (~/.ontoralph.yaml)
5. Defaults
"""

import os
import re
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    CLAUDE = "claude"
    OPENAI = "openai"
    MOCK = "mock"


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


class RuleSeverity(str, Enum):
    """Severity levels for custom rules."""

    ERROR = "error"  # Fails the check (like a red flag)
    WARNING = "warning"  # Noted but doesn't fail
    INFO = "info"  # Informational only


class CustomRule(BaseModel):
    """A custom checklist rule defined by the user."""

    name: str = Field(description="Human-readable name for the rule")
    pattern: str = Field(description="Regex pattern to match against definitions")
    message: str = Field(description="Message shown when rule triggers")
    severity: RuleSeverity = Field(
        default=RuleSeverity.WARNING,
        description="How severe a match is",
    )
    enabled: bool = Field(default=True, description="Whether this rule is active")

    model_config = {"extra": "forbid"}

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that pattern is a valid regex."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e
        return v

    def matches(self, text: str) -> re.Match[str] | None:
        """Check if this rule's pattern matches the text.

        Args:
            text: Text to check.

        Returns:
            Match object if found, None otherwise.
        """
        if not self.enabled:
            return None
        return re.search(self.pattern, text, re.IGNORECASE)


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""

    provider: LLMProviderType = Field(
        default=LLMProviderType.CLAUDE,
        description="Which LLM provider to use",
    )
    model: str | None = Field(
        default=None,
        description="Model identifier (uses provider default if not set)",
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
    api_key_env: str | None = Field(
        default=None,
        description="Environment variable name for API key (overrides default)",
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
    use_hybrid_checking: bool = Field(
        default=True,
        description="Use automated checks before LLM checks",
    )

    model_config = {"extra": "forbid"}


class ChecklistConfig(BaseModel):
    """Configuration for the definition checklist."""

    strictness: StrictnessLevel = Field(
        default=StrictnessLevel.STANDARD,
        description="How strict to be with checks",
    )
    custom_rules: list[CustomRule] = Field(
        default_factory=list,
        description="User-defined checklist rules",
    )
    disabled_checks: list[str] = Field(
        default_factory=list,
        description="Check codes to disable (e.g., ['Q1', 'Q2'])",
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
        description="Include header comments in output",
    )
    base_namespace: str = Field(
        default="http://example.org/ontology#",
        description="Base namespace for unprefixed IRIs",
    )

    model_config = {"extra": "forbid"}


class PromptConfig(BaseModel):
    """Configuration for prompt templates."""

    templates_dir: Path | None = Field(
        default=None,
        description="Directory containing custom prompt templates",
    )
    generate_template: str | None = Field(
        default=None,
        description="Custom template for GENERATE phase",
    )
    critique_template: str | None = Field(
        default=None,
        description="Custom template for CRITIQUE phase",
    )
    refine_template: str | None = Field(
        default=None,
        description="Custom template for REFINE phase",
    )

    model_config = {"extra": "forbid"}


class Settings(BaseModel):
    """Root configuration for OntoRalph."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    checklist: ChecklistConfig = Field(default_factory=ChecklistConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    prompts: PromptConfig = Field(default_factory=PromptConfig)

    model_config = {"extra": "forbid"}

    @classmethod
    def load_from_file(cls, path: str | Path) -> "Settings":
        """Load settings from a YAML file.

        Args:
            path: Path to the configuration file.

        Returns:
            Loaded settings.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If YAML is invalid or doesn't match schema.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}") from e

        if data is None:
            # Empty file, use defaults
            return cls()

        if not isinstance(data, dict):
            raise ValueError(
                "Configuration file must contain a YAML mapping (key: value pairs). "
                "Run 'ontoralph init' to generate a valid config template."
            )

        return cls.model_validate(data)

    def merge_with(self, overrides: dict[str, Any]) -> "Settings":
        """Create a new Settings with values from overrides.

        Args:
            overrides: Dictionary of override values.

        Returns:
            New Settings instance with merged values.
        """
        current = self.model_dump()
        _deep_merge(current, overrides)
        return Settings.model_validate(current)


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    """Recursively merge overrides into base dict in-place.

    Args:
        base: Base dictionary to merge into.
        overrides: Dictionary with override values.
    """
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        elif value is not None:  # Don't override with None
            base[key] = value


class ConfigLoader:
    """Loads configuration with proper precedence.

    Precedence (highest to lowest):
    1. CLI flags (passed as overrides)
    2. Environment variables (ONTORALPH_*)
    3. Project config file (./ontoralph.yaml)
    4. User config file (~/.ontoralph.yaml)
    5. Defaults
    """

    ENV_PREFIX = "ONTORALPH_"
    PROJECT_CONFIG_NAME = "ontoralph.yaml"
    USER_CONFIG_NAME = ".ontoralph.yaml"

    # Mapping of environment variables to config paths
    ENV_MAPPINGS = {
        "ONTORALPH_PROVIDER": ("llm", "provider"),
        "ONTORALPH_MODEL": ("llm", "model"),
        "ONTORALPH_MAX_ITERATIONS": ("loop", "max_iterations"),
        "ONTORALPH_OUTPUT_FORMAT": ("output", "format"),
        "ONTORALPH_STRICTNESS": ("checklist", "strictness"),
    }

    def __init__(
        self,
        project_dir: Path | None = None,
        user_dir: Path | None = None,
    ) -> None:
        """Initialize the config loader.

        Args:
            project_dir: Directory to look for project config (default: cwd).
            user_dir: User's home directory (default: ~).
        """
        self.project_dir = project_dir or Path.cwd()
        self.user_dir = user_dir or Path.home()

    def load(self, cli_overrides: dict[str, Any] | None = None) -> Settings:
        """Load settings with full precedence chain.

        Args:
            cli_overrides: Overrides from CLI flags.

        Returns:
            Merged settings.
        """
        # Start with defaults
        settings = Settings()

        # Load user config if exists
        user_config_path = self.user_dir / self.USER_CONFIG_NAME
        if user_config_path.exists():
            try:
                user_settings = Settings.load_from_file(user_config_path)
                settings = user_settings
            except (ValueError, FileNotFoundError):
                pass  # Ignore invalid user config

        # Load project config if exists
        project_config_path = self.project_dir / self.PROJECT_CONFIG_NAME
        if project_config_path.exists():
            try:
                project_data = self._load_yaml(project_config_path)
                settings = settings.merge_with(project_data)
            except (ValueError, FileNotFoundError):
                pass  # Ignore invalid project config

        # Apply environment variables
        env_overrides = self._get_env_overrides()
        if env_overrides:
            settings = settings.merge_with(env_overrides)

        # Apply CLI overrides (highest priority)
        if cli_overrides:
            settings = settings.merge_with(cli_overrides)

        return settings

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load YAML file as dict.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed dictionary.
        """
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}

    def _get_env_overrides(self) -> dict[str, Any]:
        """Get configuration overrides from environment variables.

        Returns:
            Nested dictionary of overrides.
        """
        overrides: dict[str, Any] = {}

        for env_var, path in self.ENV_MAPPINGS.items():
            value = os.environ.get(env_var)
            if value is not None:
                self._set_nested(overrides, path, self._convert_value(value))

        return overrides

    def _set_nested(self, d: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
        """Set a nested dictionary value.

        Args:
            d: Dictionary to modify.
            path: Tuple of keys.
            value: Value to set.
        """
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type.

        Args:
            value: String value from environment.

        Returns:
            Converted value.
        """
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Try boolean
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Return as string
        return value


def load_settings(
    config_file: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> Settings:
    """Convenience function to load settings.

    Args:
        config_file: Explicit config file path (optional).
        cli_overrides: Overrides from CLI.

    Returns:
        Loaded settings.
    """
    if config_file:
        # Load specific file, then apply CLI overrides
        settings = Settings.load_from_file(config_file)
        if cli_overrides:
            settings = settings.merge_with(cli_overrides)
        return settings
    else:
        # Use full precedence chain
        loader = ConfigLoader()
        return loader.load(cli_overrides)


# Default settings instance
DEFAULT_SETTINGS = Settings()
