# CLI Reference

## Global Options

```
ontoralph [OPTIONS] COMMAND [ARGS]...
```

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--help` | Show help message and exit |

## Commands

### run

Generate or refine a definition for a single class.

```bash
ontoralph run [OPTIONS]
```

**Required Options:**

| Option | Description |
|--------|-------------|
| `--iri TEXT` | Class IRI (e.g., `:PersonName`) |
| `--label TEXT` | Human-readable label |
| `--parent TEXT` | Parent class IRI |

**Optional:**

| Option | Default | Description |
|--------|---------|-------------|
| `--ice / --no-ice` | `--no-ice` | Mark as Information Content Entity |
| `--siblings TEXT` | - | Comma-separated sibling IRIs |
| `--current TEXT` | - | Existing definition to improve |
| `--provider TEXT` | `claude` | LLM provider: `claude`, `openai`, `mock` |
| `--model TEXT` | - | Specific model to use |
| `--max-iterations INT` | 5 | Maximum refinement iterations |
| `--format TEXT` | `turtle` | Output format: `turtle`, `markdown`, `json` |
| `--output PATH` | - | Output file path (stdout if not set) |
| `--dry-run` | - | Show plan without executing |
| `--verbose` | - | Show detailed progress |
| `--quiet` | - | Suppress non-error output |

**Examples:**

```bash
# Basic usage with Claude
ontoralph run --iri ":PersonName" --label "Person Name" \
  --parent "cco:DesignativeICE" --ice

# With OpenAI and custom model
ontoralph run --iri ":Test" --label "Test" --parent "owl:Thing" \
  --provider openai --model gpt-4

# Dry run to preview
ontoralph run --iri ":Test" --label "Test" --parent "owl:Thing" --dry-run

# Refine existing definition
ontoralph run --iri ":Test" --label "Test" --parent "owl:Thing" \
  --current "An entity that represents something."
```

---

### batch

Process multiple classes from a YAML file.

```bash
ontoralph batch INPUT_FILE [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `INPUT_FILE` | Path to YAML file with class definitions |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--output PATH` | - | Output directory for results |
| `--provider TEXT` | `claude` | LLM provider |
| `--max-concurrency INT` | 3 | Parallel processing limit |
| `--continue-on-error` | - | Continue if individual class fails |
| `--resume` | - | Resume from previous run |
| `--verbose` | - | Show detailed progress |

**Input File Format:**

```yaml
classes:
  - iri: ":PersonName"
    label: "Person Name"
    parent_class: "cco:DesignativeICE"
    is_ice: true
    sibling_classes:
      - ":OrganizationName"

  - iri: ":OrganizationName"
    label: "Organization Name"
    parent_class: "cco:DesignativeICE"
    is_ice: true
```

**Examples:**

```bash
# Basic batch processing
ontoralph batch classes.yaml --output results/

# With resume on failure
ontoralph batch classes.yaml --output results/ --continue-on-error --resume

# High concurrency with OpenAI
ontoralph batch classes.yaml --provider openai --max-concurrency 5
```

---

### validate

Validate a definition against the checklist without LLM calls.

```bash
ontoralph validate DEFINITION [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `DEFINITION` | The definition text to validate |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--ice / --no-ice` | `--no-ice` | Check as ICE definition |
| `--term TEXT` | - | Term name for circularity check |
| `--verbose` | - | Show all check details |
| `--quiet` | - | Only show pass/fail status |

**Examples:**

```bash
# Validate ICE definition
ontoralph validate "An ICE that denotes a person by name." --ice

# Validate with term for circularity check
ontoralph validate "A person name is an ICE that denotes a person name." \
  --ice --term "Person Name"

# Quiet mode for scripting
ontoralph validate "An ICE that represents something." --ice --quiet
echo $?  # Exit code: 0=pass, 1=fail
```

---

### init

Initialize OntoRalph configuration files in current directory.

```bash
ontoralph init [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--output PATH` | `.` | Directory to create files in |
| `--force` | - | Overwrite existing files |

**Examples:**

```bash
# Initialize in current directory
ontoralph init

# Initialize in specific directory
ontoralph init --output my-project/

# Force overwrite existing config
ontoralph init --force
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - definition passes all checks |
| 1 | Failure - definition has red flags |
| 2 | Error - processing error occurred |

Use exit codes in scripts:

```bash
ontoralph validate "$DEFINITION" --ice --quiet
if [ $? -eq 0 ]; then
  echo "Definition passes"
else
  echo "Definition has issues"
fi
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for Claude provider |
| `OPENAI_API_KEY` | API key for OpenAI provider |
| `ONTORALPH_MAX_ITERATIONS` | Override default max iterations |
| `ONTORALPH_CONFIG` | Path to config file |
