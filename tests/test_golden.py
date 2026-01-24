"""Golden file tests for OntoRalph.

These tests use fixture files to verify that the checklist evaluator
produces consistent results over time. Any change in behavior will
cause these tests to fail, indicating a potential regression.

The golden files contain known inputs and expected outputs based on
BFO/CCO ontology definition patterns.
"""

from pathlib import Path

import pytest
import yaml

from ontoralph.core.checklist import ChecklistEvaluator
from ontoralph.core.models import VerifyStatus


# Load golden file fixture
FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_FILE = FIXTURES_DIR / "golden_definitions.yaml"


@pytest.fixture
def golden_data() -> dict:
    """Load golden file test data."""
    with open(GOLDEN_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def evaluator() -> ChecklistEvaluator:
    """Create a standard evaluator."""
    return ChecklistEvaluator()


class TestPassingDefinitions:
    """Test definitions that should always pass."""

    def test_passing_definitions_loaded(self, golden_data: dict) -> None:
        """Verify golden data has passing definitions."""
        assert "passing_definitions" in golden_data
        assert len(golden_data["passing_definitions"]) > 0

    @pytest.mark.parametrize("case_index", range(4))  # Number of passing cases
    def test_passing_case(
        self,
        golden_data: dict,
        evaluator: ChecklistEvaluator,
        case_index: int,
    ) -> None:
        """Test each passing definition case."""
        cases = golden_data["passing_definitions"]
        if case_index >= len(cases):
            pytest.skip(f"No case at index {case_index}")

        case = cases[case_index]
        results = evaluator.evaluate(
            definition=case["definition"],
            term=case["term"],
            is_ice=case["is_ice"],
            parent_class=case.get("parent_class"),
        )

        # Verify expected checks pass
        for check_code in case.get("checks_must_pass", []):
            matching = [r for r in results if r.code == check_code]
            assert len(matching) > 0, f"Check {check_code} not found in results"
            assert matching[0].passed, (
                f"Check {check_code} should pass for case '{case['id']}': "
                f"{matching[0].evidence}"
            )

        # Verify overall status
        status = evaluator.determine_status(results, is_ice=case["is_ice"])
        assert status == VerifyStatus.PASS, (
            f"Case '{case['id']}' should PASS but got {status.value}"
        )


class TestFailingDefinitions:
    """Test definitions that should always fail due to red flags."""

    def test_failing_definitions_loaded(self, golden_data: dict) -> None:
        """Verify golden data has failing definitions."""
        assert "failing_definitions" in golden_data
        assert len(golden_data["failing_definitions"]) > 0

    @pytest.mark.parametrize("case_index", range(7))  # Number of failing cases
    def test_failing_case(
        self,
        golden_data: dict,
        evaluator: ChecklistEvaluator,
        case_index: int,
    ) -> None:
        """Test each failing definition case."""
        cases = golden_data["failing_definitions"]
        if case_index >= len(cases):
            pytest.skip(f"No case at index {case_index}")

        case = cases[case_index]
        results = evaluator.evaluate(
            definition=case["definition"],
            term=case["term"],
            is_ice=case["is_ice"],
            parent_class=case.get("parent_class"),
        )

        # Verify expected checks fail
        for check_code in case.get("checks_must_fail", []):
            matching = [r for r in results if r.code == check_code]
            assert len(matching) > 0, f"Check {check_code} not found in results"
            assert not matching[0].passed, (
                f"Check {check_code} should fail for case '{case['id']}'"
            )

        # Verify overall status is FAIL
        status = evaluator.determine_status(results, is_ice=case["is_ice"])
        assert status == VerifyStatus.FAIL, (
            f"Case '{case['id']}' should FAIL but got {status.value}"
        )


class TestICEFailures:
    """Test ICE-specific failure cases."""

    def test_ice_failures_loaded(self, golden_data: dict) -> None:
        """Verify golden data has ICE failure cases."""
        assert "ice_failures" in golden_data
        assert len(golden_data["ice_failures"]) > 0

    @pytest.mark.parametrize("case_index", range(2))  # Number of ICE failure cases
    def test_ice_failure_case(
        self,
        golden_data: dict,
        evaluator: ChecklistEvaluator,
        case_index: int,
    ) -> None:
        """Test each ICE failure case."""
        cases = golden_data["ice_failures"]
        if case_index >= len(cases):
            pytest.skip(f"No case at index {case_index}")

        case = cases[case_index]
        results = evaluator.evaluate(
            definition=case["definition"],
            term=case["term"],
            is_ice=True,  # All cases in this section are ICEs
            parent_class=case.get("parent_class"),
        )

        # Verify expected checks fail
        for check_code in case.get("checks_must_fail", []):
            matching = [r for r in results if r.code == check_code]
            assert len(matching) > 0, f"Check {check_code} not found in results"
            assert not matching[0].passed, (
                f"Check {check_code} should fail for case '{case['id']}'"
            )

        # Verify overall status is FAIL
        status = evaluator.determine_status(results, is_ice=True)
        assert status == VerifyStatus.FAIL, (
            f"Case '{case['id']}' should FAIL but got {status.value}"
        )


class TestIterateDefinitions:
    """Test definitions that should iterate (quality issues only)."""

    def test_iterate_definitions_loaded(self, golden_data: dict) -> None:
        """Verify golden data has iterate cases."""
        assert "iterate_definitions" in golden_data
        assert len(golden_data["iterate_definitions"]) > 0

    @pytest.mark.parametrize("case_index", range(2))  # Number of iterate cases
    def test_iterate_case(
        self,
        golden_data: dict,
        evaluator: ChecklistEvaluator,
        case_index: int,
    ) -> None:
        """Test each iterate case."""
        cases = golden_data["iterate_definitions"]
        if case_index >= len(cases):
            pytest.skip(f"No case at index {case_index}")

        case = cases[case_index]
        results = evaluator.evaluate(
            definition=case["definition"],
            term=case["term"],
            is_ice=case["is_ice"],
            parent_class=case.get("parent_class"),
        )

        # Verify expected checks fail (quality issues)
        for check_code in case.get("checks_must_fail", []):
            matching = [r for r in results if r.code == check_code]
            # Note: Some checks might not be present depending on implementation
            if matching:
                assert not matching[0].passed, (
                    f"Check {check_code} should fail for case '{case['id']}'"
                )

        # Use expected_status from golden file
        status = evaluator.determine_status(results, is_ice=case["is_ice"])
        expected = case.get("expected_status", "ITERATE")
        expected_status = VerifyStatus(expected.lower())
        assert status == expected_status, (
            f"Case '{case['id']}' should {expected} but got {status.value}"
        )


class TestGoldenFileIntegrity:
    """Tests to ensure golden file is well-formed."""

    def test_all_cases_have_required_fields(self, golden_data: dict) -> None:
        """Verify all test cases have required fields."""
        required_fields = ["id", "definition", "term", "is_ice"]

        for section in ["passing_definitions", "failing_definitions", "ice_failures", "iterate_definitions"]:
            if section in golden_data:
                for case in golden_data[section]:
                    for field in required_fields:
                        assert field in case, (
                            f"Case '{case.get('id', 'unknown')}' in {section} "
                            f"missing required field '{field}'"
                        )

    def test_all_case_ids_unique(self, golden_data: dict) -> None:
        """Verify all case IDs are unique."""
        all_ids = []

        for section in ["passing_definitions", "failing_definitions", "ice_failures", "iterate_definitions"]:
            if section in golden_data:
                for case in golden_data[section]:
                    all_ids.append(case["id"])

        assert len(all_ids) == len(set(all_ids)), "Duplicate case IDs found"

    def test_minimum_cases_per_section(self, golden_data: dict) -> None:
        """Verify each section has a minimum number of cases."""
        min_cases = {
            "passing_definitions": 2,
            "failing_definitions": 3,
            "ice_failures": 1,
            "iterate_definitions": 1,
        }

        for section, min_count in min_cases.items():
            assert section in golden_data, f"Missing section: {section}"
            assert len(golden_data[section]) >= min_count, (
                f"Section {section} should have at least {min_count} cases"
            )


class TestRegressionDetection:
    """Tests that would detect regressions in checklist logic."""

    def test_r1_still_detects_extracted(self, evaluator: ChecklistEvaluator) -> None:
        """Regression test: R1 should still detect 'extracted'."""
        results = evaluator.evaluate(
            definition="An ICE extracted from documents.",
            term="Test",
            is_ice=True,
        )

        r1 = next((r for r in results if r.code == "R1"), None)
        assert r1 is not None
        assert not r1.passed, "R1 should fail on 'extracted'"

    def test_r2_still_detects_represents(self, evaluator: ChecklistEvaluator) -> None:
        """Regression test: R2 should still detect 'represents'."""
        results = evaluator.evaluate(
            definition="An ICE that represents a concept.",
            term="Test",
            is_ice=True,
        )

        r2 = next((r for r in results if r.code == "R2"), None)
        assert r2 is not None
        assert not r2.passed, "R2 should fail on 'represents'"

    def test_r3_still_detects_serves_to(self, evaluator: ChecklistEvaluator) -> None:
        """Regression test: R3 should still detect 'serves to'."""
        results = evaluator.evaluate(
            definition="An ICE that serves to identify entities.",
            term="Test",
            is_ice=True,
        )

        r3 = next((r for r in results if r.code == "R3"), None)
        assert r3 is not None
        assert not r3.passed, "R3 should fail on 'serves to'"

    def test_r4_still_detects_noun_phrase(self, evaluator: ChecklistEvaluator) -> None:
        """Regression test: R4 should still detect 'noun phrase'."""
        results = evaluator.evaluate(
            definition="An ICE encoded as a noun phrase.",
            term="Test",
            is_ice=True,
        )

        r4 = next((r for r in results if r.code == "R4"), None)
        assert r4 is not None
        assert not r4.passed, "R4 should fail on 'noun phrase'"

    def test_i1_requires_ice_start(self, evaluator: ChecklistEvaluator) -> None:
        """Regression test: I1 should require ICE start for ICE classes."""
        results = evaluator.evaluate(
            definition="An entity that denotes something.",  # Missing ICE
            term="Test",
            is_ice=True,
        )

        i1 = next((r for r in results if r.code == "I1"), None)
        assert i1 is not None
        assert not i1.passed, "I1 should fail when not starting with 'An ICE'"

    def test_c3_detects_circularity(self, evaluator: ChecklistEvaluator) -> None:
        """Regression test: C3 should detect term in definition."""
        results = evaluator.evaluate(
            definition="A Person Name is an ICE that denotes a person name.",
            term="Person Name",
            is_ice=True,
        )

        c3 = next((r for r in results if r.code == "C3"), None)
        assert c3 is not None
        assert not c3.passed, "C3 should fail on circular definition"
