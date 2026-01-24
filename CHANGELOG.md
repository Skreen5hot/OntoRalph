# Changelog

All notable changes to OntoRalph will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-24

### Added

- **Ralph Loop Controller** - Iterative Generate → Critique → Refine → Verify cycle
- **Checklist Evaluator** - Automated definition quality checks
  - Core requirements (C1-C4): genus, differentia, circularity, single sentence
  - ICE requirements (I1-I3): ICE pattern, denotes/is about, specificity
  - Quality checks (Q1-Q3): length, clarity, terminology
  - Red flags (R1-R4): process verbs, represents, functional language, syntactic terms
- **LLM Providers** - Support for Claude, OpenAI, and mock testing
- **CLI Commands**
  - `ontoralph run` - Process single class definitions
  - `ontoralph batch` - Process multiple classes from YAML
  - `ontoralph validate` - Check definitions without LLM
  - `ontoralph init` - Create configuration files
- **Batch Processing**
  - Parallel processing with configurable concurrency
  - Dependency ordering (process parents before children)
  - Sibling exclusivity checking
  - Cross-class consistency validation
  - Resume from partial completion
- **Output Generation**
  - Turtle RDF format with SKOS definitions
  - Markdown reports with check details
  - JSON export for programmatic use
- **Configuration System**
  - YAML configuration files
  - Custom checklist rules with regex patterns
  - Custom prompt templates
  - Environment variable overrides
- **Documentation**
  - Installation guide
  - Quick start tutorial
  - CLI reference
  - Configuration guide
  - API documentation

### Based On

- Basic Formal Ontology (BFO) 2020
- Common Core Ontologies (CCO)
- The "Ralph Wiggum Loop" technique (Huntley, 2025)
