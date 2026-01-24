"""Tests for the LLM integration module.

This module tests:
- ResponseParser: Parsing LLM responses
- MockProvider: Mock provider for testing
- Usage tracking: Token counting and cost estimation
- Error handling: Graceful failure scenarios
"""

import pytest

from ontoralph.core.models import CheckResult, ClassInfo, Severity
from ontoralph.llm import (
    FailingMockProvider,
    LLMAuthenticationError,
    LLMResponseError,
    LoopPhase,
    MockProvider,
    ResponseParser,
    SessionUsage,
    UsageStats,
)


# Test fixtures
@pytest.fixture
def sample_class_info() -> ClassInfo:
    return ClassInfo(
        iri=":VerbPhrase",
        label="Verb Phrase",
        parent_class="cco:InformationContentEntity",
        sibling_classes=[":NounPhrase", ":DiscourseReferent"],
        is_ice=True,
        current_definition=None,
    )


@pytest.fixture
def non_ice_class_info() -> ClassInfo:
    return ClassInfo(
        iri=":Process",
        label="Process",
        parent_class="bfo:Occurrent",
        sibling_classes=[],
        is_ice=False,
    )


@pytest.fixture
def sample_issues() -> list[CheckResult]:
    return [
        CheckResult(
            code="R2",
            name="Uses 'denotes' not 'represents'",
            passed=False,
            evidence="Found 'represents' in definition",
            severity=Severity.RED_FLAG,
        ),
        CheckResult(
            code="Q1",
            name="Appropriate length",
            passed=False,
            evidence="Definition too short",
            severity=Severity.QUALITY,
        ),
    ]


class TestResponseParser:
    """Tests for ResponseParser."""

    @pytest.fixture
    def parser(self) -> ResponseParser:
        return ResponseParser()

    # Definition parsing tests
    @pytest.mark.parametrize(
        "response,expected",
        [
            # Clean definition
            (
                "An ICE that denotes an occurrent.",
                "An ICE that denotes an occurrent.",
            ),
            # With quotes
            (
                '"An ICE that denotes an occurrent."',
                "An ICE that denotes an occurrent.",
            ),
            # With prefix
            (
                "Definition: An ICE that denotes an occurrent.",
                "An ICE that denotes an occurrent.",
            ),
            # With code block
            (
                "```\nAn ICE that denotes an occurrent.\n```",
                "An ICE that denotes an occurrent.",
            ),
            # With whitespace
            (
                "  An ICE that denotes an occurrent.  ",
                "An ICE that denotes an occurrent.",
            ),
        ],
    )
    def test_parse_definition_valid(
        self, parser: ResponseParser, response: str, expected: str
    ) -> None:
        result = parser.parse_definition(response)
        assert result == expected

    def test_parse_definition_empty(self, parser: ResponseParser) -> None:
        with pytest.raises(LLMResponseError, match="Empty response"):
            parser.parse_definition("")

    def test_parse_definition_too_short(self, parser: ResponseParser) -> None:
        with pytest.raises(LLMResponseError, match="too short"):
            parser.parse_definition("Short")

    # Critique parsing tests
    def test_parse_critique_valid_json(self, parser: ResponseParser) -> None:
        response = """```json
[
  {"code": "C1", "name": "Genus present", "passed": true, "evidence": "Has genus"},
  {"code": "R1", "name": "No process verbs", "passed": false, "evidence": "Found 'extracted'"}
]
```"""
        results = parser.parse_critique(response)
        assert len(results) == 2
        assert results[0].code == "C1"
        assert results[0].passed is True
        assert results[1].code == "R1"
        assert results[1].passed is False

    def test_parse_critique_json_array_direct(self, parser: ResponseParser) -> None:
        response = '[{"code": "C1", "passed": true, "evidence": "OK"}]'
        results = parser.parse_critique(response)
        assert len(results) == 1
        assert results[0].code == "C1"

    def test_parse_critique_handles_variations(self, parser: ResponseParser) -> None:
        # Test different ways LLMs might express pass/fail
        response = """[
            {"code": "C1", "pass": "yes", "reason": "Has genus"},
            {"code": "C2", "passed": "false", "explanation": "Missing differentia"},
            {"code": "R1", "result": true, "evidence": "Clean"}
        ]"""
        results = parser.parse_critique(response)
        assert len(results) == 3
        assert results[0].passed is True
        assert results[1].passed is False
        assert results[2].passed is True

    def test_parse_critique_empty(self, parser: ResponseParser) -> None:
        with pytest.raises(LLMResponseError, match="Empty response"):
            parser.parse_critique("")

    def test_parse_critique_no_json(self, parser: ResponseParser) -> None:
        with pytest.raises(LLMResponseError, match="Could not find valid JSON"):
            parser.parse_critique("This is not JSON at all")

    def test_parse_critique_no_valid_results(self, parser: ResponseParser) -> None:
        with pytest.raises(LLMResponseError, match="No valid check results"):
            parser.parse_critique('[{"invalid": "data"}]')

    # Definition format validation
    def test_validate_definition_format_good(self, parser: ResponseParser) -> None:
        warnings = parser.validate_definition_format(
            "An ICE that denotes an occurrent.", is_ice=True
        )
        assert len(warnings) == 0

    def test_validate_definition_format_no_capital(
        self, parser: ResponseParser
    ) -> None:
        warnings = parser.validate_definition_format("an ICE that denotes something.")
        assert any("capital" in w.lower() for w in warnings)

    def test_validate_definition_format_no_period(self, parser: ResponseParser) -> None:
        warnings = parser.validate_definition_format("An ICE that denotes something")
        assert any("period" in w.lower() for w in warnings)

    def test_validate_definition_format_ice_no_ice_start(
        self, parser: ResponseParser
    ) -> None:
        warnings = parser.validate_definition_format(
            "A thing that does something.", is_ice=True
        )
        assert any("ICE" in w for w in warnings)

    def test_validate_definition_format_ice_uses_represents(
        self, parser: ResponseParser
    ) -> None:
        warnings = parser.validate_definition_format(
            "An ICE that represents something.", is_ice=True
        )
        assert any("denotes" in w for w in warnings)

    def test_parse_definition_lowercase_start_with_later_sentence(
        self, parser: ResponseParser
    ) -> None:
        """Test parsing when definition starts lowercase but contains valid sentence."""
        response = "here is the definition: An ICE that denotes an occurrent."
        # Should extract the capitalized sentence
        result = parser.parse_definition(response)
        assert result.startswith("An ICE")

    def test_parse_critique_with_extra_text_around_json(
        self, parser: ResponseParser
    ) -> None:
        """Test parsing critique with extra text around JSON array."""
        response = """Here are the results:

[{"code": "C1", "name": "Genus", "passed": true, "evidence": "OK"}]

This should pass."""
        results = parser.parse_critique(response)
        assert len(results) == 1
        assert results[0].code == "C1"

    def test_parse_critique_json_in_code_block_with_invalid_content(
        self, parser: ResponseParser
    ) -> None:
        """Test parsing when code block has invalid JSON but array exists."""
        response = """```json
invalid json here
```

[{"code": "C2", "passed": false, "evidence": "Failed"}]"""
        results = parser.parse_critique(response)
        assert len(results) == 1
        assert results[0].code == "C2"


class TestMockProvider:
    """Tests for MockProvider."""

    @pytest.mark.asyncio
    async def test_generate_default_ice(self, sample_class_info: ClassInfo) -> None:
        provider = MockProvider()
        result = await provider.generate(sample_class_info)

        assert "ICE" in result
        assert "denotes" in result
        assert len(provider.generate_calls) == 1
        assert provider.generate_calls[0] == sample_class_info

    @pytest.mark.asyncio
    async def test_generate_default_non_ice(
        self, non_ice_class_info: ClassInfo
    ) -> None:
        provider = MockProvider()
        result = await provider.generate(non_ice_class_info)

        assert "ICE" not in result
        assert "Occurrent" in result or "occurrent" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_custom_response(
        self, sample_class_info: ClassInfo
    ) -> None:
        custom = "Custom definition for testing."
        provider = MockProvider(generate_response=custom)
        result = await provider.generate(sample_class_info)
        assert result == custom

    @pytest.mark.asyncio
    async def test_generate_callable_response(
        self, sample_class_info: ClassInfo
    ) -> None:
        def custom_generator(info: ClassInfo) -> str:
            return f"Definition for {info.label}."

        provider = MockProvider(generate_response=custom_generator)
        result = await provider.generate(sample_class_info)
        assert result == "Definition for Verb Phrase."

    @pytest.mark.asyncio
    async def test_critique_default(self, sample_class_info: ClassInfo) -> None:
        provider = MockProvider()
        definition = "An ICE that denotes something."
        results = await provider.critique(sample_class_info, definition)

        assert len(results) > 0
        # Should include ICE checks since is_ice=True
        codes = [r.code for r in results]
        assert "I1" in codes
        assert "I2" in codes
        assert "I3" in codes
        # Should all pass by default
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_critique_non_ice(self, non_ice_class_info: ClassInfo) -> None:
        provider = MockProvider()
        results = await provider.critique(non_ice_class_info, "A definition.")

        codes = [r.code for r in results]
        # Should NOT include ICE checks
        assert "I1" not in codes
        assert "I2" not in codes
        assert "I3" not in codes

    @pytest.mark.asyncio
    async def test_refine(
        self, sample_class_info: ClassInfo, sample_issues: list[CheckResult]
    ) -> None:
        provider = MockProvider()
        definition = "An ICE that represents something."
        result = await provider.refine(sample_class_info, definition, sample_issues)

        assert len(result) > 0
        assert len(provider.refine_calls) == 1
        assert provider.refine_calls[0] == (sample_class_info, definition, sample_issues)

    @pytest.mark.asyncio
    async def test_usage_tracking(self, sample_class_info: ClassInfo) -> None:
        provider = MockProvider(simulate_tokens=True)

        await provider.generate(sample_class_info)
        await provider.critique(sample_class_info, "A definition.")
        await provider.refine(sample_class_info, "A definition.", [])

        assert provider.usage.call_count == 3
        assert provider.usage.total_tokens > 0
        assert len(provider.usage.by_phase(LoopPhase.GENERATE)) == 1
        assert len(provider.usage.by_phase(LoopPhase.CRITIQUE)) == 1
        assert len(provider.usage.by_phase(LoopPhase.REFINE)) == 1

    @pytest.mark.asyncio
    async def test_reset(self, sample_class_info: ClassInfo) -> None:
        provider = MockProvider()
        await provider.generate(sample_class_info)

        assert len(provider.generate_calls) == 1
        assert provider.usage.call_count == 1

        provider.reset()

        assert len(provider.generate_calls) == 0
        assert provider.usage.call_count == 0


class TestFailingMockProvider:
    """Tests for FailingMockProvider."""

    @pytest.mark.asyncio
    async def test_fail_on_generate(self, sample_class_info: ClassInfo) -> None:
        provider = FailingMockProvider(
            fail_on=LoopPhase.GENERATE,
            error_type=LLMResponseError,
            error_message="Generate failed",
        )

        with pytest.raises(LLMResponseError, match="Generate failed"):
            await provider.generate(sample_class_info)

    @pytest.mark.asyncio
    async def test_fail_on_critique(self, sample_class_info: ClassInfo) -> None:
        provider = FailingMockProvider(
            fail_on=LoopPhase.CRITIQUE,
            error_type=LLMResponseError,
            error_message="Critique failed",
        )

        # Generate should work
        result = await provider.generate(sample_class_info)
        assert result is not None

        # Critique should fail
        with pytest.raises(LLMResponseError, match="Critique failed"):
            await provider.critique(sample_class_info, "A definition.")

    @pytest.mark.asyncio
    async def test_fail_on_refine(
        self, sample_class_info: ClassInfo, sample_issues: list[CheckResult]
    ) -> None:
        provider = FailingMockProvider(
            fail_on=LoopPhase.REFINE,
            error_type=LLMAuthenticationError,
            error_message="Auth failed",
        )

        with pytest.raises(LLMAuthenticationError, match="Auth failed"):
            await provider.refine(sample_class_info, "A definition.", sample_issues)


class TestUsageStats:
    """Tests for usage statistics."""

    def test_usage_stats_cost_calculation(self) -> None:
        stats = UsageStats(
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            model="claude-sonnet-4-20250514",
            phase=LoopPhase.GENERATE,
        )

        # Cost should be calculated based on model rates
        assert stats.estimated_cost_usd > 0
        # Should be reasonable (less than $0.05 for this sample)
        assert stats.estimated_cost_usd < 0.05

    def test_session_usage_aggregation(self) -> None:
        usage = SessionUsage()
        usage.calls.append(
            UsageStats(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                model="mock",
                phase=LoopPhase.GENERATE,
            )
        )
        usage.calls.append(
            UsageStats(
                input_tokens=200,
                output_tokens=100,
                total_tokens=300,
                model="mock",
                phase=LoopPhase.CRITIQUE,
            )
        )

        assert usage.total_input_tokens == 300
        assert usage.total_output_tokens == 150
        assert usage.total_tokens == 450
        assert usage.call_count == 2

    def test_session_usage_summary(self) -> None:
        usage = SessionUsage()
        usage.calls.append(
            UsageStats(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                model="mock",
                phase=LoopPhase.GENERATE,
            )
        )

        summary = usage.summary()
        assert summary["total_calls"] == 1
        assert summary["total_tokens"] == 150
        assert "by_phase" in summary
        assert summary["by_phase"]["generate"] == 1


class TestPromptTemplates:
    """Tests for prompt template formatting."""

    def test_generate_prompt_ice(self, sample_class_info: ClassInfo) -> None:
        from ontoralph.llm.prompts import format_generate_prompt

        prompt = format_generate_prompt(sample_class_info)

        assert ":VerbPhrase" in prompt
        assert "Verb Phrase" in prompt
        assert "cco:InformationContentEntity" in prompt
        assert "ICE" in prompt  # ICE-specific instructions
        assert "denotes" in prompt

    def test_generate_prompt_non_ice(self, non_ice_class_info: ClassInfo) -> None:
        from ontoralph.llm.prompts import format_generate_prompt

        prompt = format_generate_prompt(non_ice_class_info)

        assert ":Process" in prompt
        assert "bfo:Occurrent" in prompt
        # Should not have ICE-specific instructions
        assert "IMPORTANT: This is an Information Content Entity" not in prompt

    def test_critique_prompt(self, sample_class_info: ClassInfo) -> None:
        from ontoralph.llm.prompts import format_critique_prompt

        prompt = format_critique_prompt(
            sample_class_info, "An ICE that denotes something."
        )

        assert "An ICE that denotes something." in prompt
        assert "C1" in prompt
        assert "R1" in prompt
        assert "I1" in prompt  # ICE checks included

    def test_refine_prompt(
        self, sample_class_info: ClassInfo, sample_issues: list[CheckResult]
    ) -> None:
        from ontoralph.llm.prompts import format_refine_prompt

        prompt = format_refine_prompt(
            sample_class_info, "An ICE that represents something.", sample_issues
        )

        assert "An ICE that represents something." in prompt
        assert "R2" in prompt  # Issue code
        assert "represents" in prompt  # Issue evidence


# Integration-style tests using mock
class TestMockProviderIntegration:
    """Integration tests using MockProvider."""

    @pytest.mark.asyncio
    async def test_full_loop_simulation(self, sample_class_info: ClassInfo) -> None:
        """Test a complete Generate -> Critique -> Refine cycle."""
        provider = MockProvider()

        # Generate
        definition = await provider.generate(sample_class_info)
        assert definition is not None
        assert len(definition) > 10

        # Critique
        results = await provider.critique(sample_class_info, definition)
        assert len(results) > 0

        # Refine (even though all pass, test the flow)
        refined = await provider.refine(sample_class_info, definition, [])
        assert refined is not None

        # Check usage was tracked
        assert provider.usage.call_count == 3

    @pytest.mark.asyncio
    async def test_custom_critique_flow(self, sample_class_info: ClassInfo) -> None:
        """Test with custom critique response that triggers refinement."""
        # Set up provider to return failing critique
        failing_checks = [
            CheckResult(
                code="R2",
                name="Uses 'denotes' not 'represents'",
                passed=False,
                evidence="Found 'represents'",
                severity=Severity.RED_FLAG,
            )
        ]

        provider = MockProvider(critique_response=failing_checks)

        definition = await provider.generate(sample_class_info)
        results = await provider.critique(sample_class_info, definition)

        # Should have the failing check
        assert len(results) == 1
        assert not results[0].passed
        assert results[0].code == "R2"

        # Should trigger refinement
        failed = [r for r in results if not r.passed]
        refined = await provider.refine(sample_class_info, definition, failed)
        assert refined != definition  # Should be different


class TestPromptTemplateManagerExtended:
    """Extended tests for PromptTemplateManager to improve coverage."""

    def test_format_generate_with_siblings(self) -> None:
        """Test generate prompt with sibling classes."""
        from ontoralph.llm.prompts import format_generate_prompt

        class_info = ClassInfo(
            iri=":TestClass",
            label="Test Class",
            parent_class="cco:Entity",
            sibling_classes=[":Sibling1", ":Sibling2"],
            is_ice=False,
        )

        prompt = format_generate_prompt(class_info)
        assert ":Sibling1" in prompt
        assert ":Sibling2" in prompt
        assert "Sibling classes" in prompt

    def test_format_generate_with_current_definition(self) -> None:
        """Test generate prompt with existing definition to improve."""
        from ontoralph.llm.prompts import format_generate_prompt

        class_info = ClassInfo(
            iri=":TestClass",
            label="Test Class",
            parent_class="cco:Entity",
            is_ice=False,
            current_definition="Old definition to improve.",
        )

        prompt = format_generate_prompt(class_info)
        assert "Old definition to improve." in prompt
        assert "Current definition" in prompt

    def test_format_critique_non_ice(self) -> None:
        """Test critique prompt for non-ICE class."""
        from ontoralph.llm.prompts import format_critique_prompt

        class_info = ClassInfo(
            iri=":TestClass",
            label="Test Class",
            parent_class="bfo:Continuant",
            is_ice=False,
        )

        prompt = format_critique_prompt(class_info, "A continuant that exists.")
        assert "C1" in prompt
        assert "R1" in prompt
        # Should NOT include ICE checks
        assert "I1-I3" not in prompt

    def test_format_refine_ice(self) -> None:
        """Test refine prompt for ICE class."""
        from ontoralph.llm.prompts import format_refine_prompt

        class_info = ClassInfo(
            iri=":TestICE",
            label="Test ICE",
            parent_class="cco:ICE",
            is_ice=True,
        )

        issues = [
            CheckResult(
                code="R2",
                name="Uses represents",
                passed=False,
                evidence="Found represents",
                severity=Severity.RED_FLAG,
            )
        ]

        prompt = format_refine_prompt(class_info, "An ICE that represents.", issues)
        assert "R2" in prompt
        assert "represents" in prompt
        assert "denotes" in prompt  # ICE instructions

    def test_format_class_context(self) -> None:
        """Test formatting class context."""
        from ontoralph.llm.prompts import format_class_context

        class_info = ClassInfo(
            iri=":TestClass",
            label="Test Class",
            parent_class="cco:Entity",
            sibling_classes=[":Sibling1"],
            is_ice=True,
            current_definition="Old def.",
        )

        context = format_class_context(class_info)
        assert ":TestClass" in context
        assert "Test Class" in context
        assert "cco:Entity" in context
        assert "True" in context
        assert ":Sibling1" in context
        assert "Old def." in context

    def test_template_manager_custom_critique(self) -> None:
        """Test PromptTemplateManager with custom critique template."""
        import tempfile
        from pathlib import Path

        from ontoralph.config import PromptConfig
        from ontoralph.llm.prompts import PromptTemplateManager

        with tempfile.TemporaryDirectory() as tmpdir:
            templates_dir = Path(tmpdir)
            (templates_dir / "critique.txt").write_text(
                "Critique: ${definition} for ${label}",
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

            prompt = manager.format_critique(class_info, "A test definition.")
            assert "Critique:" in prompt
            assert "A test definition." in prompt
            assert "Test Entity" in prompt

    def test_template_manager_custom_refine(self) -> None:
        """Test PromptTemplateManager with custom refine template."""
        import tempfile
        from pathlib import Path

        from ontoralph.config import PromptConfig
        from ontoralph.llm.prompts import PromptTemplateManager

        with tempfile.TemporaryDirectory() as tmpdir:
            templates_dir = Path(tmpdir)
            (templates_dir / "refine.txt").write_text(
                "Refine: ${definition} Issues: ${issues}",
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

            issues = [
                CheckResult(
                    code="C1",
                    name="Missing genus",
                    passed=False,
                    evidence="No genus found",
                    severity=Severity.REQUIRED,
                )
            ]

            prompt = manager.format_refine(class_info, "Bad definition.", issues)
            assert "Refine:" in prompt
            assert "Bad definition." in prompt
            assert "C1" in prompt

    def test_template_manager_custom_system_prompt(self) -> None:
        """Test PromptTemplateManager with custom system prompt."""
        import tempfile
        from pathlib import Path

        from ontoralph.config import PromptConfig
        from ontoralph.llm.prompts import PromptTemplateManager

        with tempfile.TemporaryDirectory() as tmpdir:
            templates_dir = Path(tmpdir)
            (templates_dir / "system.txt").write_text(
                "Custom system prompt for testing.",
                encoding="utf-8",
            )

            config = PromptConfig(templates_dir=templates_dir)
            manager = PromptTemplateManager(config)

            prompt = manager.get_system_prompt()
            assert "Custom system prompt" in prompt

    def test_get_template_manager_with_config(self) -> None:
        """Test get_template_manager with configuration."""
        from ontoralph.config import PromptConfig
        from ontoralph.llm.prompts import get_template_manager

        config = PromptConfig(
            generate_template="Test template ${label}"
        )

        manager = get_template_manager(config)
        class_info = ClassInfo(
            iri=":Test",
            label="Test",
            parent_class="owl:Thing",
            is_ice=False,
        )

        prompt = manager.format_generate(class_info)
        assert "Test template Test" in prompt
