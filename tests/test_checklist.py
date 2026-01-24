"""Tests for the checklist evaluation module.

This module tests:
- RedFlagDetector: Pattern-based detection of anti-patterns
- CircularityChecker: Term-in-definition detection
- ChecklistEvaluator: Full evaluation and scoring logic
"""

import pytest

from ontoralph.core.checklist import (
    ChecklistEvaluator,
    CircularityChecker,
    RedFlagDetector,
)
from ontoralph.core.models import Severity, VerifyStatus


class TestRedFlagDetector:
    """Tests for RedFlagDetector."""

    @pytest.fixture
    def detector(self) -> RedFlagDetector:
        return RedFlagDetector()

    # Test R1: Process verbs
    @pytest.mark.parametrize(
        "definition,expected_pass",
        [
            ("An ICE extracted from text", False),
            ("An ICE detected in the document", False),
            ("An ICE identified by the parser", False),
            ("An ICE parsed from the input", False),
            ("An ICE that denotes an occurrent", True),  # Clean
        ],
    )
    def test_r1_process_verbs(
        self, detector: RedFlagDetector, definition: str, expected_pass: bool
    ) -> None:
        results = detector.check(definition)
        r1_result = next(r for r in results if r.code == "R1")
        assert r1_result.passed == expected_pass
        assert r1_result.severity == Severity.RED_FLAG

    # Test R2: "represents" instead of "denotes"
    @pytest.mark.parametrize(
        "definition,expected_pass",
        [
            ("An ICE that represents meaning", False),
            ("An entity that represents something", False),
            ("An ICE that denotes an occurrent", True),  # Clean
            ("An ICE that is about a process", True),  # Clean
        ],
    )
    def test_r2_represents(
        self, detector: RedFlagDetector, definition: str, expected_pass: bool
    ) -> None:
        results = detector.check(definition)
        r2_result = next(r for r in results if r.code == "R2")
        assert r2_result.passed == expected_pass
        assert r2_result.severity == Severity.RED_FLAG

    # Test R3: Functional language
    @pytest.mark.parametrize(
        "definition,expected_pass",
        [
            ("An ICE that serves to link entities", False),
            ("A component used to process data", False),
            ("An entity that functions to organize", False),
            ("An ICE that denotes an action", True),  # Clean
        ],
    )
    def test_r3_functional_language(
        self, detector: RedFlagDetector, definition: str, expected_pass: bool
    ) -> None:
        results = detector.check(definition)
        r3_result = next(r for r in results if r.code == "R3")
        assert r3_result.passed == expected_pass
        assert r3_result.severity == Severity.RED_FLAG

    # Test R4: Syntactic terms
    @pytest.mark.parametrize(
        "definition,expected_pass",
        [
            ("An ICE encoded as a noun phrase", False),
            ("A verb phrase in the sentence", False),
            ("An entity encoded as XML", False),
            ("An ICE that denotes an event", True),  # Clean
        ],
    )
    def test_r4_syntactic_terms(
        self, detector: RedFlagDetector, definition: str, expected_pass: bool
    ) -> None:
        results = detector.check(definition)
        r4_result = next(r for r in results if r.code == "R4")
        assert r4_result.passed == expected_pass
        assert r4_result.severity == Severity.RED_FLAG

    # Test multiple red flags
    def test_multiple_red_flags(self, detector: RedFlagDetector) -> None:
        """Test definition with multiple red flag categories."""
        definition = "An ICE extracted from text that represents a verb phrase"
        results = detector.check(definition)

        failed_codes = [r.code for r in results if not r.passed]
        assert "R1" in failed_codes  # extracted
        assert "R2" in failed_codes  # represents
        assert "R4" in failed_codes  # verb phrase

    def test_clean_definition(self, detector: RedFlagDetector) -> None:
        """Test that a clean definition passes all red flag checks."""
        definition = "An ICE that denotes an occurrent as introduced in discourse"
        results = detector.check(definition)

        assert all(r.passed for r in results)
        assert len(results) == 4  # R1, R2, R3, R4


class TestCircularityChecker:
    """Tests for CircularityChecker."""

    @pytest.fixture
    def checker(self) -> CircularityChecker:
        return CircularityChecker()

    def test_direct_term_in_definition(self, checker: CircularityChecker) -> None:
        """Test detection of exact term in definition."""
        result = checker.check(
            "A verb phrase is a phrase containing a verb",
            "Verb Phrase",
        )
        assert not result.passed
        assert result.code == "C3"
        assert result.severity == Severity.REQUIRED

    def test_partial_term_in_definition(self, checker: CircularityChecker) -> None:
        """Test detection of partial term (individual words)."""
        result = checker.check(
            "A phrase with verbal content",
            "Verb Phrase",
        )
        assert not result.passed  # "phrase" is in the definition

    def test_morphological_variant(self, checker: CircularityChecker) -> None:
        """Test detection of morphological variants."""
        result = checker.check(
            "An entity that relates to events",
            "Event",
        )
        assert not result.passed  # "events" (plural) detected

    def test_clean_definition(self, checker: CircularityChecker) -> None:
        """Test that non-circular definition passes."""
        result = checker.check(
            "An ICE that denotes an occurrent as introduced in speech",
            "Discourse Referent",
        )
        assert result.passed

    def test_case_insensitivity(self, checker: CircularityChecker) -> None:
        """Test that check is case-insensitive."""
        result = checker.check(
            "A PERSON who does something",
            "person",
        )
        assert not result.passed


class TestChecklistEvaluator:
    """Tests for ChecklistEvaluator."""

    @pytest.fixture
    def evaluator(self) -> ChecklistEvaluator:
        return ChecklistEvaluator()

    # Test Core Requirements
    def test_c1_genus_present(self, evaluator: ChecklistEvaluator) -> None:
        """Test C1: Genus detection."""
        # Good definition with genus
        results = evaluator.evaluate(
            "An ICE that denotes an occurrent",
            "Test Term",
            is_ice=False,
        )
        c1_result = next(r for r in results if r.code == "C1")
        assert c1_result.passed
        assert c1_result.severity == Severity.REQUIRED

    def test_c2_differentia_present(self, evaluator: ChecklistEvaluator) -> None:
        """Test C2: Differentia detection."""
        results = evaluator.evaluate(
            "An entity that is characterized by temporal extension",
            "Occurrent",
            is_ice=False,
        )
        c2_result = next(r for r in results if r.code == "C2")
        assert c2_result.passed

    def test_c3_circularity(self, evaluator: ChecklistEvaluator) -> None:
        """Test C3: Circularity check integration."""
        results = evaluator.evaluate(
            "A process is a process that occurs over time",
            "Process",
            is_ice=False,
        )
        c3_result = next(r for r in results if r.code == "C3")
        assert not c3_result.passed

    def test_c4_single_sentence(self, evaluator: ChecklistEvaluator) -> None:
        """Test C4: Single sentence check."""
        # Single sentence
        results = evaluator.evaluate(
            "An entity that exists in time.",
            "Temporal Entity",
            is_ice=False,
        )
        c4_result = next(r for r in results if r.code == "C4")
        assert c4_result.passed

        # Multiple sentences
        results = evaluator.evaluate(
            "An entity that exists. It has temporal extension.",
            "Temporal Entity",
            is_ice=False,
        )
        c4_result = next(r for r in results if r.code == "C4")
        assert not c4_result.passed

    # Test ICE Requirements
    def test_ice_requirements_when_ice(self, evaluator: ChecklistEvaluator) -> None:
        """Test that ICE requirements are checked when is_ice=True."""
        results = evaluator.evaluate(
            "An ICE that denotes an occurrent as introduced in discourse",
            "Discourse Referent",
            is_ice=True,
        )

        # Should have I1, I2, I3 results
        ice_codes = [r.code for r in results if r.code.startswith("I")]
        assert "I1" in ice_codes
        assert "I2" in ice_codes
        assert "I3" in ice_codes

    def test_ice_requirements_not_checked_when_not_ice(
        self, evaluator: ChecklistEvaluator
    ) -> None:
        """Test that ICE requirements are not checked when is_ice=False."""
        results = evaluator.evaluate(
            "An entity that exists",
            "Entity",
            is_ice=False,
        )

        # Should not have I1, I2, I3 results
        ice_codes = [r.code for r in results if r.code.startswith("I")]
        assert len(ice_codes) == 0

    def test_i1_ice_pattern_start(self, evaluator: ChecklistEvaluator) -> None:
        """Test I1: ICE pattern start check."""
        # Correct pattern
        results = evaluator.evaluate(
            "An ICE that denotes something",
            "Test",
            is_ice=True,
        )
        i1_result = next(r for r in results if r.code == "I1")
        assert i1_result.passed

        # Wrong pattern
        results = evaluator.evaluate(
            "A thing that does something",
            "Test",
            is_ice=True,
        )
        i1_result = next(r for r in results if r.code == "I1")
        assert not i1_result.passed

    def test_i2_ice_verb(self, evaluator: ChecklistEvaluator) -> None:
        """Test I2: ICE verb (denotes/is about) check."""
        # With "denotes"
        results = evaluator.evaluate(
            "An ICE that denotes an event",
            "Event ICE",
            is_ice=True,
        )
        i2_result = next(r for r in results if r.code == "I2")
        assert i2_result.passed

        # With "is about"
        results = evaluator.evaluate(
            "An ICE that is about processes",
            "Process ICE",
            is_ice=True,
        )
        i2_result = next(r for r in results if r.code == "I2")
        assert i2_result.passed

    # Test Quality Checks
    def test_q1_appropriate_length(self, evaluator: ChecklistEvaluator) -> None:
        """Test Q1: Appropriate length check."""
        # Too short
        results = evaluator.evaluate("A thing.", "Thing", is_ice=False)
        q1_result = next(r for r in results if r.code == "Q1")
        assert not q1_result.passed

        # Appropriate length
        results = evaluator.evaluate(
            "An entity that is characterized by its existence in space and time",
            "Spatial Entity",
            is_ice=False,
        )
        q1_result = next(r for r in results if r.code == "Q1")
        assert q1_result.passed

    def test_q3_standard_terminology(self, evaluator: ChecklistEvaluator) -> None:
        """Test Q3: Standard terminology check."""
        # Non-standard term
        results = evaluator.evaluate(
            "A kind of thing that exists",
            "Entity",
            is_ice=False,
        )
        q3_result = next(r for r in results if r.code == "Q3")
        assert not q3_result.passed

    # Test Scoring Logic
    def test_scoring_pass(self, evaluator: ChecklistEvaluator) -> None:
        """Test PASS status when all checks pass."""
        results = evaluator.evaluate(
            "An ICE that denotes an occurrent as introduced in speech or text",
            "Discourse Referent",
            is_ice=True,
        )
        status = evaluator.determine_status(results, is_ice=True)
        assert status == VerifyStatus.PASS

    def test_scoring_fail_on_red_flag(self, evaluator: ChecklistEvaluator) -> None:
        """Test FAIL status when red flag is present."""
        results = evaluator.evaluate(
            "An ICE extracted from text that denotes something",
            "Test",
            is_ice=True,
        )
        status = evaluator.determine_status(results, is_ice=True)
        assert status == VerifyStatus.FAIL

    def test_scoring_fail_on_core_failure(self, evaluator: ChecklistEvaluator) -> None:
        """Test FAIL status when core requirement fails."""
        results = evaluator.evaluate(
            "A process is a process.",  # Circular
            "Process",
            is_ice=False,
        )
        status = evaluator.determine_status(results, is_ice=False)
        assert status == VerifyStatus.FAIL

    def test_scoring_fail_on_ice_failure(self, evaluator: ChecklistEvaluator) -> None:
        """Test FAIL status when ICE requirement fails."""
        results = evaluator.evaluate(
            "An entity that does something",  # Not ICE pattern
            "Test ICE",
            is_ice=True,
        )
        status = evaluator.determine_status(results, is_ice=True)
        assert status == VerifyStatus.FAIL

    def test_scoring_iterate_on_quality_failure(
        self, evaluator: ChecklistEvaluator
    ) -> None:
        """Test ITERATE status when only quality fails."""
        # Short definition that passes core but fails Q1 (length)
        results = evaluator.evaluate(
            "A thing that is.",  # Too short (Q1 fails), but non-standard term (Q3 fails)
            "Continuant",
            is_ice=False,
        )
        status = evaluator.determine_status(results, is_ice=False)
        # Should be ITERATE because only quality checks fail
        assert status == VerifyStatus.ITERATE


class TestModelSerialization:
    """Test model serialization/deserialization."""

    def test_check_result_json_roundtrip(self) -> None:
        """Test CheckResult serializes to JSON and back correctly."""
        from ontoralph.core.models import CheckResult

        original = CheckResult(
            code="R1",
            name="No process verbs",
            passed=False,
            evidence="Found process verbs: extracted",
            severity=Severity.RED_FLAG,
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        restored = CheckResult.model_validate_json(json_str)

        assert restored.code == original.code
        assert restored.name == original.name
        assert restored.passed == original.passed
        assert restored.evidence == original.evidence
        assert restored.severity == original.severity

    def test_class_info_json_roundtrip(self) -> None:
        """Test ClassInfo serializes to JSON and back correctly."""
        from ontoralph.core.models import ClassInfo

        original = ClassInfo(
            iri=":VerbPhrase",
            label="Verb Phrase",
            parent_class="cco:InformationContentEntity",
            sibling_classes=[":NounPhrase", ":DiscourseReferent"],
            is_ice=True,
            current_definition="An ICE representing a verb phrase.",
        )

        json_str = original.model_dump_json()
        restored = ClassInfo.model_validate_json(json_str)

        assert restored.iri == original.iri
        assert restored.label == original.label
        assert restored.parent_class == original.parent_class
        assert restored.sibling_classes == original.sibling_classes
        assert restored.is_ice == original.is_ice
        assert restored.current_definition == original.current_definition

    def test_loop_state_json_roundtrip(self) -> None:
        """Test LoopState serializes to JSON and back correctly."""
        from ontoralph.core.models import ClassInfo, LoopState

        class_info = ClassInfo(
            iri=":Test",
            label="Test",
            parent_class="bfo:Entity",
            is_ice=False,
        )

        original = LoopState(
            class_info=class_info,
            max_iterations=5,
        )

        json_str = original.model_dump_json()
        restored = LoopState.model_validate_json(json_str)

        assert restored.class_info.iri == original.class_info.iri
        assert restored.max_iterations == original.max_iterations


# Parametrized test from implementation plan
@pytest.mark.parametrize(
    "definition,expected_flags",
    [
        ("An ICE extracted from text", ["R1"]),
        ("An ICE that represents meaning", ["R2"]),
        ("An ICE that serves to link entities", ["R3"]),
        ("An ICE encoded as a noun phrase", ["R4"]),
        (
            "An ICE extracted from text that represents a verb phrase",
            ["R1", "R2", "R4"],
        ),
        ("An ICE that denotes an occurrent", []),  # Clean
    ],
)
def test_red_flag_detection_parametrized(
    definition: str, expected_flags: list[str]
) -> None:
    """Parametrized test from implementation plan Appendix B."""
    detector = RedFlagDetector()
    results = detector.check(definition)
    failed_codes = [r.code for r in results if not r.passed]
    assert sorted(failed_codes) == sorted(expected_flags)
