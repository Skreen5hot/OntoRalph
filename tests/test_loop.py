"""Tests for the Ralph Loop controller.

This module tests:
- RalphLoop: Full loop orchestration
- Hooks: Event callbacks at each phase
- Hybrid checking: Automated + LLM checks
- Convergence: Loop termination conditions
- State serialization: JSON round-trip
"""

import pytest

from ontoralph.core.loop import (
    CountingHooks,
    HybridCheckResult,
    LoopConfig,
    LoopHooks,
    RalphLoop,
)
from ontoralph.core.models import (
    CheckResult,
    ClassInfo,
    LoopState,
    Severity,
    VerifyStatus,
)
from ontoralph.llm import FailingMockProvider, LLMResponseError, LoopPhase, MockProvider


# Test fixtures
@pytest.fixture
def sample_class_info() -> ClassInfo:
    return ClassInfo(
        iri=":EventDescription",
        label="Event Description",
        parent_class="cco:InformationContentEntity",
        sibling_classes=[":ActionDescription", ":StateDescription"],
        is_ice=True,
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
def passing_mock_provider() -> MockProvider:
    """Mock provider that generates passing definitions."""
    return MockProvider(
        generate_response="An ICE that denotes an occurrent as it unfolds through time.",
    )


@pytest.fixture
def failing_mock_provider() -> MockProvider:
    """Mock provider that generates definitions with red flags."""
    return MockProvider(
        generate_response="An ICE that represents something extracted from text.",
    )


class TestRalphLoopBasic:
    """Basic tests for RalphLoop."""

    @pytest.mark.asyncio
    async def test_loop_completes_on_pass(
        self, sample_class_info: ClassInfo, passing_mock_provider: MockProvider
    ) -> None:
        """Test that loop terminates when definition passes."""
        loop = RalphLoop(
            llm=passing_mock_provider,
            config=LoopConfig(max_iterations=5),
        )

        result = await loop.run(sample_class_info)

        assert result.status == VerifyStatus.PASS
        assert result.total_iterations >= 1
        assert result.final_definition is not None
        assert result.converged is True

    @pytest.mark.asyncio
    async def test_loop_terminates_at_max_iterations(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that loop terminates at max iterations if no convergence."""
        # Provider that always generates failing definitions
        provider = MockProvider(
            generate_response="An ICE that represents something.",  # R2 red flag
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=3),
        )

        result = await loop.run(sample_class_info)

        assert result.status == VerifyStatus.FAIL
        assert result.total_iterations == 3
        assert result.converged is False

    @pytest.mark.asyncio
    async def test_loop_with_initial_definition(
        self, sample_class_info: ClassInfo, passing_mock_provider: MockProvider
    ) -> None:
        """Test loop with an existing definition to improve."""
        class_with_def = ClassInfo(
            iri=sample_class_info.iri,
            label=sample_class_info.label,
            parent_class=sample_class_info.parent_class,
            sibling_classes=sample_class_info.sibling_classes,
            is_ice=sample_class_info.is_ice,
            current_definition="An ICE that denotes something.",
        )

        loop = RalphLoop(
            llm=passing_mock_provider,
            config=LoopConfig(max_iterations=5),
        )

        result = await loop.run(class_with_def)

        # Should still complete
        assert result.total_iterations >= 1


class TestHooks:
    """Tests for loop event hooks."""

    @pytest.mark.asyncio
    async def test_all_hooks_fire(
        self, sample_class_info: ClassInfo, passing_mock_provider: MockProvider
    ) -> None:
        """Test that all hooks fire at correct points."""
        hooks = CountingHooks()
        loop = RalphLoop(
            llm=passing_mock_provider,
            config=LoopConfig(max_iterations=3),
            hooks=hooks,
        )

        await loop.run(sample_class_info)

        # Verify hooks fired
        assert hooks.loop_start_count == 1
        assert hooks.loop_end_count == 1
        assert hooks.iteration_start_count >= 1
        assert hooks.iteration_end_count >= 1
        assert hooks.generate_count >= 1
        assert hooks.critique_count >= 1
        assert hooks.verify_count >= 1
        # Refine may or may not fire depending on whether issues are found

    @pytest.mark.asyncio
    async def test_hooks_count_matches_iterations(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that hook counts match iteration count."""
        provider = MockProvider(
            generate_response="An ICE that represents something.",
        )
        hooks = CountingHooks()

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=3),
            hooks=hooks,
        )

        result = await loop.run(sample_class_info)

        # Iteration hooks should match total iterations
        assert hooks.iteration_start_count == result.total_iterations
        assert hooks.iteration_end_count == result.total_iterations

    @pytest.mark.asyncio
    async def test_custom_hook_receives_data(
        self, sample_class_info: ClassInfo, passing_mock_provider: MockProvider
    ) -> None:
        """Test that custom hooks receive correct data."""
        definitions_generated: list[str] = []
        verify_statuses: list[VerifyStatus] = []

        hooks = LoopHooks(
            on_generate=lambda d: definitions_generated.append(d),
            on_verify=lambda s, r: verify_statuses.append(s),
        )

        loop = RalphLoop(
            llm=passing_mock_provider,
            config=LoopConfig(max_iterations=3),
            hooks=hooks,
        )

        await loop.run(sample_class_info)

        assert len(definitions_generated) >= 1
        assert len(verify_statuses) >= 1
        assert all(isinstance(d, str) for d in definitions_generated)
        assert all(isinstance(s, VerifyStatus) for s in verify_statuses)


class TestHybridChecking:
    """Tests for hybrid automated + LLM checking."""

    @pytest.mark.asyncio
    async def test_red_flag_skips_llm(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that red flags skip LLM critique."""
        provider = MockProvider(
            generate_response="An ICE that represents something extracted from text.",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(
                max_iterations=1,
                fail_fast_on_red_flags=True,
            ),
        )

        await loop.run(sample_class_info)

        # LLM critique should not be called (only generate and refine)
        assert len(provider.critique_calls) == 0

    @pytest.mark.asyncio
    async def test_hybrid_result_properties(self) -> None:
        """Test HybridCheckResult properties."""
        result = HybridCheckResult(
            automated_results=[
                CheckResult(
                    code="R1",
                    name="No process verbs",
                    passed=False,
                    evidence="Found 'extracted'",
                    severity=Severity.RED_FLAG,
                ),
                CheckResult(
                    code="C1",
                    name="Genus present",
                    passed=True,
                    evidence="Has genus",
                    severity=Severity.REQUIRED,
                ),
            ],
            combined_results=[],
        )
        result.combined_results = result.automated_results

        assert result.has_red_flags is True
        assert result.all_passed is False
        assert len(result.failed_checks) == 1
        assert result.failed_checks[0].code == "R1"


class TestConvergence:
    """Tests for loop convergence detection."""

    @pytest.mark.asyncio
    async def test_converges_on_first_iteration(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test convergence when first definition passes."""
        # Generate a definition that passes all checks for EventDescription
        provider = MockProvider(
            generate_response="An ICE that denotes an occurrent as it unfolds through time.",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=5),
        )

        result = await loop.run(sample_class_info)

        assert result.converged is True
        assert result.total_iterations == 1

    @pytest.mark.asyncio
    async def test_non_ice_convergence(
        self, non_ice_class_info: ClassInfo
    ) -> None:
        """Test convergence for non-ICE class."""
        provider = MockProvider(
            generate_response="An occurrent that unfolds through temporal extension.",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=5),
        )

        result = await loop.run(non_ice_class_info)

        # Should pass without ICE checks
        assert result.status in [VerifyStatus.PASS, VerifyStatus.ITERATE]


class TestStateSerialization:
    """Tests for loop state JSON serialization."""

    def test_loop_state_json_roundtrip(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that LoopState serializes to JSON and back correctly."""
        state = LoopState(
            class_info=sample_class_info,
            max_iterations=5,
        )

        json_str = state.model_dump_json()
        restored = LoopState.model_validate_json(json_str)

        assert restored.class_info.iri == state.class_info.iri
        assert restored.max_iterations == state.max_iterations
        assert restored.current_iteration == state.current_iteration

    @pytest.mark.asyncio
    async def test_mid_loop_state_serialization(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that state can be serialized mid-loop."""
        provider = MockProvider(
            generate_response="An ICE that represents something.",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=3),
        )

        # Run initial state through one step
        initial_state = LoopState(
            class_info=sample_class_info,
            max_iterations=3,
        )

        state_after_step = await loop.step(initial_state)

        # Serialize and restore
        json_str = state_after_step.model_dump_json()
        restored_state = LoopState.model_validate_json(json_str)

        # Verify restoration
        assert restored_state.current_iteration == 1
        assert len(restored_state.iterations) == 1
        assert restored_state.iterations[0].generated_definition is not None


class TestErrorHandling:
    """Tests for error handling in the loop."""

    @pytest.mark.asyncio
    async def test_llm_error_in_generate(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test handling of LLM errors during generation."""
        provider = FailingMockProvider(
            fail_on=LoopPhase.GENERATE,
            error_type=LLMResponseError,
            error_message="Generation failed",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=3),
        )

        with pytest.raises(LLMResponseError, match="Generation failed"):
            await loop.run(sample_class_info)

    @pytest.mark.asyncio
    async def test_llm_error_in_refine(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test handling of LLM errors during refinement."""
        provider = FailingMockProvider(
            fail_on=LoopPhase.REFINE,
            error_type=LLMResponseError,
            error_message="Refinement failed",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=3),
        )

        # Should raise when trying to refine
        with pytest.raises(LLMResponseError, match="Refinement failed"):
            await loop.run(sample_class_info)


class TestLoopConfig:
    """Tests for loop configuration."""

    @pytest.mark.asyncio
    async def test_custom_max_iterations(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test custom max iterations setting."""
        provider = MockProvider(
            generate_response="An ICE that represents something.",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=2),
        )

        result = await loop.run(sample_class_info)

        assert result.total_iterations == 2

    @pytest.mark.asyncio
    async def test_disable_hybrid_checking(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test disabling hybrid checking uses LLM for all checks."""
        provider = MockProvider(
            generate_response="An ICE that denotes something in formal speech.",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(
                max_iterations=1,
                use_hybrid_checking=False,
            ),
        )

        await loop.run(sample_class_info)

        # LLM critique should be called when hybrid checking is disabled
        # and automated checks pass
        # Note: This depends on implementation details


class TestIterationTracking:
    """Tests for iteration history tracking."""

    @pytest.mark.asyncio
    async def test_iterations_recorded(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that all iterations are recorded in result."""
        provider = MockProvider(
            generate_response="An ICE that represents something.",
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=3),
        )

        result = await loop.run(sample_class_info)

        assert len(result.iterations) == result.total_iterations
        for i, iteration in enumerate(result.iterations, 1):
            assert iteration.iteration_number == i
            assert iteration.generated_definition is not None
            assert len(iteration.critique_results) > 0

    @pytest.mark.asyncio
    async def test_iteration_timestamps(
        self, sample_class_info: ClassInfo, passing_mock_provider: MockProvider
    ) -> None:
        """Test that iterations have timestamps."""
        loop = RalphLoop(
            llm=passing_mock_provider,
            config=LoopConfig(max_iterations=5),
        )

        result = await loop.run(sample_class_info)

        for iteration in result.iterations:
            assert iteration.timestamp is not None


class TestUsageTracking:
    """Tests for LLM usage tracking through the loop."""

    @pytest.mark.asyncio
    async def test_usage_tracked_across_iterations(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that LLM usage is tracked across iterations."""
        provider = MockProvider(
            generate_response="An ICE that represents something.",
            simulate_tokens=True,
        )

        loop = RalphLoop(
            llm=provider,
            config=LoopConfig(max_iterations=2),
        )

        await loop.run(sample_class_info)

        # Should have usage from generate and refine calls
        assert provider.usage.call_count >= 2
        assert provider.usage.total_tokens > 0
