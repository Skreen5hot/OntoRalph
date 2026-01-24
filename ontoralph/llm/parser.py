"""Response parser for LLM outputs.

This module provides utilities for extracting structured data from LLM responses,
including definition text and critique results.
"""

import json
import re
from typing import Any

from ontoralph.core.models import CheckResult, Severity
from ontoralph.llm.base import LLMResponseError


class ResponseParser:
    """Parser for extracting structured data from LLM responses."""

    # Mapping of check codes to severities
    SEVERITY_MAP: dict[str, Severity] = {
        "C1": Severity.REQUIRED,
        "C2": Severity.REQUIRED,
        "C3": Severity.REQUIRED,
        "C4": Severity.REQUIRED,
        "I1": Severity.ICE_REQUIRED,
        "I2": Severity.ICE_REQUIRED,
        "I3": Severity.ICE_REQUIRED,
        "Q1": Severity.QUALITY,
        "Q2": Severity.QUALITY,
        "Q3": Severity.QUALITY,
        "R1": Severity.RED_FLAG,
        "R2": Severity.RED_FLAG,
        "R3": Severity.RED_FLAG,
        "R4": Severity.RED_FLAG,
    }

    # Default check names
    CHECK_NAMES: dict[str, str] = {
        "C1": "Genus present",
        "C2": "Differentia present",
        "C3": "Non-circular",
        "C4": "Single sentence",
        "I1": "ICE pattern start",
        "I2": "Uses 'denotes' or 'is about'",
        "I3": "Specifies denotation",
        "Q1": "Appropriate length",
        "Q2": "Clear and readable",
        "Q3": "Standard terminology",
        "R1": "No process verbs",
        "R2": "Uses 'denotes' not 'represents'",
        "R3": "No functional language",
        "R4": "No syntactic terms",
    }

    def parse_definition(self, response: str) -> str:
        """Extract a definition from an LLM response.

        Args:
            response: The raw LLM response text.

        Returns:
            The extracted definition string.

        Raises:
            LLMResponseError: If no valid definition can be extracted.
        """
        if not response or not response.strip():
            raise LLMResponseError("Empty response from LLM")

        # Clean up the response
        text = response.strip()

        # Remove markdown code blocks if present
        text = re.sub(r"```\w*\n?", "", text)
        text = text.strip()

        # Remove surrounding quotes if present
        if (text.startswith('"') and text.endswith('"')) or (
            text.startswith("'") and text.endswith("'")
        ):
            text = text[1:-1].strip()

        # Remove common prefixes that LLMs sometimes add
        prefixes_to_remove = [
            "Definition:",
            "Here is the definition:",
            "The definition is:",
            "Refined definition:",
            "Here's the refined definition:",
        ]
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix) :].strip()

        # Validate we got something reasonable
        if len(text) < 10:
            raise LLMResponseError(
                f"Definition too short ({len(text)} chars): {text!r}. "
                "The LLM should generate a complete sentence definition."
            )

        if not text[0].isupper():
            # Try to find a sentence that starts with a capital letter
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                if sentence and sentence[0].isupper():
                    text = sentence
                    break

        return text

    def parse_critique(self, response: str) -> list[CheckResult]:
        """Extract critique results from an LLM response.

        Args:
            response: The raw LLM response text.

        Returns:
            List of CheckResult objects.

        Raises:
            LLMResponseError: If the response cannot be parsed.
        """
        if not response or not response.strip():
            raise LLMResponseError("Empty response from LLM")

        # Try to extract JSON from the response
        json_data = self._extract_json(response)

        if json_data is None:
            raise LLMResponseError(
                "Could not find valid JSON in LLM critique response. "
                "The LLM should return check results in JSON array format."
            )

        # Parse the JSON into CheckResult objects
        return self._parse_check_results(json_data)

    def _extract_json(self, text: str) -> Any | None:
        """Extract JSON data from text that may contain other content.

        Args:
            text: Text that may contain JSON.

        Returns:
            Parsed JSON data, or None if not found.
        """
        # Try to find JSON in code blocks first
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find a JSON array directly
        array_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", text)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try parsing the entire response as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        return None

    def _parse_check_results(self, data: Any) -> list[CheckResult]:
        """Parse JSON data into CheckResult objects.

        Args:
            data: Parsed JSON data (should be a list of check dicts).

        Returns:
            List of CheckResult objects.

        Raises:
            LLMResponseError: If the data format is invalid.
        """
        if not isinstance(data, list):
            raise LLMResponseError(f"Expected list of checks, got {type(data)}")

        results = []
        for item in data:
            if not isinstance(item, dict):
                continue

            code = item.get("code", "").upper()
            if not code or code not in self.SEVERITY_MAP:
                continue

            # Handle various ways LLMs might express pass/fail
            passed = item.get("passed")
            if passed is None:
                passed = item.get("pass", item.get("result", True))
            if isinstance(passed, str):
                passed = passed.lower() in ("true", "yes", "pass", "passed")

            # Get or default the check name
            name = item.get("name", self.CHECK_NAMES.get(code, code))

            # Get evidence
            evidence = item.get("evidence", item.get("reason", item.get("explanation", "")))
            if not evidence:
                evidence = "No evidence provided"

            results.append(
                CheckResult(
                    code=code,
                    name=name,
                    passed=bool(passed),
                    evidence=str(evidence),
                    severity=self.SEVERITY_MAP[code],
                )
            )

        if not results:
            raise LLMResponseError("No valid check results found in response")

        return results

    def validate_definition_format(self, definition: str, is_ice: bool = False) -> list[str]:
        """Validate basic format requirements for a definition.

        Args:
            definition: The definition to validate.
            is_ice: Whether this should be an ICE definition.

        Returns:
            List of warning messages (empty if valid).
        """
        warnings = []

        # Check for common issues
        if not definition:
            warnings.append("Definition is empty")
            return warnings

        if not definition[0].isupper():
            warnings.append("Definition should start with a capital letter")

        if not definition.rstrip().endswith("."):
            warnings.append("Definition should end with a period")

        # Count sentences (rough check)
        sentences = len(re.findall(r"[.!?]+(?:\s|$)", definition))
        if sentences > 1:
            warnings.append(f"Definition appears to have {sentences} sentences (should be 1)")

        # ICE-specific checks
        if is_ice:
            definition_lower = definition.lower()
            if not definition_lower.startswith("an ice") and not definition_lower.startswith(
                "an information content entity"
            ):
                warnings.append("ICE definition should start with 'An ICE' or 'An Information Content Entity'")

            if "represents" in definition_lower:
                warnings.append("ICE definitions should use 'denotes' instead of 'represents'")

        return warnings
