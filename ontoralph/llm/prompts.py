"""Prompt templates for LLM interactions.

This module contains the prompt templates used for each phase of the Ralph Loop:
- GENERATE: Create an initial definition
- CRITIQUE: Evaluate a definition against the checklist
- REFINE: Improve a definition based on identified issues

Supports custom templates via configuration for project-specific needs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from ontoralph.core.models import CheckResult, ClassInfo

if TYPE_CHECKING:
    from ontoralph.config.settings import PromptConfig

logger = logging.getLogger(__name__)

# System prompt establishing the ontology expert role
SYSTEM_PROMPT = """You are an expert ontologist specializing in BFO (Basic Formal Ontology) and CCO (Common Core Ontologies). You help create rigorous, formal definitions for ontology classes following the genus-differentia pattern.

Key principles:
1. Definitions must follow the Aristotelian genus-differentia pattern: "An X is a Y that Z"
2. For Information Content Entities (ICEs), use "An ICE that denotes..." or "An ICE that is about..."
3. Never use "represents" - ICEs "denote", they don't "represent"
4. Avoid process verbs (extracted, detected, identified, parsed) - definitions describe what something IS, not how it's created
5. Avoid functional language (serves to, used to, functions to) - definitions should be essential, not functional
6. Avoid syntactic terms (noun phrase, verb phrase, encoded as) - definitions should be ontological, not syntactic
7. The definition must be a single, complete sentence
8. The term being defined must not appear in the definition (non-circular)"""


def format_generate_prompt(class_info: ClassInfo) -> str:
    """Format the prompt for definition generation.

    Args:
        class_info: Information about the class to define.

    Returns:
        Formatted prompt string.
    """
    siblings_text = ""
    if class_info.sibling_classes:
        siblings_text = f"""
Sibling classes (the definition should distinguish from these):
{", ".join(class_info.sibling_classes)}
"""

    current_def_text = ""
    if class_info.current_definition:
        current_def_text = f"""
Current definition (to improve):
"{class_info.current_definition}"
"""

    ice_note = ""
    if class_info.is_ice:
        ice_note = """
IMPORTANT: This is an Information Content Entity (ICE). The definition MUST:
- Start with "An ICE that..." or "An Information Content Entity that..."
- Use "denotes" or "is about" to specify what the ICE is about
- NOT use "represents" (use "denotes" instead)
"""

    return f"""Generate a formal ontology definition for the following class:

Class IRI: {class_info.iri}
Label: {class_info.label}
Parent class: {class_info.parent_class}
{siblings_text}{current_def_text}{ice_note}
Requirements:
1. Follow the genus-differentia pattern
2. Reference the parent class as the genus
3. Include differentia that distinguishes this class from siblings
4. Be a single, complete sentence
5. Do not include the term "{class_info.label}" in the definition

Respond with ONLY the definition text, nothing else. Do not include quotes around it."""


def format_critique_prompt(class_info: ClassInfo, definition: str) -> str:
    """Format the prompt for definition critique.

    Args:
        class_info: Information about the class.
        definition: The definition to critique.

    Returns:
        Formatted prompt string.
    """
    ice_checks = ""
    if class_info.is_ice:
        ice_checks = """
ICE-Specific Requirements:
- I1: Does it start with "An ICE" or "An Information Content Entity"?
- I2: Does it use "denotes" or "is about"?
- I3: Does it specify what the ICE denotes?
"""

    return f"""Evaluate this ontology definition against the checklist:

Class: {class_info.label} ({class_info.iri})
Parent: {class_info.parent_class}
Is ICE: {class_info.is_ice}

Definition:
"{definition}"

Evaluate against these criteria and respond in JSON format:

Core Requirements:
- C1: Is the genus (parent class) present or implied?
- C2: Is there differentia (distinguishing characteristics)?
- C3: Is the definition non-circular (term "{class_info.label}" not in definition)?
- C4: Is it a single sentence?
{ice_checks}
Quality Checks:
- Q1: Is the length appropriate (not too short or too long)?
- Q2: Is it clear and readable?
- Q3: Does it use standard ontology terminology?

Red Flags (any of these is an automatic failure):
- R1: Does it use process verbs (extracted, detected, identified, parsed)?
- R2: Does it use "represents" instead of "denotes"?
- R3: Does it use functional language (serves to, used to, functions to)?
- R4: Does it use syntactic terms (noun phrase, verb phrase, encoded as)?

Respond with a JSON array of check results:
```json
[
  {{"code": "C1", "name": "Genus present", "passed": true, "evidence": "..."}},
  {{"code": "C2", "name": "Differentia present", "passed": true, "evidence": "..."}},
  ...
]
```

Include ALL checks (C1-C4, Q1-Q3, R1-R4{", I1-I3" if class_info.is_ice else ""}).
For each check, provide evidence explaining why it passed or failed."""


def format_refine_prompt(
    class_info: ClassInfo, definition: str, issues: list[CheckResult]
) -> str:
    """Format the prompt for definition refinement.

    Args:
        class_info: Information about the class.
        definition: The current definition.
        issues: List of failed checks to address.

    Returns:
        Formatted prompt string.
    """
    issues_text = "\n".join(
        f"- {issue.code} ({issue.name}): {issue.evidence}" for issue in issues
    )

    ice_note = ""
    if class_info.is_ice:
        ice_note = """
Remember: This is an ICE, so the definition must:
- Start with "An ICE that..." or "An Information Content Entity that..."
- Use "denotes" or "is about"
- NOT use "represents"
"""

    return f"""Refine this ontology definition to address the identified issues:

Class: {class_info.label} ({class_info.iri})
Parent: {class_info.parent_class}

Current definition:
"{definition}"

Issues to address:
{issues_text}
{ice_note}
Requirements:
1. Fix ALL identified issues
2. Maintain the genus-differentia structure
3. Keep it as a single sentence
4. Do not introduce new problems (especially red flags)
5. Do not include the term "{class_info.label}" in the definition

Respond with ONLY the refined definition text, nothing else. Do not include quotes around it."""


def format_class_context(class_info: ClassInfo) -> str:
    """Format class information for context in prompts.

    Args:
        class_info: The class information to format.

    Returns:
        Formatted context string.
    """
    lines = [
        f"IRI: {class_info.iri}",
        f"Label: {class_info.label}",
        f"Parent: {class_info.parent_class}",
        f"Is ICE: {class_info.is_ice}",
    ]

    if class_info.sibling_classes:
        lines.append(f"Siblings: {', '.join(class_info.sibling_classes)}")

    if class_info.current_definition:
        lines.append(f"Current definition: {class_info.current_definition}")

    return "\n".join(lines)


class PromptTemplateManager:
    """Manages custom prompt templates.

    Supports loading templates from:
    1. Configuration strings (inline templates)
    2. Template files in a specified directory
    3. Default built-in templates (fallback)

    Template variables:
    - ${iri}: Class IRI
    - ${label}: Class label
    - ${parent_class}: Parent class IRI
    - ${is_ice}: Whether class is an ICE
    - ${siblings}: Comma-separated sibling IRIs
    - ${current_definition}: Existing definition (if any)
    - ${definition}: Current definition (for critique/refine)
    - ${issues}: Formatted issues list (for refine)
    """

    def __init__(self, config: PromptConfig | None = None) -> None:
        """Initialize the template manager.

        Args:
            config: Prompt configuration from settings.
        """
        self.config = config
        self._templates: dict[str, str] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load custom templates from configuration."""
        if not self.config:
            return

        # Load from inline configuration
        if self.config.generate_template:
            self._templates["generate"] = self.config.generate_template
            logger.info("Loaded custom generate template from config")

        if self.config.critique_template:
            self._templates["critique"] = self.config.critique_template
            logger.info("Loaded custom critique template from config")

        if self.config.refine_template:
            self._templates["refine"] = self.config.refine_template
            logger.info("Loaded custom refine template from config")

        # Load from templates directory
        if self.config.templates_dir and self.config.templates_dir.exists():
            self._load_from_directory(self.config.templates_dir)

    def _load_from_directory(self, templates_dir: Path) -> None:
        """Load templates from a directory.

        Args:
            templates_dir: Directory containing template files.
        """
        template_files = {
            "generate": ["generate.txt", "generate.prompt", "generate_template.txt"],
            "critique": ["critique.txt", "critique.prompt", "critique_template.txt"],
            "refine": ["refine.txt", "refine.prompt", "refine_template.txt"],
            "system": ["system.txt", "system.prompt", "system_template.txt"],
        }

        for template_name, filenames in template_files.items():
            for filename in filenames:
                filepath = templates_dir / filename
                if filepath.exists():
                    try:
                        content = filepath.read_text(encoding="utf-8")
                        self._templates[template_name] = content
                        logger.info(f"Loaded {template_name} template from {filepath}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load template {filepath}: {e}")

    def get_system_prompt(self) -> str:
        """Get the system prompt.

        Returns:
            System prompt string.
        """
        return self._templates.get("system", SYSTEM_PROMPT)

    def format_generate(self, class_info: ClassInfo) -> str:
        """Format the generate prompt.

        Args:
            class_info: Class information.

        Returns:
            Formatted prompt.
        """
        if "generate" in self._templates:
            return self._apply_template(
                self._templates["generate"],
                class_info=class_info,
            )
        return format_generate_prompt(class_info)

    def format_critique(self, class_info: ClassInfo, definition: str) -> str:
        """Format the critique prompt.

        Args:
            class_info: Class information.
            definition: Definition to critique.

        Returns:
            Formatted prompt.
        """
        if "critique" in self._templates:
            return self._apply_template(
                self._templates["critique"],
                class_info=class_info,
                definition=definition,
            )
        return format_critique_prompt(class_info, definition)

    def format_refine(
        self,
        class_info: ClassInfo,
        definition: str,
        issues: list[CheckResult],
    ) -> str:
        """Format the refine prompt.

        Args:
            class_info: Class information.
            definition: Definition to refine.
            issues: Issues to address.

        Returns:
            Formatted prompt.
        """
        if "refine" in self._templates:
            issues_text = "\n".join(
                f"- {issue.code} ({issue.name}): {issue.evidence}" for issue in issues
            )
            return self._apply_template(
                self._templates["refine"],
                class_info=class_info,
                definition=definition,
                issues=issues_text,
            )
        return format_refine_prompt(class_info, definition, issues)

    def _apply_template(
        self,
        template_str: str,
        class_info: ClassInfo,
        definition: str = "",
        issues: str = "",
    ) -> str:
        """Apply variables to a template string.

        Args:
            template_str: Template with ${variable} placeholders.
            class_info: Class information.
            definition: Current definition (optional).
            issues: Formatted issues (optional).

        Returns:
            Filled template.
        """
        variables = {
            "iri": class_info.iri,
            "label": class_info.label,
            "parent_class": class_info.parent_class,
            "is_ice": str(class_info.is_ice),
            "siblings": ", ".join(class_info.sibling_classes)
            if class_info.sibling_classes
            else "",
            "current_definition": class_info.current_definition or "",
            "definition": definition,
            "issues": issues,
        }

        try:
            template = Template(template_str)
            return template.safe_substitute(variables)
        except Exception as e:
            logger.warning(f"Template substitution failed: {e}, using original")
            return template_str


# Global template manager instance (uses defaults)
_template_manager: PromptTemplateManager | None = None


def get_template_manager(config: PromptConfig | None = None) -> PromptTemplateManager:
    """Get or create the global template manager.

    Args:
        config: Optional configuration to use.

    Returns:
        Template manager instance.
    """
    global _template_manager
    if config is not None or _template_manager is None:
        _template_manager = PromptTemplateManager(config)
    return _template_manager
