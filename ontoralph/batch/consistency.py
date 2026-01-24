"""Cross-class consistency checking for batch processing.

This module checks for terminology consistency, pattern consistency,
and contradictions across multiple class definitions.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

from ontoralph.core.models import ClassInfo, LoopResult

logger = logging.getLogger(__name__)


class ConsistencyIssueType(str, Enum):
    """Types of consistency issues."""

    TERMINOLOGY = "terminology"  # Inconsistent use of terms
    PATTERN = "pattern"  # Inconsistent definition patterns
    CONTRADICTION = "contradiction"  # Contradictory statements


@dataclass
class ConsistencyIssue:
    """Represents a consistency issue across definitions."""

    issue_type: ConsistencyIssueType
    severity: str  # "error", "warning", "info"
    message: str
    affected_classes: list[str]
    evidence: str


class TerminologyAnalyzer:
    """Analyzes terminology usage across definitions."""

    # Common ontology verbs and their preferred forms
    VERB_NORMALIZATION = {
        "represents": "denotes",
        "signifies": "denotes",
        "refers to": "denotes",
        "stands for": "denotes",
        "indicates": "denotes",
        "designates": "denotes",
        "describes": "is about",
        "specifies": "prescribes",
        "encodes": "concretizes",
    }

    def __init__(self) -> None:
        self._term_usage: dict[str, list[tuple[str, str]]] = {}

    def analyze(
        self,
        definitions: dict[str, str],
    ) -> list[ConsistencyIssue]:
        """Analyze terminology consistency across definitions.

        Args:
            definitions: Map of class IRI to definition.

        Returns:
            List of terminology issues.
        """
        issues: list[ConsistencyIssue] = []

        # Track verb usage
        verb_usage: dict[str, list[str]] = {}

        for iri, definition in definitions.items():
            verbs = self._extract_verbs(definition)
            for verb in verbs:
                if verb not in verb_usage:
                    verb_usage[verb] = []
                verb_usage[verb].append(iri)

        # Check for inconsistent verb usage
        for bad_verb, good_verb in self.VERB_NORMALIZATION.items():
            if bad_verb in verb_usage and good_verb in verb_usage:
                issues.append(ConsistencyIssue(
                    issue_type=ConsistencyIssueType.TERMINOLOGY,
                    severity="warning",
                    message=(
                        f"Inconsistent verb usage: some definitions use '{bad_verb}' "
                        f"while others use '{good_verb}'"
                    ),
                    affected_classes=verb_usage[bad_verb] + verb_usage[good_verb],
                    evidence=(
                        f"'{bad_verb}' used in: {verb_usage[bad_verb]}\n"
                        f"'{good_verb}' used in: {verb_usage[good_verb]}"
                    ),
                ))
            elif bad_verb in verb_usage:
                issues.append(ConsistencyIssue(
                    issue_type=ConsistencyIssueType.TERMINOLOGY,
                    severity="info",
                    message=(
                        f"Non-standard verb '{bad_verb}' used. "
                        f"Consider using '{good_verb}' instead."
                    ),
                    affected_classes=verb_usage[bad_verb],
                    evidence=f"'{bad_verb}' used in: {', '.join(verb_usage[bad_verb])}",
                ))

        return issues

    def _extract_verbs(self, definition: str) -> list[str]:
        """Extract key verbs from a definition.

        Args:
            definition: Definition text.

        Returns:
            List of verbs found.
        """
        verbs: list[str] = []
        definition_lower = definition.lower()

        for verb in self.VERB_NORMALIZATION.keys():
            if verb in definition_lower:
                verbs.append(verb)

        for verb in self.VERB_NORMALIZATION.values():
            if verb in definition_lower:
                verbs.append(verb)

        # Also look for common BFO verbs
        bfo_verbs = ["participates in", "inheres in", "bears", "realizes"]
        for verb in bfo_verbs:
            if verb in definition_lower:
                verbs.append(verb)

        return verbs


class PatternAnalyzer:
    """Analyzes definition pattern consistency."""

    # Expected patterns for different class types
    ICE_PATTERNS = [
        r"^An? ICE that",
        r"^An? Information Content Entity that",
    ]

    GENERAL_PATTERNS = [
        r"^An? \w+ that",
        r"^An? \w+ which",
    ]

    def analyze(
        self,
        definitions: dict[str, str],
        class_infos: dict[str, ClassInfo] | None = None,
    ) -> list[ConsistencyIssue]:
        """Analyze definition pattern consistency.

        Args:
            definitions: Map of class IRI to definition.
            class_infos: Optional map of IRI to ClassInfo.

        Returns:
            List of pattern issues.
        """
        issues: list[ConsistencyIssue] = []

        # Group definitions by pattern
        patterns_used: dict[str, list[str]] = {}

        for iri, definition in definitions.items():
            pattern = self._identify_pattern(definition)
            if pattern not in patterns_used:
                patterns_used[pattern] = []
            patterns_used[pattern].append(iri)

        # Check for pattern inconsistency
        if len(patterns_used) > 1:
            # Find the most common pattern
            pattern_counts = {p: len(iris) for p, iris in patterns_used.items()}
            most_common = max(pattern_counts, key=lambda p: pattern_counts[p])

            for pattern, iris in patterns_used.items():
                if pattern != most_common and pattern != "unknown":
                    issues.append(ConsistencyIssue(
                        issue_type=ConsistencyIssueType.PATTERN,
                        severity="info",
                        message=(
                            f"Pattern inconsistency: {len(iris)} definitions use "
                            f"'{pattern}' pattern while most use '{most_common}'"
                        ),
                        affected_classes=iris,
                        evidence=f"Pattern '{pattern}' used in: {', '.join(iris)}",
                    ))

        # Check ICE definitions for proper pattern
        if class_infos:
            for iri, definition in definitions.items():
                if iri in class_infos and class_infos[iri].is_ice:
                    if not any(re.match(p, definition, re.IGNORECASE) for p in self.ICE_PATTERNS):
                        issues.append(ConsistencyIssue(
                            issue_type=ConsistencyIssueType.PATTERN,
                            severity="warning",
                            message=(
                                f"ICE definition for {iri} doesn't follow "
                                f"'An ICE that...' pattern"
                            ),
                            affected_classes=[iri],
                            evidence=f"Definition starts with: {definition[:50]}...",
                        ))

        return issues

    def _identify_pattern(self, definition: str) -> str:
        """Identify the pattern used in a definition.

        Args:
            definition: Definition text.

        Returns:
            Pattern name.
        """
        if re.match(r"^An? ICE that", definition, re.IGNORECASE):
            return "ICE-that"
        if re.match(r"^An? \w+ that", definition, re.IGNORECASE):
            return "genus-that"
        if re.match(r"^An? \w+ which", definition, re.IGNORECASE):
            return "genus-which"
        if re.match(r"^The \w+", definition, re.IGNORECASE):
            return "definite"

        return "unknown"


class ContradictionDetector:
    """Detects potential contradictions between definitions."""

    # Contradictory phrase pairs
    CONTRADICTIONS = [
        ("always", "never"),
        ("all", "none"),
        ("must", "cannot"),
        ("required", "forbidden"),
        ("exists", "does not exist"),
    ]

    def detect(
        self,
        definitions: dict[str, str],
    ) -> list[ConsistencyIssue]:
        """Detect potential contradictions.

        Args:
            definitions: Map of class IRI to definition.

        Returns:
            List of contradiction issues.
        """
        issues: list[ConsistencyIssue] = []

        # Convert to list for pairwise comparison
        items = list(definitions.items())

        for i, (iri1, def1) in enumerate(items):
            for iri2, def2 in items[i + 1:]:
                contradictions = self._find_contradictions(def1, def2)
                for phrase1, phrase2 in contradictions:
                    issues.append(ConsistencyIssue(
                        issue_type=ConsistencyIssueType.CONTRADICTION,
                        severity="warning",
                        message=(
                            f"Potential contradiction: {iri1} uses '{phrase1}' "
                            f"while {iri2} uses '{phrase2}'"
                        ),
                        affected_classes=[iri1, iri2],
                        evidence=(
                            f"'{phrase1}' in: {iri1}\n"
                            f"'{phrase2}' in: {iri2}"
                        ),
                    ))

        return issues

    def _find_contradictions(
        self,
        def1: str,
        def2: str,
    ) -> list[tuple[str, str]]:
        """Find contradictory phrases between two definitions.

        Args:
            def1: First definition.
            def2: Second definition.

        Returns:
            List of contradictory phrase pairs.
        """
        found: list[tuple[str, str]] = []
        def1_lower = def1.lower()
        def2_lower = def2.lower()

        for phrase1, phrase2 in self.CONTRADICTIONS:
            if phrase1 in def1_lower and phrase2 in def2_lower:
                found.append((phrase1, phrase2))
            if phrase2 in def1_lower and phrase1 in def2_lower:
                found.append((phrase2, phrase1))

        return found


class CrossClassConsistencyChecker:
    """Comprehensive cross-class consistency checking.

    Combines terminology, pattern, and contradiction analysis.
    """

    def __init__(self) -> None:
        self._terminology = TerminologyAnalyzer()
        self._pattern = PatternAnalyzer()
        self._contradiction = ContradictionDetector()

    def check(
        self,
        definitions: dict[str, str],
        class_infos: dict[str, ClassInfo] | None = None,
    ) -> list[ConsistencyIssue]:
        """Run all consistency checks.

        Args:
            definitions: Map of class IRI to definition.
            class_infos: Optional map of IRI to ClassInfo.

        Returns:
            Combined list of consistency issues.
        """
        issues: list[ConsistencyIssue] = []

        issues.extend(self._terminology.analyze(definitions))
        issues.extend(self._pattern.analyze(definitions, class_infos))
        issues.extend(self._contradiction.detect(definitions))

        return issues

    def check_from_results(
        self,
        results: list[LoopResult],
    ) -> list[ConsistencyIssue]:
        """Check consistency from loop results.

        Args:
            results: List of loop results.

        Returns:
            List of consistency issues.
        """
        definitions = {r.class_info.iri: r.final_definition for r in results}
        class_infos = {r.class_info.iri: r.class_info for r in results}
        return self.check(definitions, class_infos)


def check_consistency(
    definitions: dict[str, str],
    class_infos: dict[str, ClassInfo] | None = None,
) -> list[ConsistencyIssue]:
    """Convenience function to check cross-class consistency.

    Args:
        definitions: Map of class IRI to definition.
        class_infos: Optional map of IRI to ClassInfo.

    Returns:
        List of consistency issues.
    """
    checker = CrossClassConsistencyChecker()
    return checker.check(definitions, class_infos)
