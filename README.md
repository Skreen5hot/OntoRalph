# [NAME]

**Iterative definition refinement for BFO/CCO ontologies**

[NAME] implements the Ralph Loop technique for ontology quality assurance: 
rather than accepting first-draft definitions, it cycles through 
Generate → Critique → Refine → Verify until rigorous quality standards are met.

## Why?

Most ontology definitions fail basic quality checks:
- ❌ Circular ("A verb phrase is a phrase containing a verb")
- ❌ Epistemological ("An entity extracted from text")
- ❌ Missing aboutness ("An information content entity")
- ❌ Vague differentia ("A thing related to documents")

[NAME] catches these systematically and drives toward definitions that a 
BFO realist would approve.

## The Loop
```
[GENERATE] ──► [CRITIQUE] ──► [REFINE] ──► [VERIFY]
                                              │
                                         Pass? ──► Done
                                              │
                                         Loop (max 5x)
```

## Quick Start

1. Copy the prompt template
2. Fill in your class information  
3. Paste into Claude/GPT
4. Get back validated Turtle

## Features

- 📋 Condensed checklist derived from BFO/CCO best practices
- 🔄 Iterative refinement until convergence
- 🚫 Red-flag detection for common anti-patterns
- 📦 Copy-paste prompts for immediate use
- 📊 Batch processing for multiple classes

## Based On

- Basic Formal Ontology (BFO) 2020
- Common Core Ontologies (CCO)
- The "Ralph Wiggum Loop" technique (Huntley, 2025)
- Smithian realist critique methodology

## License

MIT
