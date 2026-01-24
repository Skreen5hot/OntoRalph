# OntoRalph

[![PyPI version](https://badge.fury.io/py/ontoralph.svg)](https://badge.fury.io/py/ontoralph)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Iterative definition refinement for BFO/CCO ontologies**

OntoRalph implements the Ralph Loop technique for ontology quality assurance:
rather than accepting first-draft definitions, it cycles through
Generate → Critique → Refine → Verify until rigorous quality standards are met.

## Why?

Most ontology definitions fail basic quality checks:
- Circular ("A verb phrase is a phrase containing a verb")
- Epistemological ("An entity extracted from text")
- Missing aboutness ("An information content entity")
- Vague differentia ("A thing related to documents")

OntoRalph catches these systematically and drives toward definitions that a
BFO realist would approve.

## The Loop

```
[GENERATE] ──► [CRITIQUE] ──► [REFINE] ──► [VERIFY]
                                              │
                                         Pass? ──► Done
                                              │
                                         Loop (max 5x)
```

## Installation

```bash
pip install ontoralph
```

## Quick Start

### Set up API key

```bash
export ANTHROPIC_API_KEY="your-api-key"
# or
export OPENAI_API_KEY="your-api-key"
```

### Generate a definition

```bash
ontoralph run \
  --iri ":PersonName" \
  --label "Person Name" \
  --parent "cco:DesignativeICE" \
  --ice
```

### Validate an existing definition

```bash
ontoralph validate "An ICE that denotes a person by name." --ice
```

### Batch process from YAML

```bash
ontoralph batch classes.yaml --output results/
```

### Test without API key

```bash
ontoralph run --provider mock --iri ":Test" --label "Test" --parent "owl:Thing"
```

## Features

- **BFO/CCO Compliance** - Built-in checks for ontology best practices
- **ICE Pattern Support** - Special handling for Information Content Entities
- **Multiple LLM Providers** - Claude, OpenAI, or mock for testing
- **Batch Processing** - Process entire ontology files
- **Extensible** - Custom rules, templates, and configuration
- **CI/CD Ready** - Exit codes and quiet mode for automation

## Commands

| Command | Description |
|---------|-------------|
| `ontoralph run` | Process a single class |
| `ontoralph batch` | Process multiple classes from YAML |
| `ontoralph validate` | Check a definition without LLM |
| `ontoralph init` | Create config files |

## Configuration

Create `ontoralph.yaml`:

```yaml
llm:
  provider: claude
  model: claude-sonnet-4-20250514

loop:
  max_iterations: 5

checklist:
  strictness: standard
  custom_rules:
    - name: "No jargon"
      pattern: '\b(NLP|ML|AI)\b'
      message: "Avoid technical jargon"
```

## Documentation

- [Installation Guide](https://ontoralph.github.io/ontoralph/installation/)
- [Quick Start](https://ontoralph.github.io/ontoralph/quickstart/)
- [CLI Reference](https://ontoralph.github.io/ontoralph/cli-reference/)
- [Configuration](https://ontoralph.github.io/ontoralph/configuration/)
- [API Reference](https://ontoralph.github.io/ontoralph/api/)

## Based On

- Basic Formal Ontology (BFO) 2020
- Common Core Ontologies (CCO)
- The "Ralph Wiggum Loop" technique (Huntley, 2025)
- Smithian realist critique methodology

## License

MIT
