"""Output validation for BFO/CCO patterns and batch integrity.

This module validates generated Turtle output against BFO/CCO ontology patterns
and checks batch integrity (duplicate labels, punning, namespace validation).

Patterns based on shaclValidator.js and SPARQL queries from Recommended Tests.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

logger = logging.getLogger(__name__)

# CCO and BFO namespaces
CCO = Namespace("http://www.ontologyrepository.com/CommonCoreOntologies/")
BFO = Namespace("http://purl.obolibrary.org/obo/")


class IssueSeverity(str, Enum):
    """Severity levels for validation issues (aligned with SHACL)."""

    VIOLATION = "violation"  # Must be fixed - ontologically impossible
    WARNING = "warning"  # Should be addressed - incomplete but valid
    INFO = "info"  # Suggestion - nice to have


@dataclass
class ValidationIssue:
    """Represents a validation issue found in output."""

    pattern: str  # Pattern name (e.g., "Information Staircase", "Role Pattern")
    rule: str  # Specific rule violated
    severity: IssueSeverity
    subject: str  # IRI of the problematic entity
    message: str
    explanation: str
    fix: str | None = None


# CCO predicate IRIs
CCO_IS_CONCRETIZED_BY = CCO["is_concretized_by"]
CCO_CONCRETIZES = CCO["concretizes"]
CCO_HAS_TEXT_VALUE = CCO["has_text_value"]
CCO_IS_BEARER_OF = CCO["is_bearer_of"]
CCO_REALIZES = CCO["realizes"]
CCO_DESIGNATES = CCO["designates"]
CCO_IS_DESIGNATED_BY = CCO["is_designated_by"]

# CCO class IRIs
CCO_ICE = CCO["InformationContentEntity"]
CCO_IBE = CCO["InformationBearingEntity"]
CCO_DESIGNATIVE_ICE = CCO["DesignativeInformationContentEntity"]
CCO_ROLE = CCO["Role"]


class TurtleValidator:
    """Validates generated Turtle against BFO/CCO patterns.

    Based on patterns from shaclValidator.js:
    - Information Staircase (ICE/IBE)
    - Role Pattern (bearer/realization)
    - Designation Pattern
    - Domain/Range constraints
    """

    # Valid OWL namespace terms
    VALID_OWL_TERMS = {
        "AllDifferent",
        "allValuesFrom",
        "AnnotationProperty",
        "backwardCompatibleWith",
        "cardinality",
        "Class",
        "complementOf",
        "DataRange",
        "DatatypeProperty",
        "DeprecatedClass",
        "DeprecatedProperty",
        "differentFrom",
        "disjointWith",
        "distinctMembers",
        "equivalentClass",
        "equivalentProperty",
        "FunctionalProperty",
        "hasValue",
        "imports",
        "incompatibleWith",
        "intersectionOf",
        "InverseFunctionalProperty",
        "inverseOf",
        "maxCardinality",
        "minCardinality",
        "Nothing",
        "ObjectProperty",
        "oneOf",
        "onProperty",
        "Ontology",
        "OntologyProperty",
        "priorVersion",
        "Restriction",
        "sameAs",
        "someValuesFrom",
        "SymmetricProperty",
        "Thing",
        "TransitiveProperty",
        "unionOf",
        "versionInfo",
        "NamedIndividual",
    }

    # Valid RDFS namespace terms
    VALID_RDFS_TERMS = {
        "Class",
        "comment",
        "Container",
        "ContainerMembershipProperty",
        "Datatype",
        "domain",
        "isDefinedBy",
        "label",
        "Literal",
        "member",
        "range",
        "Resource",
        "seeAlso",
        "subClassOf",
        "subPropertyOf",
    }

    # Valid SKOS namespace terms
    VALID_SKOS_TERMS = {
        "altLabel",
        "broader",
        "changeNote",
        "Collection",
        "Concept",
        "ConceptScheme",
        "definition",
        "editorialNote",
        "example",
        "hasTopConcept",
        "hiddenLabel",
        "historyNote",
        "inScheme",
        "member",
        "memberList",
        "narrower",
        "note",
        "OrderedCollection",
        "prefLabel",
        "related",
        "scopeNote",
        "semanticRelation",
    }

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the validator.

        Args:
            strict_mode: If True, raise warnings as violations.
        """
        self.strict_mode = strict_mode

    def validate(self, graph: Graph) -> list[ValidationIssue]:
        """Run all validation checks on a graph.

        Args:
            graph: RDF graph to validate.

        Returns:
            List of validation issues.
        """
        issues: list[ValidationIssue] = []

        # Run all pattern validators
        issues.extend(self.validate_ice_pattern(graph))
        issues.extend(self.validate_role_pattern(graph))
        issues.extend(self.validate_designation_pattern(graph))
        issues.extend(self.validate_namespace_terms(graph))

        return issues

    def validate_ice_pattern(self, graph: Graph) -> list[ValidationIssue]:
        """Validate Information Staircase pattern.

        ICE should have is_concretized_by relationship to IBE.
        This is a WARNING since ICE can exist abstractly (like a Law).

        Args:
            graph: RDF graph to check.

        Returns:
            List of issues found.
        """
        issues: list[ValidationIssue] = []

        # Find all ICE instances
        for ice in graph.subjects(RDF.type, CCO_ICE):
            # Check for is_concretized_by relationship
            concretizations = list(graph.objects(ice, CCO_IS_CONCRETIZED_BY))

            if not concretizations:
                issues.append(
                    ValidationIssue(
                        pattern="Information Staircase",
                        rule="ICE Concretization",
                        severity=IssueSeverity.WARNING,
                        subject=str(ice),
                        message=f"ICE {self._short_iri(ice)} should have is_concretized_by relationship to IBE",
                        explanation=(
                            "While an ICE can exist abstractly (like a Law or Recipe), "
                            "for practical modeling it should be concretized in a physical bearer."
                        ),
                        fix=f"Add: {self._short_iri(ice)} is_concretized_by [IBE]",
                    )
                )

        # Find all IBE instances
        for ibe in graph.subjects(RDF.type, CCO_IBE):
            # Check for concretizes relationship
            concretizes = list(graph.objects(ibe, CCO_CONCRETIZES))
            inverse = list(graph.subjects(CCO_IS_CONCRETIZED_BY, ibe))

            if not concretizes and not inverse:
                issues.append(
                    ValidationIssue(
                        pattern="Information Staircase",
                        rule="IBE Concretization",
                        severity=IssueSeverity.WARNING,
                        subject=str(ibe),
                        message=f"IBE {self._short_iri(ibe)} should concretize at least one ICE",
                        explanation=(
                            "An IBE without information is a 'blank slate' which is "
                            "rarely the modeling intent."
                        ),
                        fix=f"Add: {self._short_iri(ibe)} concretizes [ICE]",
                    )
                )

        return issues

    def validate_role_pattern(self, graph: Graph) -> list[ValidationIssue]:
        """Validate Role Pattern.

        Role MUST have a bearer (VIOLATION - BFO principle).
        Role SHOULD be realized by a Process (WARNING).

        Args:
            graph: RDF graph to check.

        Returns:
            List of issues found.
        """
        issues: list[ValidationIssue] = []

        # Find all Role instances
        for role in graph.subjects(RDF.type, CCO_ROLE):
            # Check for bearer (REQUIRED)
            bearers = list(graph.subjects(CCO_IS_BEARER_OF, role))

            if not bearers:
                issues.append(
                    ValidationIssue(
                        pattern="Role Pattern",
                        rule="Role Bearer",
                        severity=IssueSeverity.VIOLATION,
                        subject=str(role),
                        message=f"Role {self._short_iri(role)} must be borne by at least one entity",
                        explanation=(
                            "In BFO, a Role (Disposition) cannot exist without a bearer - "
                            "this is ontologically impossible."
                        ),
                        fix=f"Add: [Entity] is_bearer_of {self._short_iri(role)}",
                    )
                )

            # Check for realization (OPTIONAL but recommended)
            realizations = list(graph.subjects(CCO_REALIZES, role))

            if not realizations:
                issues.append(
                    ValidationIssue(
                        pattern="Role Pattern",
                        rule="Role Realization",
                        severity=IssueSeverity.WARNING,
                        subject=str(role),
                        message=f"Role {self._short_iri(role)} is not realized by any Process",
                        explanation=(
                            "While dispositions can remain dormant (per BFO), consider "
                            "adding a realizes relationship if this role has been actualized."
                        ),
                        fix=f"Add: [Process] realizes {self._short_iri(role)}",
                    )
                )

        return issues

    def validate_designation_pattern(self, graph: Graph) -> list[ValidationIssue]:
        """Validate Designation Pattern.

        DesignativeICE MUST designate an entity (VIOLATION).
        A Name that names nothing is not a Designative ICE.

        Args:
            graph: RDF graph to check.

        Returns:
            List of issues found.
        """
        issues: list[ValidationIssue] = []

        # Find all DesignativeICE instances
        for desig in graph.subjects(RDF.type, CCO_DESIGNATIVE_ICE):
            # Check for designates or is_designated_by relationship
            designates = list(graph.objects(desig, CCO_DESIGNATES))
            designated_by = list(graph.subjects(CCO_IS_DESIGNATED_BY, desig))

            if not designates and not designated_by:
                issues.append(
                    ValidationIssue(
                        pattern="Designation Pattern",
                        rule="Designation Link",
                        severity=IssueSeverity.VIOLATION,
                        subject=str(desig),
                        message=f"DesignativeICE {self._short_iri(desig)} must designate an entity",
                        explanation=(
                            "A 'Name' that names nothing is not a Designative ICE in a "
                            "realist sense - it's just an InformationContentEntity."
                        ),
                        fix=f"Add: {self._short_iri(desig)} designates [Entity]",
                    )
                )

        return issues

    def validate_namespace_terms(self, graph: Graph) -> list[ValidationIssue]:
        """Validate OWL/RDFS/SKOS namespace term usage.

        Catches typos like rdfs:lable instead of rdfs:label.

        Args:
            graph: RDF graph to check.

        Returns:
            List of issues found.
        """
        issues: list[ValidationIssue] = []

        # Check all predicates and objects for namespace issues
        for _s, p, o in graph:
            # Check predicate
            issues.extend(self._check_term(p))

            # Check object if it's a URI
            if isinstance(o, URIRef):
                issues.extend(self._check_term(o))

        return issues

    def _check_term(self, term: URIRef) -> list[ValidationIssue]:
        """Check a single term for namespace validity.

        Args:
            term: URI to check.

        Returns:
            List of issues found.
        """
        issues: list[ValidationIssue] = []
        term_str = str(term)

        # Check OWL namespace
        if str(OWL) in term_str:
            local = term_str.replace(str(OWL), "")
            if local and local not in self.VALID_OWL_TERMS:
                issues.append(
                    ValidationIssue(
                        pattern="Namespace Validation",
                        rule="Invalid OWL Term",
                        severity=IssueSeverity.WARNING,
                        subject=term_str,
                        message=f"Term 'owl:{local}' is not a valid OWL vocabulary term",
                        explanation=(
                            f"'{local}' is not defined in the OWL namespace. "
                            "This may be a typo or unsupported term."
                        ),
                        fix=f"Check spelling of 'owl:{local}'",
                    )
                )

        # Check RDFS namespace
        if str(RDFS) in term_str:
            local = term_str.replace(str(RDFS), "")
            if local and local not in self.VALID_RDFS_TERMS:
                issues.append(
                    ValidationIssue(
                        pattern="Namespace Validation",
                        rule="Invalid RDFS Term",
                        severity=IssueSeverity.WARNING,
                        subject=term_str,
                        message=f"Term 'rdfs:{local}' is not a valid RDFS vocabulary term",
                        explanation=(
                            f"'{local}' is not defined in the RDFS namespace. "
                            "This may be a typo (e.g., 'lable' instead of 'label')."
                        ),
                        fix=f"Check spelling of 'rdfs:{local}'",
                    )
                )

        # Check SKOS namespace
        if str(SKOS) in term_str:
            local = term_str.replace(str(SKOS), "")
            if local and local not in self.VALID_SKOS_TERMS:
                issues.append(
                    ValidationIssue(
                        pattern="Namespace Validation",
                        rule="Invalid SKOS Term",
                        severity=IssueSeverity.WARNING,
                        subject=term_str,
                        message=f"Term 'skos:{local}' is not a valid SKOS vocabulary term",
                        explanation=(
                            f"'{local}' is not defined in the SKOS namespace. "
                            "This may be a typo."
                        ),
                        fix=f"Check spelling of 'skos:{local}'",
                    )
                )

        return issues

    def _short_iri(self, iri: URIRef | str) -> str:
        """Get short form of an IRI.

        Args:
            iri: Full IRI.

        Returns:
            Short form (e.g., "cco:Person").
        """
        iri_str = str(iri)

        if "CommonCoreOntologies/" in iri_str:
            return "cco:" + iri_str.split("/")[-1]
        if "purl.obolibrary.org/obo/" in iri_str:
            return "bfo:" + iri_str.split("/")[-1]
        if "#" in iri_str:
            return ":" + iri_str.split("#")[-1]
        if "/" in iri_str:
            return ":" + iri_str.split("/")[-1]

        return iri_str


@dataclass
class DuplicateLabelIssue:
    """Represents a duplicate label issue."""

    label: str
    resources: list[str]
    message: str


@dataclass
class PunningIssue:
    """Represents an OWL punning issue."""

    resource: str
    types: list[str]
    message: str


@dataclass
class NamespaceIssue:
    """Represents a namespace validation issue."""

    term: str
    namespace: str
    message: str


class BatchIntegrityChecker:
    """Checks batch output for integrity issues.

    Based on SPARQL queries from Recommended Tests:
    - duplicate-rdfs-label.rq: Duplicate labels
    - avoid-punning.rq: OWL punning
    - check-for-undefined-*.sparql: Namespace validation
    """

    def check_all(
        self, graph: Graph
    ) -> tuple[
        list[DuplicateLabelIssue],
        list[PunningIssue],
        list[NamespaceIssue],
    ]:
        """Run all batch integrity checks.

        Args:
            graph: Combined RDF graph from batch.

        Returns:
            Tuple of (duplicate_labels, punning_issues, namespace_issues).
        """
        return (
            self.check_duplicate_labels(graph),
            self.check_punning(graph),
            self.validate_namespace_terms(graph),
        )

    def check_duplicate_labels(self, graph: Graph) -> list[DuplicateLabelIssue]:
        """Detect duplicate rdfs:label values across batch output.

        Based on duplicate-rdfs-label.rq SPARQL query.

        Args:
            graph: RDF graph to check.

        Returns:
            List of duplicate label issues.
        """
        issues: list[DuplicateLabelIssue] = []

        # Collect all labels
        labels: dict[str, list[str]] = {}
        for s, o in graph.subject_objects(RDFS.label):
            label = str(o).lower() if isinstance(o, Literal) else str(o).lower()
            if label not in labels:
                labels[label] = []
            labels[label].append(str(s))

        # Find duplicates
        for label, resources in labels.items():
            if len(resources) > 1:
                issues.append(
                    DuplicateLabelIssue(
                        label=label,
                        resources=resources,
                        message=f"Duplicate rdfs:label '{label}' found on {len(resources)} resources",
                    )
                )

        return issues

    def check_punning(self, graph: Graph) -> list[PunningIssue]:
        """Detect OWL punning (element is both individual and class).

        Based on avoid-punning.rq SPARQL query.

        Args:
            graph: RDF graph to check.

        Returns:
            List of punning issues.
        """
        issues: list[PunningIssue] = []

        # Types that shouldn't coexist with NamedIndividual
        universal_types = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty}

        # Find all NamedIndividuals
        individuals = set(graph.subjects(RDF.type, OWL.NamedIndividual))

        for individual in individuals:
            # Check if it's also typed as a universal (Class, Property)
            individual_types = set(graph.objects(individual, RDF.type))
            pun_types = individual_types & universal_types

            if pun_types:
                issues.append(
                    PunningIssue(
                        resource=str(individual),
                        types=[str(t) for t in pun_types | {OWL.NamedIndividual}],
                        message=(
                            f"Resource {str(individual)} is a pun: "
                            f"typed as both individual and {', '.join(str(t).split('#')[-1] for t in pun_types)}"
                        ),
                    )
                )

        return issues

    def validate_namespace_terms(self, graph: Graph) -> list[NamespaceIssue]:
        """Validate namespace term usage.

        Based on check-for-undefined-*.sparql queries.

        Args:
            graph: RDF graph to check.

        Returns:
            List of namespace issues.
        """
        # Delegate to TurtleValidator
        validator = TurtleValidator()
        validation_issues = validator.validate_namespace_terms(graph)

        return [
            NamespaceIssue(
                term=issue.subject,
                namespace=issue.pattern,
                message=issue.message,
            )
            for issue in validation_issues
        ]


def validate_turtle_output(turtle_str: str) -> list[ValidationIssue]:
    """Convenience function to validate Turtle output.

    Args:
        turtle_str: Turtle syntax string.

    Returns:
        List of validation issues.
    """
    graph = Graph()
    graph.parse(data=turtle_str, format="turtle")

    validator = TurtleValidator()
    return validator.validate(graph)


def check_batch_integrity(
    turtle_str: str,
) -> tuple[list[DuplicateLabelIssue], list[PunningIssue], list[NamespaceIssue]]:
    """Convenience function to check batch integrity.

    Args:
        turtle_str: Combined Turtle output from batch.

    Returns:
        Tuple of (duplicate_labels, punning_issues, namespace_issues).
    """
    graph = Graph()
    graph.parse(data=turtle_str, format="turtle")

    checker = BatchIntegrityChecker()
    return checker.check_all(graph)
