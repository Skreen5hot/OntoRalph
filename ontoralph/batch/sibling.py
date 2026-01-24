"""Sibling exclusivity checking for batch processing.

This module verifies that sibling class definitions are mutually exclusive
and don't have overlapping concepts or terminology.
"""

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum

from ontoralph.core.models import ClassInfo, LoopResult

logger = logging.getLogger(__name__)


class OverlapType(str, Enum):
    """Types of overlap between sibling definitions."""

    IDENTICAL = "identical"  # Definitions are the same
    HIGH_SIMILARITY = "high_similarity"  # Very similar wording
    SHARED_DIFFERENTIA = "shared_differentia"  # Same differentia used
    TERM_OVERLAP = "term_overlap"  # Uses sibling's term in definition
    CONCEPT_OVERLAP = "concept_overlap"  # Overlapping concepts


@dataclass
class ExclusivityIssue:
    """Represents an exclusivity issue between sibling classes."""

    class1_iri: str
    class2_iri: str
    overlap_type: OverlapType
    severity: str  # "error", "warning", "info"
    message: str
    evidence: str
    similarity_score: float = 0.0


class SiblingExclusivityChecker:
    """Checks that sibling class definitions are mutually exclusive.

    Siblings should have distinct definitions that clearly differentiate
    them from each other. This checker identifies potential overlaps.
    """

    # Common differentiating words to ignore in similarity checks
    STOP_WORDS = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "that",
        "which",
        "of",
        "in",
        "to",
        "for",
        "and",
        "or",
        "as",
        "by",
        "with",
        "from",
        "at",
        "on",
    }

    # Threshold for high similarity warning
    SIMILARITY_THRESHOLD = 0.85

    # Threshold for shared differentia detection
    SHARED_DIFFERENTIA_THRESHOLD = 0.7

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        check_term_overlap: bool = True,
    ) -> None:
        """Initialize the checker.

        Args:
            similarity_threshold: Threshold for flagging high similarity.
            check_term_overlap: Whether to check for term usage in definitions.
        """
        self.similarity_threshold = similarity_threshold
        self.check_term_overlap = check_term_overlap

    def check(
        self,
        definitions: dict[str, str],
        class_infos: dict[str, ClassInfo] | None = None,
    ) -> list[ExclusivityIssue]:
        """Check sibling definitions for mutual exclusivity.

        Args:
            definitions: Map of class IRI to definition text.
            class_infos: Optional map of class IRI to ClassInfo for labels.

        Returns:
            List of exclusivity issues found.
        """
        issues: list[ExclusivityIssue] = []
        iris = list(definitions.keys())

        # Compare each pair of definitions
        for i, iri1 in enumerate(iris):
            for iri2 in iris[i + 1 :]:
                def1 = definitions[iri1]
                def2 = definitions[iri2]

                # Check for identical definitions
                if def1 == def2:
                    issues.append(
                        ExclusivityIssue(
                            class1_iri=iri1,
                            class2_iri=iri2,
                            overlap_type=OverlapType.IDENTICAL,
                            severity="error",
                            message=f"Classes {iri1} and {iri2} have identical definitions",
                            evidence=f"Both: {def1[:100]}...",
                            similarity_score=1.0,
                        )
                    )
                    continue

                # Check overall similarity
                similarity = self._calculate_similarity(def1, def2)
                if similarity >= self.similarity_threshold:
                    issues.append(
                        ExclusivityIssue(
                            class1_iri=iri1,
                            class2_iri=iri2,
                            overlap_type=OverlapType.HIGH_SIMILARITY,
                            severity="warning",
                            message=(
                                f"Classes {iri1} and {iri2} have highly similar "
                                f"definitions ({similarity:.0%} similar)"
                            ),
                            evidence=f"Definition 1: {def1[:80]}...\nDefinition 2: {def2[:80]}...",
                            similarity_score=similarity,
                        )
                    )

                # Check for shared differentia
                diff_overlap = self._check_differentia_overlap(def1, def2)
                if diff_overlap and diff_overlap >= self.SHARED_DIFFERENTIA_THRESHOLD:
                    issues.append(
                        ExclusivityIssue(
                            class1_iri=iri1,
                            class2_iri=iri2,
                            overlap_type=OverlapType.SHARED_DIFFERENTIA,
                            severity="warning",
                            message=(
                                f"Classes {iri1} and {iri2} may share similar "
                                f"differentiating properties"
                            ),
                            evidence=f"Differentia overlap: {diff_overlap:.0%}",
                            similarity_score=diff_overlap,
                        )
                    )

                # Check for term overlap (using sibling's label)
                if self.check_term_overlap and class_infos:
                    term_issues = self._check_term_overlap(
                        iri1, iri2, def1, def2, class_infos
                    )
                    issues.extend(term_issues)

        return issues

    def check_from_results(
        self,
        results: list[LoopResult],
        group_by_parent: bool = True,
    ) -> list[ExclusivityIssue]:
        """Check exclusivity from a list of LoopResults.

        Args:
            results: List of loop results to check.
            group_by_parent: If True, only check siblings with same parent.

        Returns:
            List of exclusivity issues.
        """
        if group_by_parent:
            # Group by parent class
            by_parent: dict[str, list[LoopResult]] = {}
            for result in results:
                parent = result.class_info.parent_class
                if parent not in by_parent:
                    by_parent[parent] = []
                by_parent[parent].append(result)

            # Check each group
            all_issues: list[ExclusivityIssue] = []
            for _parent, group in by_parent.items():
                if len(group) < 2:
                    continue

                definitions = {r.class_info.iri: r.final_definition for r in group}
                class_infos = {r.class_info.iri: r.class_info for r in group}
                issues = self.check(definitions, class_infos)
                all_issues.extend(issues)

            return all_issues
        else:
            # Check all pairs
            definitions = {r.class_info.iri: r.final_definition for r in results}
            class_infos = {r.class_info.iri: r.class_info for r in results}
            return self.check(definitions, class_infos)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.

        Uses SequenceMatcher for fuzzy string matching.

        Args:
            text1: First text.
            text2: Second text.

        Returns:
            Similarity ratio between 0 and 1.
        """
        # Normalize texts
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)

        return SequenceMatcher(None, norm1, norm2).ratio()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Text to normalize.

        Returns:
            Normalized text.
        """
        # Lowercase
        text = text.lower()

        # Remove punctuation
        text = re.sub(r"[^\w\s]", " ", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        return text

    def _check_differentia_overlap(self, def1: str, def2: str) -> float | None:
        """Check for overlap in differentiating content.

        Extracts the part after "that" (the differentia) and compares.

        Args:
            def1: First definition.
            def2: Second definition.

        Returns:
            Overlap ratio or None if no differentia found.
        """
        # Extract differentia (part after "that" or "which")
        diff1 = self._extract_differentia(def1)
        diff2 = self._extract_differentia(def2)

        if not diff1 or not diff2:
            return None

        # Remove stop words and compare
        words1 = set(diff1.lower().split()) - self.STOP_WORDS
        words2 = set(diff2.lower().split()) - self.STOP_WORDS

        if not words1 or not words2:
            return None

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total if total > 0 else 0.0

    def _extract_differentia(self, definition: str) -> str | None:
        """Extract the differentia from a genus-differentia definition.

        Args:
            definition: The full definition.

        Returns:
            The differentia part or None if not found.
        """
        # Pattern: "An X that Y" or "An X which Y"
        match = re.search(r"\bthat\s+(.+)", definition, re.IGNORECASE)
        if match:
            return match.group(1)

        match = re.search(r"\bwhich\s+(.+)", definition, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _check_term_overlap(
        self,
        iri1: str,
        iri2: str,
        def1: str,
        def2: str,
        class_infos: dict[str, ClassInfo],
    ) -> list[ExclusivityIssue]:
        """Check if definitions use sibling's term.

        Args:
            iri1: First class IRI.
            iri2: Second class IRI.
            def1: First definition.
            def2: Second definition.
            class_infos: Map of IRI to ClassInfo.

        Returns:
            List of term overlap issues.
        """
        issues: list[ExclusivityIssue] = []

        label1 = class_infos[iri1].label.lower()
        label2 = class_infos[iri2].label.lower()

        # Check if def1 mentions label2
        if self._contains_term(def1, label2):
            issues.append(
                ExclusivityIssue(
                    class1_iri=iri1,
                    class2_iri=iri2,
                    overlap_type=OverlapType.TERM_OVERLAP,
                    severity="info",
                    message=(f"Definition of {iri1} mentions sibling term '{label2}'"),
                    evidence=f"'{label2}' found in definition of {iri1}",
                    similarity_score=0.0,
                )
            )

        # Check if def2 mentions label1
        if self._contains_term(def2, label1):
            issues.append(
                ExclusivityIssue(
                    class1_iri=iri2,
                    class2_iri=iri1,
                    overlap_type=OverlapType.TERM_OVERLAP,
                    severity="info",
                    message=(f"Definition of {iri2} mentions sibling term '{label1}'"),
                    evidence=f"'{label1}' found in definition of {iri2}",
                    similarity_score=0.0,
                )
            )

        return issues

    def _contains_term(self, text: str, term: str) -> bool:
        """Check if text contains a term (as whole word).

        Args:
            text: Text to search.
            term: Term to find.

        Returns:
            True if term is found as a whole word.
        """
        # Use word boundary matching
        pattern = rf"\b{re.escape(term)}\b"
        return bool(re.search(pattern, text, re.IGNORECASE))


def check_sibling_exclusivity(
    definitions: dict[str, str],
    class_infos: dict[str, ClassInfo] | None = None,
) -> list[ExclusivityIssue]:
    """Convenience function to check sibling exclusivity.

    Args:
        definitions: Map of class IRI to definition.
        class_infos: Optional map of IRI to ClassInfo.

    Returns:
        List of exclusivity issues.
    """
    checker = SiblingExclusivityChecker()
    return checker.check(definitions, class_infos)
