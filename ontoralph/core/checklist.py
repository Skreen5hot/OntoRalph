"""Checklist evaluation for ontology definitions.

This module contains the automated checklist evaluation logic for the Ralph Loop.
It implements:
- RedFlagDetector: Pattern-based detection of anti-patterns (R1-R4)
- CircularityChecker: Detects term appearing in its own definition
- ChecklistEvaluator: Orchestrates all checks and determines scoring
- CustomRuleEvaluator: Evaluates user-defined regex-based rules
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ontoralph.core.models import CheckResult, Severity, VerifyStatus

if TYPE_CHECKING:
    from ontoralph.config.settings import CustomRule


class RedFlagDetector:
    """Detects red flag anti-patterns in definitions.

    Red flags are patterns that indicate fundamental problems with a definition
    that cannot be fixed through minor refinement. Their presence causes
    automatic FAIL status.

    Red Flag Categories:
        R1: Process verbs (extracted, detected, identified, parsed)
            - Definitions should describe what something IS, not how it's created
        R2: "represents" instead of "denotes"
            - ICEs denote, they don't represent (BFO terminology)
        R3: Functional language (serves to, used to, functions to)
            - Definitions should be essential, not functional
        R4: Syntactic terms (noun phrase, verb phrase, encoded as)
            - Definitions should be ontological, not syntactic
    """

    R1_PATTERNS = [
        r"\bextracted\b",
        r"\bdetected\b",
        r"\bidentified\b",
        r"\bparsed\b",
    ]
    R2_PATTERNS = [
        r"\brepresents\b",
    ]
    R3_PATTERNS = [
        r"\bserves to\b",
        r"\bused to\b",
        r"\bfunctions to\b",
    ]
    R4_PATTERNS = [
        r"\bnoun phrase\b",
        r"\bverb phrase\b",
        r"\bencoded as\b",
    ]

    def check(self, definition: str) -> list[CheckResult]:
        """Check a definition for red flags.

        Args:
            definition: The definition text to check.

        Returns:
            List of red flag check results (one per category R1-R4).
        """
        results = []
        definition_lower = definition.lower()

        # R1: Process verbs
        r1_matches = self._find_matches(definition_lower, self.R1_PATTERNS)
        results.append(
            CheckResult(
                code="R1",
                name="No process verbs",
                passed=len(r1_matches) == 0,
                evidence=(
                    f"Found process verbs: {', '.join(r1_matches)}"
                    if r1_matches
                    else "No process verbs found"
                ),
                severity=Severity.RED_FLAG,
            )
        )

        # R2: "represents" instead of "denotes"
        r2_matches = self._find_matches(definition_lower, self.R2_PATTERNS)
        results.append(
            CheckResult(
                code="R2",
                name="Uses 'denotes' not 'represents'",
                passed=len(r2_matches) == 0,
                evidence=(
                    "Found 'represents' - ICEs should 'denote', not 'represent'"
                    if r2_matches
                    else "Correct: does not use 'represents'"
                ),
                severity=Severity.RED_FLAG,
            )
        )

        # R3: Functional language
        r3_matches = self._find_matches(definition_lower, self.R3_PATTERNS)
        results.append(
            CheckResult(
                code="R3",
                name="No functional language",
                passed=len(r3_matches) == 0,
                evidence=(
                    f"Found functional language: {', '.join(r3_matches)}"
                    if r3_matches
                    else "No functional language found"
                ),
                severity=Severity.RED_FLAG,
            )
        )

        # R4: Syntactic terms
        r4_matches = self._find_matches(definition_lower, self.R4_PATTERNS)
        results.append(
            CheckResult(
                code="R4",
                name="No syntactic terms",
                passed=len(r4_matches) == 0,
                evidence=(
                    f"Found syntactic terms: {', '.join(r4_matches)}"
                    if r4_matches
                    else "No syntactic terms found"
                ),
                severity=Severity.RED_FLAG,
            )
        )

        return results

    def _find_matches(self, text: str, patterns: list[str]) -> list[str]:
        """Find all matching patterns in text.

        Args:
            text: The text to search (should be lowercase).
            patterns: List of regex patterns to match.

        Returns:
            List of matched strings.
        """
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)
        return matches


class CircularityChecker:
    """Checks for circularity in definitions.

    A definition is circular if it contains the term being defined,
    either directly or through morphological variants.
    """

    def check(self, definition: str, term: str) -> CheckResult:
        """Check if the term appears in its own definition.

        Args:
            definition: The definition text to check.
            term: The term being defined (e.g., "Verb Phrase").

        Returns:
            Check result for circularity.
        """
        definition_lower = definition.lower()
        term_lower = term.lower()

        # Generate variants of the term to check
        variants = self._generate_variants(term_lower)

        # Check for any variant in the definition
        found_variants = []
        for variant in variants:
            # Use word boundary matching to avoid false positives
            pattern = r"\b" + re.escape(variant) + r"\b"
            if re.search(pattern, definition_lower):
                found_variants.append(variant)

        passed = len(found_variants) == 0

        return CheckResult(
            code="C3",
            name="Non-circular",
            passed=passed,
            evidence=(
                f"Term appears in definition: {', '.join(found_variants)}"
                if found_variants
                else "Definition does not contain the term being defined"
            ),
            severity=Severity.REQUIRED,
        )

    def _generate_variants(self, term: str) -> list[str]:
        """Generate morphological variants of a term.

        Args:
            term: The term to generate variants for (lowercase).

        Returns:
            List of variants including the original term.
        """
        variants = [term]

        # Split multi-word terms and add individual words
        words = term.split()
        if len(words) > 1:
            variants.extend(words)

        # Add common morphological variants
        for word in words:
            # Plural forms
            if not word.endswith("s"):
                variants.append(word + "s")
            if word.endswith("s"):
                variants.append(word[:-1])

            # -ing forms
            if word.endswith("e"):
                variants.append(word[:-1] + "ing")
            elif not word.endswith("ing"):
                variants.append(word + "ing")

            # -ed forms
            if word.endswith("e"):
                variants.append(word + "d")
            elif not word.endswith("ed"):
                variants.append(word + "ed")

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen and len(v) > 2:  # Skip very short words
                seen.add(v)
                unique_variants.append(v)

        return unique_variants


class CustomRuleEvaluator:
    """Evaluates user-defined custom rules.

    Custom rules are regex-based patterns defined in configuration
    that check for project-specific anti-patterns or requirements.
    """

    def __init__(self, rules: list[CustomRule] | None = None) -> None:
        """Initialize with custom rules.

        Args:
            rules: List of custom rules to evaluate.
        """
        self.rules = rules or []

    def evaluate(self, definition: str) -> list[CheckResult]:
        """Evaluate definition against custom rules.

        Args:
            definition: The definition text to check.

        Returns:
            List of check results for custom rules.
        """
        results: list[CheckResult] = []

        for i, rule in enumerate(self.rules):
            if not rule.enabled:
                continue

            match = rule.matches(definition)

            # Map rule severity to Severity enum
            severity_map = {
                "error": Severity.RED_FLAG,
                "warning": Severity.QUALITY,
                "info": Severity.QUALITY,
            }
            severity = severity_map.get(rule.severity.value, Severity.QUALITY)

            results.append(
                CheckResult(
                    code=f"X{i + 1}",  # Custom rule codes are X1, X2, etc.
                    name=rule.name,
                    passed=match is None,
                    evidence=(
                        f"{rule.message} (matched: '{match.group()}')"
                        if match
                        else f"No match for custom rule: {rule.name}"
                    ),
                    severity=severity,
                )
            )

        return results


class ChecklistEvaluator:
    """Evaluates definitions against the Ralph Loop checklist.

    The checklist has four categories of checks:
    1. Core Requirements (C1-C4): Must all pass for PASS status
    2. ICE Requirements (I1-I3): Must pass if is_ice=True
    3. Quality Checks (Q1-Q3): Desirable but not required
    4. Red Flags (R1-R4): Any failure causes FAIL status
    5. Custom Rules (X1-Xn): User-defined pattern checks

    Scoring Logic:
    - PASS: All Core pass + All ICE pass (if applicable) + No Red Flags
    - FAIL: Any Core fails OR any Red Flag present
    - ITERATE: Core passes but Quality fails (needs refinement)
    """

    def __init__(self, custom_rules: list[CustomRule] | None = None) -> None:
        """Initialize the checklist evaluator.

        Args:
            custom_rules: Optional list of user-defined rules.
        """
        self.red_flag_detector = RedFlagDetector()
        self.circularity_checker = CircularityChecker()
        self.custom_rule_evaluator = CustomRuleEvaluator(custom_rules)

    def evaluate(
        self,
        definition: str,
        term: str,
        is_ice: bool,
        parent_class: str | None = None,
    ) -> list[CheckResult]:
        """Evaluate a definition against all applicable checks.

        Args:
            definition: The definition text to evaluate.
            term: The term being defined (for circularity check).
            is_ice: Whether this is an ICE (enables ICE-specific checks).
            parent_class: Parent class IRI (for genus check).

        Returns:
            List of all check results.
        """
        results: list[CheckResult] = []

        # Core Requirements (C1-C4)
        results.extend(self._check_core_requirements(definition, term, parent_class))

        # ICE Requirements (I1-I3) - only if is_ice
        if is_ice:
            results.extend(self._check_ice_requirements(definition))

        # Quality Checks (Q1-Q3)
        results.extend(self._check_quality(definition))

        # Red Flags (R1-R4)
        results.extend(self.red_flag_detector.check(definition))

        # Custom Rules (X1-Xn)
        results.extend(self.custom_rule_evaluator.evaluate(definition))

        return results

    def _check_core_requirements(
        self,
        definition: str,
        term: str,
        parent_class: str | None = None,
    ) -> list[CheckResult]:
        """Check core requirements C1-C4.

        C1: Genus present (mentions parent class or equivalent)
        C2: Differentia present (distinguishes from siblings)
        C3: Non-circular (term not in definition)
        C4: Single sentence (one complete thought)
        """
        results = []

        # C1: Genus present - check if definition has a genus structure
        # This is a heuristic check; full verification requires LLM
        has_genus = self._check_genus_structure(definition, parent_class)
        results.append(
            CheckResult(
                code="C1",
                name="Genus present",
                passed=has_genus,
                evidence=(
                    "Definition appears to have genus-differentia structure"
                    if has_genus
                    else "Definition may lack proper genus (parent class reference)"
                ),
                severity=Severity.REQUIRED,
            )
        )

        # C2: Differentia present - check for distinguishing characteristics
        has_differentia = self._check_differentia_structure(definition)
        results.append(
            CheckResult(
                code="C2",
                name="Differentia present",
                passed=has_differentia,
                evidence=(
                    "Definition includes distinguishing characteristics"
                    if has_differentia
                    else "Definition may lack differentia (distinguishing features)"
                ),
                severity=Severity.REQUIRED,
            )
        )

        # C3: Non-circular
        circularity_result = self.circularity_checker.check(definition, term)
        results.append(circularity_result)

        # C4: Single sentence
        is_single_sentence = self._check_single_sentence(definition)
        results.append(
            CheckResult(
                code="C4",
                name="Single sentence",
                passed=is_single_sentence,
                evidence=(
                    "Definition is a single, complete sentence"
                    if is_single_sentence
                    else "Definition should be a single sentence"
                ),
                severity=Severity.REQUIRED,
            )
        )

        return results

    def _check_ice_requirements(self, definition: str) -> list[CheckResult]:
        """Check ICE-specific requirements I1-I3.

        I1: Starts with "An ICE" or equivalent
        I2: Uses "denotes" or "is about"
        I3: Specifies what the ICE denotes
        """
        results = []
        definition_lower = definition.lower()

        # I1: Starts with ICE pattern
        ice_starters = [
            r"^an ice\b",
            r"^an information content entity\b",
            r"^a[n]? .* ice\b",
        ]
        starts_with_ice = any(
            re.match(pattern, definition_lower) for pattern in ice_starters
        )
        results.append(
            CheckResult(
                code="I1",
                name="ICE pattern start",
                passed=starts_with_ice,
                evidence=(
                    "Definition correctly starts with ICE pattern"
                    if starts_with_ice
                    else "ICE definitions should start with 'An ICE...'"
                ),
                severity=Severity.ICE_REQUIRED,
            )
        )

        # I2: Uses proper ICE verbs
        ice_verbs = [r"\bdenotes\b", r"\bis about\b", r"\bthat is about\b"]
        has_ice_verb = any(
            re.search(pattern, definition_lower) for pattern in ice_verbs
        )
        results.append(
            CheckResult(
                code="I2",
                name="Uses 'denotes' or 'is about'",
                passed=has_ice_verb,
                evidence=(
                    "Definition uses appropriate ICE verb (denotes/is about)"
                    if has_ice_verb
                    else "ICE definitions should use 'denotes' or 'is about'"
                ),
                severity=Severity.ICE_REQUIRED,
            )
        )

        # I3: Specifies denotation target
        # This is a heuristic - the definition should have content after the verb
        has_denotation = self._check_has_denotation_target(definition_lower)
        results.append(
            CheckResult(
                code="I3",
                name="Specifies denotation",
                passed=has_denotation,
                evidence=(
                    "Definition specifies what the ICE denotes"
                    if has_denotation
                    else "ICE definitions should specify what they denote"
                ),
                severity=Severity.ICE_REQUIRED,
            )
        )

        return results

    def _check_quality(self, definition: str) -> list[CheckResult]:
        """Check quality requirements Q1-Q3.

        Q1: Appropriate length (not too short or too long)
        Q2: Clear and readable
        Q3: Uses standard terminology
        """
        results = []

        # Q1: Appropriate length (20-300 characters is reasonable)
        length = len(definition)
        appropriate_length = 20 <= length <= 300
        results.append(
            CheckResult(
                code="Q1",
                name="Appropriate length",
                passed=appropriate_length,
                evidence=(
                    f"Definition length ({length} chars) is appropriate"
                    if appropriate_length
                    else f"Definition length ({length} chars) may be too {'short' if length < 20 else 'long'}"
                ),
                severity=Severity.QUALITY,
            )
        )

        # Q2: Clear and readable - check for overly complex structure
        is_readable = self._check_readability(definition)
        results.append(
            CheckResult(
                code="Q2",
                name="Clear and readable",
                passed=is_readable,
                evidence=(
                    "Definition is clear and readable"
                    if is_readable
                    else "Definition may be overly complex or unclear"
                ),
                severity=Severity.QUALITY,
            )
        )

        # Q3: Uses standard terminology - basic check
        uses_standard = self._check_standard_terminology(definition)
        results.append(
            CheckResult(
                code="Q3",
                name="Standard terminology",
                passed=uses_standard,
                evidence=(
                    "Definition uses standard ontology terminology"
                    if uses_standard
                    else "Definition may use non-standard terminology"
                ),
                severity=Severity.QUALITY,
            )
        )

        return results

    def _check_genus_structure(
        self, definition: str, parent_class: str | None
    ) -> bool:
        """Check if definition has a genus (parent class) reference."""
        definition_lower = definition.lower()

        # Check for common genus patterns
        genus_patterns = [
            r"^a[n]?\s+\w+",  # Starts with "A/An <something>"
            r"^the\s+\w+",  # Starts with "The <something>"
        ]

        has_genus_pattern = any(
            re.match(pattern, definition_lower) for pattern in genus_patterns
        )

        # If parent class is provided, check for reference
        if parent_class:
            parent_name = parent_class.split(":")[-1].lower()
            # Convert CamelCase to words
            parent_words = re.sub(r"([A-Z])", r" \1", parent_name).lower().split()
            has_parent_reference = any(
                word in definition_lower for word in parent_words if len(word) > 2
            )
            return has_genus_pattern or has_parent_reference

        return has_genus_pattern

    def _check_differentia_structure(self, definition: str) -> bool:
        """Check if definition has differentia (distinguishing features)."""
        # Look for patterns that indicate differentiation
        differentia_patterns = [
            r"\bthat\b",  # "An X that..."
            r"\bwhich\b",  # "An X which..."
            r"\bwhere\b",  # "An X where..."
            r"\bwhen\b",  # "An X when..."
            r"\bcharacterized by\b",
            r"\bdefined by\b",
            r"\bdistinguished by\b",
        ]

        definition_lower = definition.lower()
        return any(
            re.search(pattern, definition_lower) for pattern in differentia_patterns
        )

    def _check_single_sentence(self, definition: str) -> bool:
        """Check if definition is a single sentence."""
        # Count sentence-ending punctuation
        # Allow for abbreviations by checking for capital after period
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", definition.strip())
        return len(sentences) == 1

    def _check_has_denotation_target(self, definition_lower: str) -> bool:
        """Check if an ICE definition specifies what it denotes."""
        # Look for content after denotation verbs
        patterns = [
            r"\bdenotes\s+\w+",
            r"\bis about\s+\w+",
            r"\bthat is about\s+\w+",
        ]
        return any(re.search(pattern, definition_lower) for pattern in patterns)

    def _check_readability(self, definition: str) -> bool:
        """Check if definition is readable (not overly nested/complex)."""
        # Count nested clauses (parentheses, commas indicating clauses)
        paren_count = definition.count("(") + definition.count(")")
        comma_count = definition.count(",")

        # Heuristic: too many commas or parentheses indicates complexity
        return paren_count <= 4 and comma_count <= 5

    def _check_standard_terminology(self, definition: str) -> bool:
        """Check for standard ontology terminology."""
        # Check for non-standard terms that should be avoided
        non_standard = [
            r"\bstuff\b",
            r"\bthing\b(?!s)",  # "thing" but not "things" in context
            r"\bkind of\b",
            r"\bsort of\b",
            r"\btype of\b",  # Should use more precise terms
        ]

        definition_lower = definition.lower()
        return not any(
            re.search(pattern, definition_lower) for pattern in non_standard
        )

    def determine_status(self, results: list[CheckResult], is_ice: bool) -> VerifyStatus:
        """Determine the overall PASS/FAIL/ITERATE status.

        Args:
            results: List of all check results.
            is_ice: Whether this is an ICE definition.

        Returns:
            VerifyStatus indicating the outcome.

        Scoring Logic:
        - FAIL if any RED_FLAG check fails
        - FAIL if any REQUIRED check fails
        - FAIL if is_ice and any ICE_REQUIRED check fails
        - ITERATE if only QUALITY checks fail
        - PASS otherwise
        """
        # Group results by severity
        red_flags = [r for r in results if r.severity == Severity.RED_FLAG]
        required = [r for r in results if r.severity == Severity.REQUIRED]
        ice_required = [r for r in results if r.severity == Severity.ICE_REQUIRED]
        quality = [r for r in results if r.severity == Severity.QUALITY]

        # Check for red flags (auto-fail)
        if any(not r.passed for r in red_flags):
            return VerifyStatus.FAIL

        # Check required checks
        if any(not r.passed for r in required):
            return VerifyStatus.FAIL

        # Check ICE requirements if applicable
        if is_ice and any(not r.passed for r in ice_required):
            return VerifyStatus.FAIL

        # Check quality (iterate if failing)
        if any(not r.passed for r in quality):
            return VerifyStatus.ITERATE

        return VerifyStatus.PASS
