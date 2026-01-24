"""Prompt templates for LLM interactions.

This module contains the prompt templates used for each phase of the Ralph Loop:
- GENERATE: Create an initial definition
- CRITIQUE: Evaluate a definition against the checklist
- REFINE: Improve a definition based on identified issues
"""

from ontoralph.core.models import CheckResult, ClassInfo

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
{', '.join(class_info.sibling_classes)}
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
