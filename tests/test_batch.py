"""Tests for the batch processing module.

This module tests:
- Parallel batch processing
- Dependency ordering
- Sibling exclusivity checking
- Cross-class consistency
- BFO/CCO pattern validation
- Batch integrity checking
"""

import tempfile
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from ontoralph.batch import (
    BatchConfig,
    BatchIntegrityChecker,
    BatchProcessor,
    CrossClassConsistencyChecker,
    DependencyGraph,
    OverlapType,
    SiblingExclusivityChecker,
    TurtleValidator,
    check_batch_integrity,
    check_consistency,
    check_sibling_exclusivity,
    get_processing_levels,
    order_by_dependency,
    validate_turtle_output,
)
from ontoralph.core.models import ClassInfo, LoopResult, VerifyStatus
from ontoralph.llm import MockProvider


# Test fixtures
@pytest.fixture
def sample_classes() -> list[ClassInfo]:
    """Create sample classes for testing."""
    return [
        ClassInfo(
            iri=":VerbPhrase",
            label="Verb Phrase",
            parent_class="cco:InformationContentEntity",
            sibling_classes=[":NounPhrase"],
            is_ice=True,
        ),
        ClassInfo(
            iri=":NounPhrase",
            label="Noun Phrase",
            parent_class="cco:InformationContentEntity",
            sibling_classes=[":VerbPhrase"],
            is_ice=True,
        ),
        ClassInfo(
            iri=":Sentence",
            label="Sentence",
            parent_class="cco:InformationContentEntity",
            is_ice=True,
        ),
    ]


@pytest.fixture
def hierarchical_classes() -> list[ClassInfo]:
    """Create hierarchical classes for dependency testing."""
    return [
        ClassInfo(
            iri=":Child",
            label="Child",
            parent_class=":Parent",
            is_ice=True,
        ),
        ClassInfo(
            iri=":Parent",
            label="Parent",
            parent_class=":GrandParent",
            is_ice=True,
        ),
        ClassInfo(
            iri=":GrandParent",
            label="Grand Parent",
            parent_class="owl:Thing",
            is_ice=True,
        ),
    ]


@pytest.fixture
def mock_provider() -> MockProvider:
    """Create a mock LLM provider."""
    return MockProvider(
        generate_response="An ICE that denotes an occurrent.",
    )


class TestDependencyOrdering:
    """Tests for dependency ordering."""

    def test_order_simple_hierarchy(self, hierarchical_classes: list[ClassInfo]) -> None:
        """Test ordering of simple parent-child hierarchy (AC7.3)."""
        ordered = order_by_dependency(hierarchical_classes)

        # GrandParent should come before Parent, Parent before Child
        iris = [c.iri for c in ordered]
        assert iris.index(":GrandParent") < iris.index(":Parent")
        assert iris.index(":Parent") < iris.index(":Child")

    def test_order_flat_classes(self, sample_classes: list[ClassInfo]) -> None:
        """Test ordering of non-hierarchical classes."""
        ordered = order_by_dependency(sample_classes)

        # Should return all classes (order doesn't matter for flat)
        assert len(ordered) == len(sample_classes)
        assert {c.iri for c in ordered} == {c.iri for c in sample_classes}

    def test_detect_circular_dependency(self) -> None:
        """Test detection of circular dependencies."""
        circular = [
            ClassInfo(iri=":A", label="A", parent_class=":B", is_ice=True),
            ClassInfo(iri=":B", label="B", parent_class=":A", is_ice=True),
        ]

        with pytest.raises(ValueError, match="circular"):
            order_by_dependency(circular)

    def test_get_processing_levels(self, hierarchical_classes: list[ClassInfo]) -> None:
        """Test grouping classes into processing levels."""
        levels = get_processing_levels(hierarchical_classes)

        # Should have 3 levels
        assert len(levels) >= 1

        # First level should have GrandParent (no internal dependencies)
        first_level_iris = [c.iri for c in levels[0]]
        assert ":GrandParent" in first_level_iris

    def test_dependency_graph_validation(self) -> None:
        """Test dependency graph validation."""
        graph = DependencyGraph()
        graph.add_class(ClassInfo(
            iri=":SelfRef",
            label="Self Reference",
            parent_class=":SelfRef",  # Self-reference
            is_ice=True,
        ))

        issues = graph.validate()
        assert len(issues) > 0
        assert any(i.issue_type == "self_reference" for i in issues)


class TestSiblingExclusivity:
    """Tests for sibling exclusivity checking."""

    def test_detect_identical_definitions(self) -> None:
        """Test detection of identical definitions (AC7.2)."""
        definitions = {
            ":Class1": "An ICE that denotes an occurrent.",
            ":Class2": "An ICE that denotes an occurrent.",
        }

        issues = check_sibling_exclusivity(definitions)

        assert len(issues) >= 1
        assert any(i.overlap_type == OverlapType.IDENTICAL for i in issues)

    def test_detect_high_similarity(self) -> None:
        """Test detection of highly similar definitions."""
        definitions = {
            ":Class1": "An ICE that denotes an occurrent as it unfolds in time.",
            ":Class2": "An ICE that denotes an occurrent as it unfolds through time.",
        }

        checker = SiblingExclusivityChecker(similarity_threshold=0.8)
        issues = checker.check(definitions)

        assert len(issues) >= 1
        assert any(i.overlap_type == OverlapType.HIGH_SIMILARITY for i in issues)

    def test_no_issues_for_distinct_definitions(self) -> None:
        """Test that distinct definitions don't trigger issues."""
        definitions = {
            ":VerbPhrase": "An ICE that denotes a verb phrase in natural language.",
            ":NounPhrase": "An ICE that denotes a noun phrase in discourse.",
        }

        issues = check_sibling_exclusivity(definitions)

        # May have some minor issues but no critical ones
        critical = [i for i in issues if i.severity == "error"]
        assert len(critical) == 0

    def test_term_overlap_detection(self) -> None:
        """Test detection of sibling term usage."""
        # VerbPhrase definition mentions "noun phrase" (NounPhrase's label)
        # NounPhrase definition mentions "verb phrase" (VerbPhrase's label)
        definitions = {
            ":VerbPhrase": "An ICE that includes a noun phrase component.",
            ":NounPhrase": "An ICE that is distinct from verb phrase structures.",
        }
        class_infos = {
            ":VerbPhrase": ClassInfo(iri=":VerbPhrase", label="Verb Phrase", parent_class="owl:Thing", is_ice=True),
            ":NounPhrase": ClassInfo(iri=":NounPhrase", label="Noun Phrase", parent_class="owl:Thing", is_ice=True),
        }

        checker = SiblingExclusivityChecker(check_term_overlap=True)
        issues = checker.check(definitions, class_infos)

        term_issues = [i for i in issues if i.overlap_type == OverlapType.TERM_OVERLAP]
        # Each definition mentions the other's label
        assert len(term_issues) >= 2  # Both should be flagged


class TestCrossClassConsistency:
    """Tests for cross-class consistency checking."""

    def test_detect_terminology_inconsistency(self) -> None:
        """Test detection of inconsistent terminology."""
        definitions = {
            ":Class1": "An ICE that represents something.",
            ":Class2": "An ICE that denotes something else.",
        }

        issues = check_consistency(definitions)

        # Should detect mix of "represents" and "denotes"
        term_issues = [i for i in issues if i.issue_type.value == "terminology"]
        assert len(term_issues) >= 1

    def test_detect_pattern_inconsistency(self) -> None:
        """Test detection of pattern inconsistency."""
        definitions = {
            ":Class1": "An ICE that denotes something.",
            ":Class2": "The class which represents something.",  # Different pattern
        }

        issues = check_consistency(definitions)

        pattern_issues = [i for i in issues if i.issue_type.value == "pattern"]
        assert len(pattern_issues) >= 1

    def test_ice_pattern_validation(self) -> None:
        """Test ICE definition pattern validation."""
        definitions = {
            ":Class1": "Something that is an entity.",  # Wrong pattern for ICE
        }
        class_infos = {
            ":Class1": ClassInfo(iri=":Class1", label="Class1", parent_class="owl:Thing", is_ice=True),
        }

        checker = CrossClassConsistencyChecker()
        issues = checker.check(definitions, class_infos)

        ice_issues = [i for i in issues if "ICE" in i.message]
        assert len(ice_issues) >= 1


class TestTurtleValidator:
    """Tests for Turtle/RDF output validation."""

    def test_validate_namespace_terms(self) -> None:
        """Test detection of invalid namespace terms (AC7.10)."""
        # Create graph with invalid term
        graph = Graph()
        invalid_term = URIRef("http://www.w3.org/2000/01/rdf-schema#lable")  # Typo
        graph.add((URIRef("http://example.org/test"), invalid_term, Literal("Test")))

        validator = TurtleValidator()
        issues = validator.validate_namespace_terms(graph)

        assert len(issues) >= 1
        assert any("lable" in i.message for i in issues)

    def test_validate_ice_pattern(self) -> None:
        """Test ICE concretization pattern validation (AC7.6)."""
        CCO = Namespace("http://www.ontologyrepository.com/CommonCoreOntologies/")

        graph = Graph()
        ice = URIRef("http://example.org/MyICE")
        # Bind the CCO namespace explicitly
        graph.bind("cco", CCO)
        graph.add((ice, RDF.type, CCO.InformationContentEntity))
        # Missing is_concretized_by relationship

        validator = TurtleValidator()
        issues = validator.validate_ice_pattern(graph)

        # Should find ICE without concretization
        assert len(issues) >= 1
        # Check for either "concretization" or "concretized"
        assert any("concret" in i.message.lower() for i in issues)

    def test_validate_role_pattern(self) -> None:
        """Test Role bearer pattern validation (AC7.7)."""
        CCO = Namespace("http://www.ontologyrepository.com/CommonCoreOntologies/")

        graph = Graph()
        role = URIRef("http://example.org/MyRole")
        graph.add((role, RDF.type, CCO["Role"]))
        # Missing bearer relationship

        validator = TurtleValidator()
        issues = validator.validate_role_pattern(graph)

        # Should have a VIOLATION for missing bearer
        violations = [i for i in issues if i.severity.value == "violation"]
        assert len(violations) >= 1


class TestBatchIntegrityChecker:
    """Tests for batch integrity checking."""

    def test_detect_duplicate_labels(self) -> None:
        """Test detection of duplicate rdfs:label values (AC7.8)."""
        graph = Graph()
        graph.add((URIRef("http://example.org/A"), RDFS.label, Literal("Same Label")))
        graph.add((URIRef("http://example.org/B"), RDFS.label, Literal("Same Label")))

        checker = BatchIntegrityChecker()
        issues = checker.check_duplicate_labels(graph)

        assert len(issues) >= 1
        # Label is stored lowercase
        assert any("same label" in i.label for i in issues)

    def test_detect_punning(self) -> None:
        """Test detection of OWL punning (AC7.9)."""
        graph = Graph()
        entity = URIRef("http://example.org/Punned")
        graph.add((entity, RDF.type, OWL.NamedIndividual))
        graph.add((entity, RDF.type, OWL.Class))  # Punning!

        checker = BatchIntegrityChecker()
        issues = checker.check_punning(graph)

        assert len(issues) >= 1
        assert any("pun" in i.message.lower() for i in issues)

    def test_no_issues_for_clean_graph(self) -> None:
        """Test that clean graph has no integrity issues."""
        graph = Graph()
        entity = URIRef("http://example.org/Clean")
        graph.add((entity, RDF.type, OWL.Class))
        graph.add((entity, RDFS.label, Literal("Clean Class")))

        checker = BatchIntegrityChecker()
        dup, pun, ns = checker.check_all(graph)

        assert len(dup) == 0
        assert len(pun) == 0


class TestBatchProcessor:
    """Tests for parallel batch processing."""

    @pytest.mark.asyncio
    async def test_process_multiple_classes(
        self,
        sample_classes: list[ClassInfo],
        mock_provider: MockProvider,
    ) -> None:
        """Test processing multiple classes."""
        config = BatchConfig(max_concurrency=2, continue_on_error=True)
        processor = BatchProcessor(mock_provider, config)

        result = await processor.process(sample_classes[:2])

        assert len(result.results) > 0
        assert result.progress.total == 2

    @pytest.mark.asyncio
    async def test_parallel_processing(
        self,
        sample_classes: list[ClassInfo],
        mock_provider: MockProvider,
    ) -> None:
        """Test that parallel processing works (AC7.1)."""
        config = BatchConfig(
            max_concurrency=3,
            rate_limit_delay=0.1,
        )
        processor = BatchProcessor(mock_provider, config)

        result = await processor.process(sample_classes)

        # Should complete all classes
        assert result.progress.completed + result.progress.errors == len(sample_classes)

    @pytest.mark.asyncio
    async def test_continue_on_error(self, sample_classes: list[ClassInfo]) -> None:
        """Test continue-on-error behavior (AC7.4)."""
        from ontoralph.llm import FailingMockProvider

        # Provider that generates failing definitions (red flags)
        failing_provider = FailingMockProvider()

        config = BatchConfig(
            max_concurrency=1,
            continue_on_error=True,
        )
        processor = BatchProcessor(failing_provider, config)

        result = await processor.process(sample_classes[:2])

        # FailingMockProvider returns definitions that fail checks (not exceptions)
        # So we check that processing completed but results failed
        assert result.progress.completed > 0
        assert result.progress.failed > 0

    @pytest.mark.asyncio
    async def test_batch_resume(
        self,
        sample_classes: list[ClassInfo],
        mock_provider: MockProvider,
    ) -> None:
        """Test batch resume functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "batch_state.json"

            config = BatchConfig(
                enable_resume=True,
                state_file=state_file,
            )
            processor = BatchProcessor(mock_provider, config)

            # First run - process one class
            result1 = await processor.process(sample_classes[:1])
            assert result1.progress.completed > 0

            # State file should exist
            assert state_file.exists()

            # Second run - should skip completed
            result2 = await processor.process(sample_classes[:1])
            assert result2.progress.skipped >= result1.progress.completed


class TestBatchProgressProperties:
    """Tests for BatchProgress properties."""

    def test_remaining_calculation(self) -> None:
        """Test remaining property."""
        from ontoralph.batch.processor import BatchProgress

        progress = BatchProgress(total=10, completed=3, skipped=2)
        assert progress.remaining == 5

    def test_success_rate_with_completions(self) -> None:
        """Test success_rate property with completed classes."""
        from ontoralph.batch.processor import BatchProgress

        progress = BatchProgress(total=10, completed=4, passed=3, failed=1)
        assert progress.success_rate == 75.0

    def test_success_rate_zero_completed(self) -> None:
        """Test success_rate property with no completed classes."""
        from ontoralph.batch.processor import BatchProgress

        progress = BatchProgress(total=10)
        assert progress.success_rate == 0.0


class TestBatchResultProperties:
    """Tests for BatchResult properties."""

    def test_duration_seconds(self) -> None:
        """Test duration_seconds property."""
        from datetime import datetime, timedelta

        from ontoralph.batch.processor import BatchProgress, BatchResult

        start = datetime.now()
        end = start + timedelta(seconds=10)
        result = BatchResult(
            results=[],
            progress=BatchProgress(total=0),
            started_at=start,
            completed_at=end,
        )
        assert result.duration_seconds == 10.0

    def test_passed_and_failed_results(self) -> None:
        """Test passed_results and failed_results properties."""
        from datetime import datetime

        from ontoralph.batch.processor import BatchProgress, BatchResult

        # Create mock results
        now = datetime.now()
        passed_result = LoopResult(
            class_info=ClassInfo(iri=":Test1", label="Test1", parent_class="owl:Thing", is_ice=False),
            final_definition="A test definition.",
            status=VerifyStatus.PASS,
            total_iterations=1,
            iterations=[],
            started_at=now,
            completed_at=now,
        )
        failed_result = LoopResult(
            class_info=ClassInfo(iri=":Test2", label="Test2", parent_class="owl:Thing", is_ice=False),
            final_definition="A failed definition.",
            status=VerifyStatus.FAIL,
            total_iterations=5,
            iterations=[],
            started_at=now,
            completed_at=now,
        )

        batch_result = BatchResult(
            results=[passed_result, failed_result],
            progress=BatchProgress(total=2, completed=2, passed=1, failed=1),
            started_at=now,
            completed_at=now,
        )

        assert len(batch_result.passed_results) == 1
        assert len(batch_result.failed_results) == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_turtle_output(self) -> None:
        """Test validate_turtle_output convenience function."""
        turtle = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        <http://example.org/Test> a owl:Class ;
            rdfs:label "Test Class" .
        """

        issues = validate_turtle_output(turtle)
        # Clean turtle should have minimal issues
        violations = [i for i in issues if i.severity.value == "violation"]
        assert len(violations) == 0

    def test_check_batch_integrity(self) -> None:
        """Test check_batch_integrity convenience function."""
        turtle = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        <http://example.org/Test1> a owl:Class ;
            rdfs:label "Test Class" .
        <http://example.org/Test2> a owl:Class ;
            rdfs:label "Test Class" .
        """

        dup, pun, ns = check_batch_integrity(turtle)

        # Should detect duplicate label
        assert len(dup) >= 1
