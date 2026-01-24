"""Tests for the output generation module.

This module tests:
- TurtleGenerator: Turtle syntax generation
- TurtleValidation: rdflib-based validation
- TurtleDiff: Definition comparison
- ReportGenerator: Markdown/HTML/JSON reports
- BatchReportGenerator: Multi-result reports
"""

import json
from datetime import datetime, timedelta

import pytest
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from ontoralph.core.models import (
    CheckResult,
    ClassInfo,
    LoopIteration,
    LoopResult,
    Severity,
    VerifyStatus,
)
from ontoralph.output import (
    BatchReportGenerator,
    ReportGenerator,
    TurtleDiff,
    TurtleGenerator,
    TurtleValidationError,
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
def sample_definition() -> str:
    return "An ICE that denotes a phrase headed by a verb in formal discourse."


@pytest.fixture
def sample_check_results() -> list[CheckResult]:
    return [
        CheckResult(
            code="C1",
            name="Genus present",
            passed=True,
            evidence="Has genus 'ICE'",
            severity=Severity.REQUIRED,
        ),
        CheckResult(
            code="C2",
            name="Differentia present",
            passed=True,
            evidence="Has differentiating characteristics",
            severity=Severity.REQUIRED,
        ),
        CheckResult(
            code="R1",
            name="No process verbs",
            passed=True,
            evidence="No process verbs found",
            severity=Severity.RED_FLAG,
        ),
        CheckResult(
            code="I1",
            name="ICE pattern start",
            passed=True,
            evidence="Starts with 'An ICE'",
            severity=Severity.ICE_REQUIRED,
        ),
    ]


@pytest.fixture
def sample_iteration(
    sample_definition: str, sample_check_results: list[CheckResult]
) -> LoopIteration:
    return LoopIteration(
        iteration_number=1,
        generated_definition=sample_definition,
        critique_results=sample_check_results,
        verify_status=VerifyStatus.PASS,
        timestamp=datetime.now(),
    )


@pytest.fixture
def sample_loop_result(
    sample_class_info: ClassInfo,
    sample_definition: str,
    sample_iteration: LoopIteration,
) -> LoopResult:
    started = datetime.now() - timedelta(seconds=2)
    return LoopResult(
        class_info=sample_class_info,
        final_definition=sample_definition,
        status=VerifyStatus.PASS,
        iterations=[sample_iteration],
        total_iterations=1,
        started_at=started,
        completed_at=datetime.now(),
    )


@pytest.fixture
def multi_iteration_result(
    sample_class_info: ClassInfo,
    sample_check_results: list[CheckResult],
) -> LoopResult:
    """Result with multiple iterations showing refinement."""
    started = datetime.now() - timedelta(seconds=5)

    iterations = [
        LoopIteration(
            iteration_number=1,
            generated_definition="An ICE that represents a verb phrase.",
            critique_results=[
                CheckResult(
                    code="R2",
                    name="Uses 'denotes' not 'represents'",
                    passed=False,
                    evidence="Found 'represents'",
                    severity=Severity.RED_FLAG,
                ),
            ],
            verify_status=VerifyStatus.FAIL,
            timestamp=started + timedelta(seconds=1),
        ),
        LoopIteration(
            iteration_number=2,
            generated_definition="An ICE that denotes a phrase headed by a verb.",
            critique_results=sample_check_results,
            verify_status=VerifyStatus.PASS,
            timestamp=started + timedelta(seconds=3),
        ),
    ]

    return LoopResult(
        class_info=sample_class_info,
        final_definition="An ICE that denotes a phrase headed by a verb.",
        status=VerifyStatus.PASS,
        iterations=iterations,
        total_iterations=2,
        started_at=started,
        completed_at=datetime.now(),
    )


class TestTurtleGenerator:
    """Tests for TurtleGenerator."""

    def test_generate_basic(
        self, sample_class_info: ClassInfo, sample_definition: str
    ) -> None:
        """Test basic Turtle generation."""
        generator = TurtleGenerator()
        turtle = generator.generate(sample_class_info, sample_definition)

        assert "owl:Class" in turtle or "a owl:Class" in turtle
        assert "Verb Phrase" in turtle
        assert sample_definition in turtle

    def test_generated_turtle_parses(
        self, sample_class_info: ClassInfo, sample_definition: str
    ) -> None:
        """Test that generated Turtle parses without errors (AC5.1)."""
        generator = TurtleGenerator()
        turtle = generator.generate(sample_class_info, sample_definition)

        # Parse with rdflib
        graph = Graph()
        graph.parse(data=turtle, format="turtle")

        # Should have triples
        assert len(graph) > 0

    def test_generated_turtle_has_correct_triples(
        self, sample_class_info: ClassInfo, sample_definition: str
    ) -> None:
        """Test that generated Turtle contains expected triples."""
        generator = TurtleGenerator()
        turtle = generator.generate(sample_class_info, sample_definition)

        graph = Graph()
        graph.parse(data=turtle, format="turtle")

        # Find the class subject
        classes = list(graph.subjects(RDF.type, OWL.Class))
        assert len(classes) == 1

        class_uri = classes[0]

        # Check label
        labels = list(graph.objects(class_uri, RDFS.label))
        assert len(labels) == 1
        assert str(labels[0]) == "Verb Phrase"

        # Check definition
        definitions = list(graph.objects(class_uri, SKOS.definition))
        assert len(definitions) == 1
        assert str(definitions[0]) == sample_definition

        # Check subClassOf
        parents = list(graph.objects(class_uri, RDFS.subClassOf))
        assert len(parents) == 1

    def test_generate_non_ice(
        self, non_ice_class_info: ClassInfo
    ) -> None:
        """Test Turtle generation for non-ICE class."""
        generator = TurtleGenerator()
        definition = "An occurrent that unfolds through temporal extension."
        turtle = generator.generate(non_ice_class_info, definition)

        # Should parse
        graph = Graph()
        graph.parse(data=turtle, format="turtle")
        assert len(graph) > 0

    def test_generate_with_special_characters(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test that definitions with special characters are properly escaped."""
        generator = TurtleGenerator()
        # Definition with quotes and special chars
        definition = 'An ICE that denotes a "phrase" with special chars: <>&'

        turtle = generator.generate(sample_class_info, definition)

        # Should parse without errors
        graph = Graph()
        graph.parse(data=turtle, format="turtle")

        # Definition should be retrievable
        definitions = list(graph.objects(predicate=SKOS.definition))
        assert len(definitions) == 1

    def test_generate_multiline_definition(
        self, sample_class_info: ClassInfo
    ) -> None:
        """Test multi-line definitions use correct escaping (AC5.3)."""
        generator = TurtleGenerator()
        # Multi-line definition
        definition = (
            "An ICE that denotes a phrase headed by a verb.\n"
            "This phrase typically expresses an action or state."
        )

        turtle = generator.generate(sample_class_info, definition)

        # Should parse
        graph = Graph()
        graph.parse(data=turtle, format="turtle")

        # Definition should be preserved
        definitions = list(graph.objects(predicate=SKOS.definition))
        assert len(definitions) == 1

    def test_generate_batch(self) -> None:
        """Test batch generation of multiple classes."""
        generator = TurtleGenerator()

        classes = [
            (
                ClassInfo(
                    iri=":ClassA",
                    label="Class A",
                    parent_class="owl:Thing",
                    is_ice=False,
                ),
                "Definition for Class A.",
            ),
            (
                ClassInfo(
                    iri=":ClassB",
                    label="Class B",
                    parent_class="owl:Thing",
                    is_ice=False,
                ),
                "Definition for Class B.",
            ),
        ]

        turtle = generator.generate_batch(classes)

        # Should parse
        graph = Graph()
        graph.parse(data=turtle, format="turtle")

        # Should have 2 classes
        class_count = len(list(graph.subjects(RDF.type, OWL.Class)))
        assert class_count == 2

    def test_generate_from_result(
        self, sample_loop_result: LoopResult
    ) -> None:
        """Test generation from LoopResult."""
        generator = TurtleGenerator()
        turtle = generator.generate_from_result(sample_loop_result)

        # Should parse
        graph = Graph()
        graph.parse(data=turtle, format="turtle")
        assert len(graph) > 0

    def test_generate_with_custom_base_namespace(
        self, sample_class_info: ClassInfo, sample_definition: str
    ) -> None:
        """Test custom base namespace."""
        generator = TurtleGenerator(
            base_namespace="http://myontology.org/classes#"
        )
        turtle = generator.generate(sample_class_info, sample_definition)

        assert "http://myontology.org/classes#" in turtle

    def test_generate_without_comments(
        self, sample_class_info: ClassInfo, sample_definition: str
    ) -> None:
        """Test generation without header comments."""
        generator = TurtleGenerator(include_comments=False)
        turtle = generator.generate(sample_class_info, sample_definition)

        # Should not have OntoRalph header comment
        assert "# OntoRalph" not in turtle

    def test_generate_prefixes(self) -> None:
        """Test prefix generation."""
        generator = TurtleGenerator()
        prefixes = generator.generate_prefixes()

        assert "@prefix owl:" in prefixes
        assert "@prefix rdfs:" in prefixes
        assert "@prefix skos:" in prefixes
        assert "@prefix cco:" in prefixes


class TestTurtleValidation:
    """Tests for Turtle validation."""

    def test_validate_valid_turtle(self) -> None:
        """Test validation of valid Turtle."""
        generator = TurtleGenerator()
        valid_turtle = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        <http://example.org/Class> a owl:Class ;
            rdfs:label "Test Class" .
        """

        is_valid, error = generator.validate(valid_turtle)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_turtle(self) -> None:
        """Test validation of invalid Turtle."""
        generator = TurtleGenerator()
        invalid_turtle = """
        This is not valid Turtle syntax at all {{{
        """

        is_valid, error = generator.validate(invalid_turtle)
        assert is_valid is False
        assert error is not None

    def test_validate_or_raise_valid(self) -> None:
        """Test validate_or_raise with valid Turtle."""
        generator = TurtleGenerator()
        valid_turtle = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <http://example.org/Class> a owl:Class .
        """

        graph = generator.validate_or_raise(valid_turtle)
        assert isinstance(graph, Graph)
        assert len(graph) > 0

    def test_validate_or_raise_invalid(self) -> None:
        """Test validate_or_raise with invalid Turtle."""
        generator = TurtleGenerator()
        invalid_turtle = "not valid {{{ turtle"

        with pytest.raises(TurtleValidationError):
            generator.validate_or_raise(invalid_turtle)


class TestTurtleDiff:
    """Tests for TurtleDiff."""

    def test_diff_identical(self) -> None:
        """Test diff of identical definitions."""
        differ = TurtleDiff()
        definition = "An ICE that denotes something."

        diff = differ.diff(definition, definition)

        assert diff["changed"] is False
        assert diff["similarity"] == 1.0
        assert len(diff["added_words"]) == 0
        assert len(diff["removed_words"]) == 0

    def test_diff_different(self) -> None:
        """Test diff of different definitions."""
        differ = TurtleDiff()
        old = "An ICE that represents something."
        new = "An ICE that denotes something else."

        diff = differ.diff(old, new)

        assert diff["changed"] is True
        assert "represents" in diff["removed_words"]
        assert "denotes" in diff["added_words"]
        assert "else." in diff["added_words"]

    def test_format_diff_text_no_changes(self) -> None:
        """Test text diff format with no changes."""
        differ = TurtleDiff()
        definition = "An ICE that denotes something."

        text = differ.format_diff_text(definition, definition)

        assert "(no changes)" in text

    def test_format_diff_text_with_changes(self) -> None:
        """Test text diff format with changes."""
        differ = TurtleDiff()
        old = "An ICE that represents something."
        new = "An ICE that denotes something."

        text = differ.format_diff_text(old, new)

        assert "Removed:" in text
        assert "Added:" in text
        assert "represents" in text
        assert "denotes" in text


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generate_markdown(
        self, sample_loop_result: LoopResult
    ) -> None:
        """Test Markdown report generation."""
        generator = ReportGenerator()
        markdown = generator.generate_markdown(sample_loop_result)

        # Check structure
        assert "# Ralph Loop Report:" in markdown
        assert "## Summary" in markdown
        assert "## Class Information" in markdown
        assert "## Final Definition" in markdown
        assert "## Iteration History" in markdown

        # Check content
        assert "Verb Phrase" in markdown
        assert ":VerbPhrase" in markdown
        assert "PASS" in markdown

    def test_generate_markdown_shows_iteration_progression(
        self, multi_iteration_result: LoopResult
    ) -> None:
        """Test that report shows iteration progression (AC5.4)."""
        generator = ReportGenerator()
        markdown = generator.generate_markdown(multi_iteration_result)

        # Should show both iterations
        assert "### Iteration 1" in markdown
        assert "### Iteration 2" in markdown

        # Should show evolution section
        assert "## Definition Evolution" in markdown

    def test_generate_summary(
        self, sample_loop_result: LoopResult
    ) -> None:
        """Test summary generation."""
        generator = ReportGenerator()
        summary = generator.generate_summary(sample_loop_result)

        assert "Verb Phrase" in summary
        assert "PASS" in summary
        assert "1 iteration" in summary

    def test_generate_json(
        self, sample_loop_result: LoopResult
    ) -> None:
        """Test JSON report generation."""
        generator = ReportGenerator()
        json_str = generator.generate_json(sample_loop_result)

        # Should be valid JSON
        data = json.loads(json_str)

        assert data["class_info"]["iri"] == ":VerbPhrase"
        assert data["status"] == "pass"
        assert data["converged"] is True
        assert data["total_iterations"] == 1
        assert len(data["iterations"]) == 1

    def test_json_roundtrip(
        self, sample_loop_result: LoopResult
    ) -> None:
        """Test that JSON output can reconstruct loop history (AC5.5)."""
        generator = ReportGenerator()
        json_str = generator.generate_json(sample_loop_result)

        # Parse JSON
        data = json.loads(json_str)

        # Verify we can reconstruct key information
        assert data["class_info"]["iri"] == sample_loop_result.class_info.iri
        assert data["final_definition"] == sample_loop_result.final_definition
        assert data["total_iterations"] == sample_loop_result.total_iterations

        # Verify iteration data
        for i, iteration_data in enumerate(data["iterations"]):
            original = sample_loop_result.iterations[i]
            assert iteration_data["iteration_number"] == original.iteration_number
            assert iteration_data["generated_definition"] == original.generated_definition
            assert iteration_data["verify_status"] == original.verify_status.value

            # Verify check results
            for j, check_data in enumerate(iteration_data["critique_results"]):
                original_check = original.critique_results[j]
                assert check_data["code"] == original_check.code
                assert check_data["passed"] == original_check.passed

    def test_generate_html(
        self, sample_loop_result: LoopResult
    ) -> None:
        """Test HTML report generation."""
        generator = ReportGenerator()
        html = generator.generate_html(sample_loop_result)

        # Check HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "<style>" in html
        assert "</html>" in html

        # Check content
        assert "Verb Phrase" in html
        assert "PASS" in html

    def test_report_without_timestamps(
        self, sample_loop_result: LoopResult
    ) -> None:
        """Test report generation without timestamps."""
        generator = ReportGenerator(include_timestamps=False)
        markdown = generator.generate_markdown(sample_loop_result)

        # Should not include started/completed timestamps in summary
        assert "Started:" not in markdown

    def test_report_failed_checks_only(
        self, multi_iteration_result: LoopResult
    ) -> None:
        """Test showing only failed checks."""
        generator = ReportGenerator(show_all_checks=False)
        markdown = generator.generate_markdown(multi_iteration_result)

        # In iteration 1, R2 failed - should be shown
        assert "R2" in markdown


class TestBatchReportGenerator:
    """Tests for BatchReportGenerator."""

    @pytest.fixture
    def batch_results(
        self, sample_class_info: ClassInfo, sample_check_results: list[CheckResult]
    ) -> list[LoopResult]:
        """Create multiple results for batch testing."""
        started = datetime.now() - timedelta(seconds=5)

        # Passing result
        passing = LoopResult(
            class_info=sample_class_info,
            final_definition="An ICE that denotes a phrase headed by a verb.",
            status=VerifyStatus.PASS,
            iterations=[
                LoopIteration(
                    iteration_number=1,
                    generated_definition="An ICE that denotes a phrase headed by a verb.",
                    critique_results=sample_check_results,
                    verify_status=VerifyStatus.PASS,
                    timestamp=started + timedelta(seconds=1),
                )
            ],
            total_iterations=1,
            started_at=started,
            completed_at=started + timedelta(seconds=2),
        )

        # Failing result
        failing_class = ClassInfo(
            iri=":FailingClass",
            label="Failing Class",
            parent_class="owl:Thing",
            is_ice=False,
        )
        failing = LoopResult(
            class_info=failing_class,
            final_definition="A thing that represents something.",
            status=VerifyStatus.FAIL,
            iterations=[
                LoopIteration(
                    iteration_number=1,
                    generated_definition="A thing that represents something.",
                    critique_results=[
                        CheckResult(
                            code="R2",
                            name="Uses 'denotes' not 'represents'",
                            passed=False,
                            evidence="Found 'represents'",
                            severity=Severity.RED_FLAG,
                        )
                    ],
                    verify_status=VerifyStatus.FAIL,
                    timestamp=started + timedelta(seconds=3),
                )
            ],
            total_iterations=1,
            started_at=started + timedelta(seconds=2),
            completed_at=started + timedelta(seconds=4),
        )

        return [passing, failing]

    def test_generate_summary_markdown(
        self, batch_results: list[LoopResult]
    ) -> None:
        """Test batch summary markdown generation."""
        generator = BatchReportGenerator()
        markdown = generator.generate_summary_markdown(batch_results)

        # Check statistics
        assert "## Statistics" in markdown
        assert "**Total Classes**: 2" in markdown
        assert "**Passed**: 1" in markdown
        assert "**Failed**: 1" in markdown

        # Check results table
        assert "| Class | Status | Iterations | Duration |" in markdown

        # Check failed classes section
        assert "## Failed Classes" in markdown
        assert "Failing Class" in markdown

    def test_generate_json(
        self, batch_results: list[LoopResult]
    ) -> None:
        """Test batch JSON generation."""
        generator = BatchReportGenerator()
        json_str = generator.generate_json(batch_results)

        data = json.loads(json_str)

        assert data["summary"]["total"] == 2
        assert data["summary"]["passed"] == 1
        assert data["summary"]["failed"] == 1
        assert len(data["results"]) == 2


class TestIntegration:
    """Integration tests for output generation."""

    def test_full_pipeline(
        self, sample_class_info: ClassInfo, sample_definition: str
    ) -> None:
        """Test complete output generation pipeline."""
        # Generate Turtle
        turtle_gen = TurtleGenerator()
        turtle = turtle_gen.generate(sample_class_info, sample_definition)

        # Validate Turtle
        is_valid, error = turtle_gen.validate(turtle)
        assert is_valid is True

        # Parse and verify
        graph = Graph()
        graph.parse(data=turtle, format="turtle")
        assert len(graph) > 0

    def test_roundtrip_50_definitions(self) -> None:
        """Test that generated Turtle parses for many definitions (AC5.1)."""
        generator = TurtleGenerator()

        definitions = [
            f"An ICE that denotes concept number {i} in the ontology."
            for i in range(50)
        ]

        for i, definition in enumerate(definitions):
            class_info = ClassInfo(
                iri=f":Concept{i}",
                label=f"Concept {i}",
                parent_class="owl:Thing",
                is_ice=True,
            )

            turtle = generator.generate(class_info, definition)

            # All should parse
            graph = Graph()
            graph.parse(data=turtle, format="turtle")
            assert len(graph) > 0

    def test_definitions_with_quotes(self) -> None:
        """Test definitions containing various quote types."""
        generator = TurtleGenerator()

        definitions = [
            'An ICE that denotes a "quoted term".',
            "An ICE that denotes a term with 'single quotes'.",
            'An ICE that "uses" both \'quote\' types.',
            "An ICE with special chars: <>&",
        ]

        for i, definition in enumerate(definitions):
            class_info = ClassInfo(
                iri=f":QuoteTest{i}",
                label=f"Quote Test {i}",
                parent_class="owl:Thing",
                is_ice=True,
            )

            turtle = generator.generate(class_info, definition)

            # Should parse
            graph = Graph()
            graph.parse(data=turtle, format="turtle")

            # Definition should be in graph
            defs = list(graph.objects(predicate=SKOS.definition))
            assert len(defs) == 1
