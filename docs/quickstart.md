# Quick Start

This guide will get you up and running with OntoRalph in 5 minutes.

## 1. Initialize a Project

Create configuration files in your project directory:

```bash
ontoralph init
```

This creates:
- `ontoralph.yaml` - Configuration file
- `templates/` - Custom prompt templates directory

## 2. Generate a Definition

Generate a definition for a single class:

```bash
ontoralph run \
  --iri ":PersonName" \
  --label "Person Name" \
  --parent "cco:DesignativeICE" \
  --ice \
  --provider claude
```

The tool will:
1. Generate an initial definition using the LLM
2. Check it against the definition checklist
3. Refine if issues are found
4. Output the result

## 3. Validate an Existing Definition

Check if a definition follows BFO/CCO patterns:

```bash
ontoralph validate "An ICE that denotes a person by their given name and surname." --ice
```

Output shows pass/fail status and any issues found.

## 4. Batch Process Multiple Classes

Create a YAML file with your classes:

```yaml
# classes.yaml
classes:
  - iri: ":PersonName"
    label: "Person Name"
    parent_class: "cco:DesignativeICE"
    is_ice: true

  - iri: ":OrganizationName"
    label: "Organization Name"
    parent_class: "cco:DesignativeICE"
    is_ice: true

  - iri: ":Address"
    label: "Address"
    parent_class: "cco:DescriptiveICE"
    is_ice: true
```

Run batch processing:

```bash
ontoralph batch classes.yaml --output results/
```

## 5. View Results

Results can be output in multiple formats:

```bash
# Turtle format (default)
ontoralph run --iri ":Test" --label "Test" --parent "owl:Thing" --format turtle

# Markdown report
ontoralph run --iri ":Test" --label "Test" --parent "owl:Thing" --format markdown

# JSON
ontoralph run --iri ":Test" --label "Test" --parent "owl:Thing" --format json
```

## Common Options

| Option | Description |
|--------|-------------|
| `--provider` | LLM provider: `claude`, `openai`, or `mock` |
| `--ice` | Mark class as an Information Content Entity |
| `--dry-run` | Show what would be done without making API calls |
| `--verbose` | Show detailed progress |
| `--quiet` | Suppress all output except errors |
| `--output` | Write output to file instead of stdout |

## Next Steps

- Read the [CLI Reference](cli-reference.md) for all commands
- Learn about [Configuration](configuration.md) options
- See the [API Reference](api/index.md) for programmatic use
