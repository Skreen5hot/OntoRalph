"""Turtle output generation.

This module generates valid OWL/Turtle syntax for refined definitions.
Uses rdflib for proper RDF handling and validation.
"""

from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

from ontoralph.core.models import ClassInfo, LoopResult


class TurtleValidationError(Exception):
    """Raised when Turtle validation fails."""

    pass


class TurtleGenerator:
    """Generates Turtle syntax for ontology class definitions.

    Uses rdflib for proper IRI handling, literal escaping,
    and Turtle validation.
    """

    # Standard namespace definitions
    NAMESPACES = {
        "owl": OWL,
        "rdf": RDF,
        "rdfs": RDFS,
        "skos": SKOS,
        "xsd": XSD,
    }

    # Custom namespace URIs
    CUSTOM_NAMESPACE_URIS = {
        "cco": "http://www.ontologyrepository.com/CommonCoreOntologies/",
        "bfo": "http://purl.obolibrary.org/obo/BFO_",
        "obo": "http://purl.obolibrary.org/obo/",
    }

    def __init__(
        self,
        base_namespace: str | None = None,
        additional_prefixes: dict[str, str] | None = None,
        include_comments: bool = True,
    ) -> None:
        """Initialize the Turtle generator.

        Args:
            base_namespace: Base namespace for unprefixed IRIs (default uses empty prefix).
            additional_prefixes: Additional namespace prefixes to include.
            include_comments: Whether to include comments in output.
        """
        self.base_namespace = base_namespace or "http://example.org/ontology#"
        self.additional_prefixes = additional_prefixes or {}
        self.include_comments = include_comments

        # Build namespace map
        self._namespaces: dict[str, Namespace] = {}
        for prefix, uri in self.CUSTOM_NAMESPACE_URIS.items():
            self._namespaces[prefix] = Namespace(uri)
        for prefix, uri in self.additional_prefixes.items():
            self._namespaces[prefix] = Namespace(uri)

    def generate(self, class_info: ClassInfo, definition: str) -> str:
        """Generate a Turtle block for a class definition.

        Args:
            class_info: Information about the class.
            definition: The refined definition.

        Returns:
            Valid Turtle syntax as a string.
        """
        graph = self._create_graph()

        # Resolve the class IRI
        class_uri = self._resolve_iri(class_info.iri)

        # Add class declaration
        graph.add((class_uri, RDF.type, OWL.Class))

        # Add label
        graph.add((class_uri, RDFS.label, Literal(class_info.label, lang="en")))

        # Add definition using skos:definition
        graph.add((class_uri, SKOS.definition, Literal(definition, lang="en")))

        # Add parent class (subClassOf)
        if class_info.parent_class:
            parent_uri = self._resolve_iri(class_info.parent_class)
            graph.add((class_uri, RDFS.subClassOf, parent_uri))

        # Serialize to Turtle
        turtle_str = graph.serialize(format="turtle")

        # Add header comment if enabled
        if self.include_comments:
            header = self._generate_header_comment(class_info)
            turtle_str = header + turtle_str

        return turtle_str

    def generate_batch(self, results: list[tuple[ClassInfo, str]]) -> str:
        """Generate a Turtle file with multiple class definitions.

        Args:
            results: List of (ClassInfo, definition) tuples.

        Returns:
            Combined Turtle syntax for all classes.
        """
        graph = self._create_graph()

        for class_info, definition in results:
            class_uri = self._resolve_iri(class_info.iri)

            # Add class declaration
            graph.add((class_uri, RDF.type, OWL.Class))
            graph.add((class_uri, RDFS.label, Literal(class_info.label, lang="en")))
            graph.add((class_uri, SKOS.definition, Literal(definition, lang="en")))

            if class_info.parent_class:
                parent_uri = self._resolve_iri(class_info.parent_class)
                graph.add((class_uri, RDFS.subClassOf, parent_uri))

        turtle_str = graph.serialize(format="turtle")

        if self.include_comments:
            header = f"# OntoRalph Generated Definitions\n# Classes: {len(results)}\n\n"
            turtle_str = header + turtle_str

        return turtle_str

    def generate_from_result(self, result: LoopResult) -> str:
        """Generate Turtle from a completed LoopResult.

        Args:
            result: The completed loop result.

        Returns:
            Valid Turtle syntax for the refined definition.
        """
        return self.generate(result.class_info, result.final_definition)

    def validate(self, turtle_str: str) -> tuple[bool, str | None]:
        """Validate Turtle syntax by parsing with rdflib.

        Args:
            turtle_str: Turtle string to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            graph = Graph()
            graph.parse(data=turtle_str, format="turtle")
            return True, None
        except Exception as e:
            return False, str(e)

    def validate_or_raise(self, turtle_str: str) -> Graph:
        """Validate Turtle and return the parsed graph, or raise on error.

        Args:
            turtle_str: Turtle string to validate.

        Returns:
            Parsed RDF graph.

        Raises:
            TurtleValidationError: If validation fails.
        """
        try:
            graph = Graph()
            graph.parse(data=turtle_str, format="turtle")
            return graph
        except Exception as e:
            raise TurtleValidationError(f"Invalid Turtle syntax: {e}") from e

    def _create_graph(self) -> Graph:
        """Create an RDF graph with namespace bindings.

        Returns:
            Configured RDF graph.
        """
        graph = Graph()

        # Bind standard namespaces
        graph.bind("owl", OWL)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("skos", SKOS)

        # Bind custom namespaces
        for prefix, ns in self._namespaces.items():
            graph.bind(prefix, ns)

        # Bind base namespace with empty prefix
        base_ns = Namespace(self.base_namespace)
        graph.bind("", base_ns)
        self._namespaces[""] = base_ns

        return graph

    def _resolve_iri(self, iri: str) -> URIRef:
        """Resolve a prefixed IRI to a full URI.

        Args:
            iri: IRI string, possibly with prefix (e.g., ':VerbPhrase', 'cco:ICE').

        Returns:
            Full URI reference.
        """
        if iri.startswith("http://") or iri.startswith("https://"):
            return URIRef(iri)

        if ":" in iri:
            prefix, local = iri.split(":", 1)
            if prefix in self._namespaces:
                return self._namespaces[prefix][local]
            elif prefix in self.NAMESPACES:
                return self.NAMESPACES[prefix][local]
            else:
                # Unknown prefix, treat as base namespace
                return URIRef(self.base_namespace + local)
        else:
            # No prefix, use base namespace
            return URIRef(self.base_namespace + iri)

    def _generate_header_comment(self, class_info: ClassInfo) -> str:
        """Generate a header comment for the Turtle output.

        Args:
            class_info: Information about the class.

        Returns:
            Comment string.
        """
        lines = [
            "# OntoRalph Generated Definition",
            f"# Class: {class_info.iri}",
            f"# Label: {class_info.label}",
        ]
        if class_info.is_ice:
            lines.append("# Type: Information Content Entity (ICE)")
        lines.append("")
        return "\n".join(lines) + "\n"

    def generate_prefixes(self, custom_only: bool = False) -> str:
        """Generate prefix declarations in Turtle format.

        Args:
            custom_only: If True, only generate custom prefixes.

        Returns:
            Turtle prefix declarations.
        """
        lines = []

        if not custom_only:
            lines.append(f"@prefix owl: <{OWL}> .")
            lines.append(f"@prefix rdf: <{RDF}> .")
            lines.append(f"@prefix rdfs: <{RDFS}> .")
            lines.append(f"@prefix skos: <{SKOS}> .")
            lines.append(f"@prefix xsd: <{XSD}> .")

        for prefix, uri in self.CUSTOM_NAMESPACE_URIS.items():
            lines.append(f"@prefix {prefix}: <{uri}> .")

        for prefix, uri in self.additional_prefixes.items():
            lines.append(f"@prefix {prefix}: <{uri}> .")

        lines.append(f"@prefix : <{self.base_namespace}> .")

        return "\n".join(lines)


class TurtleDiff:
    """Computes differences between Turtle definitions."""

    def diff(self, old_definition: str, new_definition: str) -> dict[str, Any]:
        """Compare two definitions and identify changes.

        Args:
            old_definition: The original definition.
            new_definition: The updated definition.

        Returns:
            Dictionary with diff information.
        """
        old_words = set(old_definition.lower().split())
        new_words = set(new_definition.lower().split())

        added = new_words - old_words
        removed = old_words - new_words
        unchanged = old_words & new_words

        return {
            "old_definition": old_definition,
            "new_definition": new_definition,
            "added_words": sorted(added),
            "removed_words": sorted(removed),
            "unchanged_words": sorted(unchanged),
            "changed": old_definition != new_definition,
            "similarity": len(unchanged) / max(len(old_words | new_words), 1),
        }

    def format_diff_text(
        self, old_definition: str, new_definition: str, context: int = 0
    ) -> str:
        """Format a text-based diff between definitions.

        Args:
            old_definition: The original definition.
            new_definition: The updated definition.
            context: Number of words of context (not used in simple mode).

        Returns:
            Formatted diff string.
        """
        if old_definition == new_definition:
            return "(no changes)"

        diff = self.diff(old_definition, new_definition)

        lines = []
        if diff["removed_words"]:
            lines.append(f"- Removed: {', '.join(diff['removed_words'])}")
        if diff["added_words"]:
            lines.append(f"+ Added: {', '.join(diff['added_words'])}")

        lines.append("")
        lines.append(f"Old: {old_definition}")
        lines.append(f"New: {new_definition}")

        return "\n".join(lines)
