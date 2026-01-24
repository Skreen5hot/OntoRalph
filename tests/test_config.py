"""Tests for the configuration module.

This module tests:
- Configuration file loading
- Config precedence (CLI > env > project > user > defaults)
- Custom checklist rules
- Custom prompt templates
- Validation and error handling
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from ontoralph.config import (
    ConfigLoader,
    CustomRule,
    LLMProviderType,
    OutputFormat,
    PromptConfig,
    RuleSeverity,
    Settings,
    StrictnessLevel,
    load_settings,
)
from ontoralph.core.checklist import ChecklistEvaluator, CustomRuleEvaluator
from ontoralph.core.models import ClassInfo
from ontoralph.llm.prompts import PromptTemplateManager


class TestSettings:
    """Tests for Settings model."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = Settings()

        assert settings.llm.provider == LLMProviderType.CLAUDE
        assert settings.loop.max_iterations == 5
        assert settings.output.format == OutputFormat.TURTLE
        assert settings.checklist.strictness == StrictnessLevel.STANDARD
        assert len(settings.checklist.custom_rules) == 0

    def test_settings_from_dict(self) -> None:
        """Test creating settings from dictionary."""
        data = {
            "llm": {"provider": "openai", "model": "gpt-4"},
            "loop": {"max_iterations": 3},
            "output": {"format": "markdown"},
        }

        settings = Settings.model_validate(data)

        assert settings.llm.provider == LLMProviderType.OPENAI
        assert settings.llm.model == "gpt-4"
        assert settings.loop.max_iterations == 3
        assert settings.output.format == OutputFormat.MARKDOWN

    def test_settings_merge(self) -> None:
        """Test merging settings with overrides."""
        base = Settings()
        overrides = {"loop": {"max_iterations": 7}}

        merged = base.merge_with(overrides)

        assert merged.loop.max_iterations == 7
        # Other values should remain default
        assert merged.llm.provider == LLMProviderType.CLAUDE


class TestConfigFileLoading:
    """Tests for configuration file loading (AC8.1)."""

    def test_load_valid_yaml(self) -> None:
        """Test loading a valid YAML config file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(
                {
                    "llm": {"provider": "claude", "model": "claude-3-opus"},
                    "loop": {"max_iterations": 10},
                },
                f,
            )
            config_path = f.name

        try:
            settings = Settings.load_from_file(config_path)
            assert settings.llm.model == "claude-3-opus"
            assert settings.loop.max_iterations == 10
        finally:
            os.unlink(config_path)

    def test_load_empty_file(self) -> None:
        """Test loading an empty config file uses defaults."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            config_path = f.name

        try:
            settings = Settings.load_from_file(config_path)
            assert settings.loop.max_iterations == 5  # Default
        finally:
            os.unlink(config_path)

    def test_load_nonexistent_file(self) -> None:
        """Test loading nonexistent file raises error (AC8.5)."""
        with pytest.raises(FileNotFoundError):
            Settings.load_from_file("/nonexistent/path/config.yaml")

    def test_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises error (AC8.5)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("not: valid: yaml: {{")
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                Settings.load_from_file(config_path)
        finally:
            os.unlink(config_path)

    def test_load_invalid_schema(self) -> None:
        """Test loading YAML with invalid schema raises error (AC8.5)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(
                {"llm": {"provider": "invalid_provider"}},
                f,
            )
            config_path = f.name

        try:
            with pytest.raises(ValueError):  # Pydantic validation error
                Settings.load_from_file(config_path)
        finally:
            os.unlink(config_path)


class TestConfigPrecedence:
    """Tests for configuration precedence (AC8.2)."""

    def test_cli_overrides_config_file(self) -> None:
        """Test CLI flags override config file values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project config with max_iterations=3
            config_path = Path(tmpdir) / "ontoralph.yaml"
            config_path.write_text(
                yaml.dump({"loop": {"max_iterations": 3}}), encoding="utf-8"
            )

            loader = ConfigLoader(project_dir=Path(tmpdir))

            # Load with CLI override max_iterations=7
            settings = loader.load(cli_overrides={"loop": {"max_iterations": 7}})

            # CLI should win
            assert settings.loop.max_iterations == 7

    def test_env_overrides_config(self) -> None:
        """Test environment variables override config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create project config
            config_path = Path(tmpdir) / "ontoralph.yaml"
            config_path.write_text(
                yaml.dump({"loop": {"max_iterations": 3}}), encoding="utf-8"
            )

            # Set environment variable
            os.environ["ONTORALPH_MAX_ITERATIONS"] = "8"

            try:
                loader = ConfigLoader(project_dir=Path(tmpdir))
                settings = loader.load()

                # Environment should win over file
                assert settings.loop.max_iterations == 8
            finally:
                del os.environ["ONTORALPH_MAX_ITERATIONS"]

    def test_project_config_overrides_user_config(self) -> None:
        """Test project config overrides user config."""
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as user_dir:
            # Create user config
            user_config = Path(user_dir) / ".ontoralph.yaml"
            user_config.write_text(
                yaml.dump({"loop": {"max_iterations": 2}}), encoding="utf-8"
            )

            # Create project config
            project_config = Path(project_dir) / "ontoralph.yaml"
            project_config.write_text(
                yaml.dump({"loop": {"max_iterations": 4}}), encoding="utf-8"
            )

            loader = ConfigLoader(project_dir=Path(project_dir), user_dir=Path(user_dir))
            settings = loader.load()

            # Project should win over user
            assert settings.loop.max_iterations == 4

    def test_defaults_used_when_no_config(self) -> None:
        """Test defaults used when no config files exist."""
        with tempfile.TemporaryDirectory() as empty_dir:
            loader = ConfigLoader(
                project_dir=Path(empty_dir),
                user_dir=Path(empty_dir),
            )
            settings = loader.load()

            # Should use defaults
            assert settings.loop.max_iterations == 5


class TestCustomRules:
    """Tests for custom checklist rules (AC8.3)."""

    def test_custom_rule_creation(self) -> None:
        """Test creating a custom rule."""
        rule = CustomRule(
            name="No jargon",
            pattern=r"\b(NLP|ML|AI)\b",
            message="Avoid technical jargon",
            severity=RuleSeverity.WARNING,
        )

        assert rule.name == "No jargon"
        assert rule.enabled is True

    def test_custom_rule_matches(self) -> None:
        """Test custom rule pattern matching (AC8.3)."""
        rule = CustomRule(
            name="No jargon",
            pattern=r"\b(NLP|ML|AI)\b",
            message="Avoid technical jargon",
        )

        # Should match
        assert rule.matches("An ICE that uses NLP techniques") is not None
        assert rule.matches("An AI-powered entity") is not None

        # Should not match
        assert rule.matches("An ICE that denotes an occurrent") is None

    def test_invalid_regex_rejected(self) -> None:
        """Test invalid regex patterns are rejected."""
        with pytest.raises(ValueError, match="Invalid regex"):
            CustomRule(
                name="Bad rule",
                pattern=r"[invalid",  # Unclosed bracket
                message="This should fail",
            )

    def test_disabled_rule_not_matched(self) -> None:
        """Test disabled rules don't match."""
        rule = CustomRule(
            name="Disabled rule",
            pattern=r"\btest\b",
            message="Should not match",
            enabled=False,
        )

        assert rule.matches("This is a test") is None

    def test_custom_rule_evaluator(self) -> None:
        """Test custom rule evaluator integration."""
        rules = [
            CustomRule(
                name="No jargon",
                pattern=r"\b(NLP|ML|AI)\b",
                message="Avoid technical jargon",
                severity=RuleSeverity.ERROR,
            ),
            CustomRule(
                name="No latin",
                pattern=r"\b(e\.g\.|i\.e\.)\b",
                message="Avoid Latin abbreviations",
                severity=RuleSeverity.WARNING,
            ),
        ]

        evaluator = CustomRuleEvaluator(rules)

        # Definition with jargon
        results = evaluator.evaluate("An ICE that uses NLP for processing")
        assert len(results) == 2  # Both rules evaluated

        # First rule should fail
        x1 = next(r for r in results if r.code == "X1")
        assert not x1.passed
        assert "NLP" in x1.evidence

        # Second rule should pass
        x2 = next(r for r in results if r.code == "X2")
        assert x2.passed

    def test_custom_rules_in_checklist_evaluator(self) -> None:
        """Test custom rules integrated with checklist evaluator."""
        rules = [
            CustomRule(
                name="No project name",
                pattern=r"\bOntoRalph\b",
                message="Don't mention the project name",
                severity=RuleSeverity.WARNING,
            ),
        ]

        evaluator = ChecklistEvaluator(custom_rules=rules)

        results = evaluator.evaluate(
            definition="An ICE defined by OntoRalph",
            term="Test",
            is_ice=True,
        )

        # Should have custom rule result
        custom_results = [r for r in results if r.code.startswith("X")]
        assert len(custom_results) == 1
        assert not custom_results[0].passed


class TestCustomPromptTemplates:
    """Tests for custom prompt templates (AC8.4)."""

    def test_default_templates(self) -> None:
        """Test using default templates when none configured."""
        manager = PromptTemplateManager()

        class_info = ClassInfo(
            iri=":Test",
            label="Test",
            parent_class="owl:Thing",
            is_ice=True,
        )

        prompt = manager.format_generate(class_info)
        assert "Test" in prompt
        assert "owl:Thing" in prompt

    def test_custom_template_from_config(self) -> None:
        """Test loading custom template from config string."""
        config = PromptConfig(
            generate_template="Generate definition for ${label} (${iri}) with parent ${parent_class}",
        )

        manager = PromptTemplateManager(config)

        class_info = ClassInfo(
            iri=":MyClass",
            label="My Class",
            parent_class="cco:ICE",
            is_ice=True,
        )

        prompt = manager.format_generate(class_info)
        assert "My Class" in prompt
        assert ":MyClass" in prompt
        assert "cco:ICE" in prompt

    def test_custom_template_from_file(self) -> None:
        """Test loading custom templates from directory (AC8.4)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_dir = Path(tmpdir)

            # Create a custom generate template
            (templates_dir / "generate.txt").write_text(
                "Custom template for ${label}: Parent is ${parent_class}",
                encoding="utf-8",
            )

            config = PromptConfig(templates_dir=templates_dir)
            manager = PromptTemplateManager(config)

            class_info = ClassInfo(
                iri=":Test",
                label="Test Entity",
                parent_class="owl:Thing",
                is_ice=False,
            )

            prompt = manager.format_generate(class_info)
            assert "Custom template for Test Entity" in prompt
            assert "Parent is owl:Thing" in prompt

    def test_template_variable_substitution(self) -> None:
        """Test all template variables are substituted."""
        config = PromptConfig(
            generate_template=(
                "IRI: ${iri}, Label: ${label}, Parent: ${parent_class}, "
                "ICE: ${is_ice}, Siblings: ${siblings}, "
                "Current: ${current_definition}"
            ),
        )

        manager = PromptTemplateManager(config)

        class_info = ClassInfo(
            iri=":TestClass",
            label="Test Class",
            parent_class="cco:Entity",
            sibling_classes=[":Sibling1", ":Sibling2"],
            is_ice=True,
            current_definition="Old definition",
        )

        prompt = manager.format_generate(class_info)

        assert ":TestClass" in prompt
        assert "Test Class" in prompt
        assert "cco:Entity" in prompt
        assert "True" in prompt
        assert ":Sibling1" in prompt
        assert ":Sibling2" in prompt
        assert "Old definition" in prompt


class TestLoadSettings:
    """Tests for the load_settings convenience function."""

    def test_load_from_specific_file(self) -> None:
        """Test loading from a specific config file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"loop": {"max_iterations": 9}}, f)
            config_path = f.name

        try:
            settings = load_settings(config_file=config_path)
            assert settings.loop.max_iterations == 9
        finally:
            os.unlink(config_path)

    def test_load_with_cli_overrides(self) -> None:
        """Test loading with CLI overrides only."""
        settings = load_settings(cli_overrides={"loop": {"max_iterations": 6}})
        assert settings.loop.max_iterations == 6


class TestIntegration:
    """Integration tests for configuration."""

    def test_full_config_workflow(self) -> None:
        """Test full configuration workflow with all features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config with custom rules
            config_path = Path(tmpdir) / "ontoralph.yaml"
            config_data = {
                "llm": {
                    "provider": "mock",
                    "model": "test-model",
                },
                "loop": {
                    "max_iterations": 3,
                },
                "checklist": {
                    "strictness": "strict",
                    "custom_rules": [
                        {
                            "name": "No acronyms",
                            "pattern": r"\b[A-Z]{2,}\b",
                            "message": "Avoid acronyms in definitions",
                            "severity": "warning",
                        },
                    ],
                },
                "output": {
                    "format": "turtle",
                    "include_comments": True,
                },
            }
            config_path.write_text(yaml.dump(config_data), encoding="utf-8")

            # Load config
            settings = Settings.load_from_file(config_path)

            # Verify all settings loaded correctly
            assert settings.llm.provider == LLMProviderType.MOCK
            assert settings.loop.max_iterations == 3
            assert settings.checklist.strictness == StrictnessLevel.STRICT
            assert len(settings.checklist.custom_rules) == 1
            assert settings.checklist.custom_rules[0].name == "No acronyms"
            assert settings.output.format == OutputFormat.TURTLE

            # Test custom rule evaluation
            evaluator = ChecklistEvaluator(
                custom_rules=settings.checklist.custom_rules
            )
            results = evaluator.evaluate(
                definition="An ICE that uses XML and JSON formats",
                term="Test",
                is_ice=True,
            )

            # Should have custom rule result (matching XML and JSON)
            custom_results = [r for r in results if r.code.startswith("X")]
            assert len(custom_results) == 1
            assert not custom_results[0].passed
