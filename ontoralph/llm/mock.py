"""Mock LLM provider for testing.

This module provides a mock implementation of the LLM provider interface
that can be used for testing without making actual API calls.
"""

from collections.abc import Callable

from ontoralph.core.models import CheckResult, ClassInfo, Severity
from ontoralph.llm.base import (
    LLMProvider,
    LLMResponseError,
    LoopPhase,
    UsageStats,
)


class MockProvider(LLMProvider):
    """Mock LLM provider for testing.

    Provides configurable responses for each phase of the Ralph Loop,
    simulating LLM behavior without making actual API calls.
    """

    def __init__(
        self,
        generate_response: str | Callable[[ClassInfo], str] | None = None,
        critique_response: list[CheckResult] | Callable[[ClassInfo, str], list[CheckResult]] | None = None,
        refine_response: str | Callable[[ClassInfo, str, list[CheckResult]], str] | None = None,
        simulate_tokens: bool = True,
    ) -> None:
        """Initialize the mock provider.

        Args:
            generate_response: Response for generate() calls. Can be:
                - A static string
                - A callable that takes ClassInfo and returns a string
                - None to use a default response
            critique_response: Response for critique() calls. Can be:
                - A static list of CheckResult
                - A callable that takes (ClassInfo, str) and returns list[CheckResult]
                - None to use a default passing response
            refine_response: Response for refine() calls. Can be:
                - A static string
                - A callable that takes (ClassInfo, str, list[CheckResult]) and returns str
                - None to use a default response
            simulate_tokens: Whether to simulate token usage statistics.
        """
        super().__init__()
        self._generate_response = generate_response
        self._critique_response = critique_response
        self._refine_response = refine_response
        self._simulate_tokens = simulate_tokens

        # Track calls for testing
        self.generate_calls: list[ClassInfo] = []
        self.critique_calls: list[tuple[ClassInfo, str]] = []
        self.refine_calls: list[tuple[ClassInfo, str, list[CheckResult]]] = []

    async def generate(self, class_info: ClassInfo) -> str:
        """Generate an initial definition for a class.

        Args:
            class_info: Information about the class to define.

        Returns:
            A generated definition string.
        """
        self.generate_calls.append(class_info)

        if self._simulate_tokens:
            self._record_usage(
                UsageStats(
                    input_tokens=150,
                    output_tokens=50,
                    total_tokens=200,
                    model="mock-model",
                    phase=LoopPhase.GENERATE,
                    latency_ms=100.0,
                )
            )

        if self._generate_response is None:
            return self._default_generate_response(class_info)
        elif callable(self._generate_response):
            return self._generate_response(class_info)
        else:
            return self._generate_response

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
        self.critique_calls.append((class_info, definition))

        if self._simulate_tokens:
            self._record_usage(
                UsageStats(
                    input_tokens=200,
                    output_tokens=300,
                    total_tokens=500,
                    model="mock-model",
                    phase=LoopPhase.CRITIQUE,
                    latency_ms=150.0,
                )
            )

        if self._critique_response is None:
            return self._default_critique_response(class_info, definition)
        elif callable(self._critique_response):
            return self._critique_response(class_info, definition)
        else:
            return self._critique_response

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
        self.refine_calls.append((class_info, definition, issues))

        if self._simulate_tokens:
            self._record_usage(
                UsageStats(
                    input_tokens=250,
                    output_tokens=60,
                    total_tokens=310,
                    model="mock-model",
                    phase=LoopPhase.REFINE,
                    latency_ms=120.0,
                )
            )

        if self._refine_response is None:
            return self._default_refine_response(class_info, definition, issues)
        elif callable(self._refine_response):
            return self._refine_response(class_info, definition, issues)
        else:
            return self._refine_response

    def _default_generate_response(self, class_info: ClassInfo) -> str:
        """Generate a default response for testing.

        Args:
            class_info: Information about the class.

        Returns:
            A plausible definition string.
        """
        if class_info.is_ice:
            return f"An ICE that denotes a {class_info.label.lower()} as specified in formal discourse."
        else:
            parent_name = class_info.parent_class.split(":")[-1]
            return f"A {parent_name} that is characterized by its role as a {class_info.label.lower()}."

    def _default_critique_response(
        self, class_info: ClassInfo, _definition: str
    ) -> list[CheckResult]:
        """Generate a default critique response (all passing).

        Args:
            class_info: Information about the class.
            definition: The definition being critiqued.

        Returns:
            List of passing check results.
        """
        results = [
            CheckResult(
                code="C1",
                name="Genus present",
                passed=True,
                evidence="Definition includes genus reference.",
                severity=Severity.REQUIRED,
            ),
            CheckResult(
                code="C2",
                name="Differentia present",
                passed=True,
                evidence="Definition includes differentiating characteristics.",
                severity=Severity.REQUIRED,
            ),
            CheckResult(
                code="C3",
                name="Non-circular",
                passed=True,
                evidence="Term does not appear in definition.",
                severity=Severity.REQUIRED,
            ),
            CheckResult(
                code="C4",
                name="Single sentence",
                passed=True,
                evidence="Definition is a single sentence.",
                severity=Severity.REQUIRED,
            ),
            CheckResult(
                code="Q1",
                name="Appropriate length",
                passed=True,
                evidence="Definition length is appropriate.",
                severity=Severity.QUALITY,
            ),
            CheckResult(
                code="Q2",
                name="Clear and readable",
                passed=True,
                evidence="Definition is clear and readable.",
                severity=Severity.QUALITY,
            ),
            CheckResult(
                code="Q3",
                name="Standard terminology",
                passed=True,
                evidence="Definition uses standard terminology.",
                severity=Severity.QUALITY,
            ),
            CheckResult(
                code="R1",
                name="No process verbs",
                passed=True,
                evidence="No process verbs found.",
                severity=Severity.RED_FLAG,
            ),
            CheckResult(
                code="R2",
                name="Uses 'denotes' not 'represents'",
                passed=True,
                evidence="Correct usage of terminology.",
                severity=Severity.RED_FLAG,
            ),
            CheckResult(
                code="R3",
                name="No functional language",
                passed=True,
                evidence="No functional language found.",
                severity=Severity.RED_FLAG,
            ),
            CheckResult(
                code="R4",
                name="No syntactic terms",
                passed=True,
                evidence="No syntactic terms found.",
                severity=Severity.RED_FLAG,
            ),
        ]

        # Add ICE-specific checks if needed
        if class_info.is_ice:
            results.extend(
                [
                    CheckResult(
                        code="I1",
                        name="ICE pattern start",
                        passed=True,
                        evidence="Definition starts with ICE pattern.",
                        severity=Severity.ICE_REQUIRED,
                    ),
                    CheckResult(
                        code="I2",
                        name="Uses 'denotes' or 'is about'",
                        passed=True,
                        evidence="Definition uses appropriate ICE verb.",
                        severity=Severity.ICE_REQUIRED,
                    ),
                    CheckResult(
                        code="I3",
                        name="Specifies denotation",
                        passed=True,
                        evidence="Definition specifies what ICE denotes.",
                        severity=Severity.ICE_REQUIRED,
                    ),
                ]
            )

        return results

    def _default_refine_response(
        self,
        class_info: ClassInfo,
        _definition: str,
        _issues: list[CheckResult],
    ) -> str:
        """Generate a default refined response.

        Args:
            class_info: Information about the class.
            definition: The current definition.
            issues: List of failed checks.

        Returns:
            A refined definition string.
        """
        # Return the original definition with minor modification
        if class_info.is_ice:
            return f"An ICE that denotes a {class_info.label.lower()} as formally specified in discourse."
        else:
            parent_name = class_info.parent_class.split(":")[-1]
            return f"A {parent_name} that is distinctively characterized as a {class_info.label.lower()}."

    def reset(self) -> None:
        """Reset the mock provider state."""
        self.generate_calls.clear()
        self.critique_calls.clear()
        self.refine_calls.clear()
        self.reset_usage()


class FailingMockProvider(MockProvider):
    """Mock provider that simulates failures for testing error handling."""

    def __init__(
        self,
        fail_on: LoopPhase | None = None,
        error_type: type[Exception] = LLMResponseError,
        error_message: str = "Simulated failure",
    ) -> None:
        """Initialize the failing mock provider.

        Args:
            fail_on: Which phase to fail on (None = never fail).
            error_type: Type of exception to raise.
            error_message: Error message to include.
        """
        super().__init__()
        self.fail_on = fail_on
        self.error_type = error_type
        self.error_message = error_message

    async def generate(self, class_info: ClassInfo) -> str:
        if self.fail_on == LoopPhase.GENERATE:
            raise self.error_type(self.error_message)
        return await super().generate(class_info)

    async def critique(
        self, class_info: ClassInfo, definition: str
    ) -> list[CheckResult]:
        if self.fail_on == LoopPhase.CRITIQUE:
            raise self.error_type(self.error_message)
        return await super().critique(class_info, definition)

    async def refine(
        self, class_info: ClassInfo, definition: str, issues: list[CheckResult]
    ) -> str:
        if self.fail_on == LoopPhase.REFINE:
            raise self.error_type(self.error_message)
        return await super().refine(class_info, definition, issues)
