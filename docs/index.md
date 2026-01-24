# OntoRalph Documentation

**OntoRalph** is a tool for generating and refining ontology definitions using the Ralph Loop technique. It leverages LLMs to iteratively improve definitions following BFO (Basic Formal Ontology) and CCO (Common Core Ontologies) patterns.

## Quick Navigation

- [Installation](installation.md) - How to install OntoRalph
- [Quick Start](quickstart.md) - Get started in 5 minutes
- [CLI Reference](cli-reference.md) - Complete command-line documentation
- [Configuration](configuration.md) - Configuration options and examples
- [API Reference](api/index.md) - Python API documentation

## What is the Ralph Loop?

The Ralph Loop is an iterative definition refinement process:

1. **Generate** - LLM creates an initial definition
2. **Critique** - Checklist evaluates the definition against BFO/CCO patterns
3. **Refine** - If issues found, LLM improves the definition
4. **Verify** - Final check determines pass/fail/iterate

This continues until the definition passes all checks or max iterations reached.

## Features

- **BFO/CCO Compliance** - Built-in checks for ontology best practices
- **ICE Pattern Support** - Special handling for Information Content Entities
- **Multiple LLM Providers** - Claude, OpenAI, or mock for testing
- **Batch Processing** - Process entire ontology files
- **Extensible** - Custom rules, templates, and configuration
- **CI/CD Ready** - Exit codes and quiet mode for automation

## Requirements

- Python 3.11+
- An LLM API key (Anthropic or OpenAI) for production use
