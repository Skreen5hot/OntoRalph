# API Reference

This section documents the Python API for programmatic use of OntoRalph.

## Core Modules

### ontoralph.core

Core loop and checking functionality.

- [`RalphLoop`](#ralphloop) - Main loop orchestrator
- [`ChecklistEvaluator`](#checklistevaluator) - Definition checker
- [`ClassInfo`](#classinfo) - Class information model
- [`LoopResult`](#loopresult) - Loop result model

### ontoralph.llm

LLM provider integrations.

- [`ClaudeProvider`](#claudeprovider) - Anthropic Claude
- [`OpenAIProvider`](#openaiprovider) - OpenAI GPT
- [`MockProvider`](#mockprovider) - Testing mock

### ontoralph.batch

Batch processing functionality.

- [`BatchProcessor`](#batchprocessor) - Process multiple classes
- [`DependencyOrderer`](#dependencyorderer) - Order by hierarchy
- [`SiblingExclusivityChecker`](#siblingexclusivitychecker) - Check siblings

### ontoralph.output

Output generation.

- [`TurtleGenerator`](#turtlegenerator) - Generate Turtle RDF
- [`ReportGenerator`](#reportgenerator) - Generate reports

### ontoralph.config

Configuration management.

- [`Settings`](#settings) - Configuration model
- [`ConfigLoader`](#configloader) - Load from files

---

## Quick Example

```python
import asyncio
from ontoralph.core.loop import RalphLoop, LoopConfig
from ontoralph.core.models import ClassInfo
from ontoralph.llm import MockProvider  # or ClaudeProvider

async def main():
    # Create provider
    provider = MockProvider()

    # Configure loop
    config = LoopConfig(max_iterations=5)
    loop = RalphLoop(llm=provider, config=config)

    # Define class to process
    class_info = ClassInfo(
        iri=":PersonName",
        label="Person Name",
        parent_class="cco:DesignativeICE",
        is_ice=True,
    )

    # Run the loop
    result = await loop.run(class_info)

    print(f"Status: {result.status.value}")
    print(f"Definition: {result.final_definition}")

asyncio.run(main())
```

---

## RalphLoop

Main loop orchestrator for definition refinement.

```python
from ontoralph.core.loop import RalphLoop, LoopConfig, LoopHooks

# Create with default config
loop = RalphLoop(llm=provider)

# Create with custom config
config = LoopConfig(
    max_iterations=5,
    use_hybrid_checking=True,
)
loop = RalphLoop(llm=provider, config=config)

# Add event hooks
hooks = LoopHooks(
    on_iteration_start=lambda i, s: print(f"Iteration {i}"),
    on_generate=lambda d: print(f"Generated: {d}"),
)
loop = RalphLoop(llm=provider, hooks=hooks)

# Run the loop
result = await loop.run(class_info)
```

---

## ChecklistEvaluator

Evaluate definitions against the checklist.

```python
from ontoralph.core.checklist import ChecklistEvaluator

evaluator = ChecklistEvaluator()

# Evaluate a definition
results = evaluator.evaluate(
    definition="An ICE that denotes a person.",
    term="Person Name",
    is_ice=True,
)

# Get overall status
status = evaluator.determine_status(results, is_ice=True)
print(f"Status: {status.value}")

# Check individual results
for r in results:
    print(f"{r.code}: {'PASS' if r.passed else 'FAIL'}")
```

---

## ClassInfo

Data model for class information.

```python
from ontoralph.core.models import ClassInfo

class_info = ClassInfo(
    iri=":PersonName",
    label="Person Name",
    parent_class="cco:DesignativeICE",
    sibling_classes=[":OrganizationName"],
    is_ice=True,
    current_definition=None,  # Optional existing definition
)
```

---

## BatchProcessor

Process multiple classes in parallel.

```python
from ontoralph.batch import BatchProcessor, BatchConfig

config = BatchConfig(
    max_concurrency=3,
    continue_on_error=True,
)
processor = BatchProcessor(provider, config)

# Process classes
result = await processor.process(classes)

print(f"Passed: {result.progress.passed}")
print(f"Failed: {result.progress.failed}")
```

---

## TurtleGenerator

Generate Turtle RDF output.

```python
from ontoralph.output import TurtleGenerator

generator = TurtleGenerator()

# From loop result
turtle = generator.generate_from_result(result)

# From definition directly
turtle = generator.generate(
    iri=":PersonName",
    label="Person Name",
    definition="An ICE that denotes a person.",
    parent_class="cco:DesignativeICE",
)

print(turtle)
```

---

## Settings

Configuration management.

```python
from ontoralph.config import Settings, load_settings

# Load from file
settings = Settings.load_from_file("ontoralph.yaml")

# Load with auto-discovery
settings = load_settings()

# Access settings
print(settings.llm.provider)
print(settings.loop.max_iterations)
```

---

For complete API documentation with all parameters and return types, see the auto-generated reference below.

::: ontoralph.core.loop
::: ontoralph.core.checklist
::: ontoralph.core.models
::: ontoralph.llm
::: ontoralph.batch
::: ontoralph.output
::: ontoralph.config
