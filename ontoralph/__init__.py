"""OntoRalph: Iterative definition refinement for BFO/CCO ontologies.

OntoRalph implements the Ralph Loop technique for ontology quality assurance:
Generate → Critique → Refine → Verify until rigorous quality standards are met.
"""

__version__ = "1.0.0"
__author__ = "OntoRalph Contributors"

from ontoralph.core.models import ClassInfo, CheckResult, LoopResult

__all__ = [
    "__version__",
    "ClassInfo",
    "CheckResult",
    "LoopResult",
]
