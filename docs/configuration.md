# Configuration

OntoRalph can be configured via YAML files, environment variables, or CLI options.

## Configuration Precedence

Settings are applied in this order (later overrides earlier):

1. **Built-in defaults**
2. **User config** (`~/.ontoralph.yaml`)
3. **Project config** (`./ontoralph.yaml`)
4. **Environment variables**
5. **CLI options**

## Configuration File

Create an `ontoralph.yaml` file in your project:

```yaml
# ontoralph.yaml

# LLM Provider Settings
llm:
  provider: claude           # claude, openai, or mock
  model: claude-sonnet-4-20250514  # specific model to use

# Loop Settings
loop:
  max_iterations: 5          # max refinement attempts
  use_hybrid_checking: true  # combine automated + LLM checks

# Output Settings
output:
  format: turtle             # turtle, markdown, or json
  include_comments: true     # add explanatory comments

# Checklist Settings
checklist:
  strictness: standard       # lenient, standard, or strict
  custom_rules: []           # additional rules (see below)

# Prompt Settings
prompts:
  templates_dir: ./templates  # directory for custom templates
```

## LLM Configuration

### Provider Options

```yaml
llm:
  # Use Claude (Anthropic)
  provider: claude
  model: claude-sonnet-4-20250514

  # Or use OpenAI
  # provider: openai
  # model: gpt-4

  # Or mock for testing
  # provider: mock
```

### API Keys

Set via environment variables:

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."
```

## Custom Rules

Add project-specific validation rules:

```yaml
checklist:
  custom_rules:
    - name: "No project jargon"
      pattern: '\b(Widget|Gadget|Frobulator)\b'
      message: "Avoid project-specific jargon"
      severity: warning  # error or warning

    - name: "No Latin abbreviations"
      pattern: '\b(e\.g\.|i\.e\.|etc\.)\b'
      message: "Spell out Latin abbreviations"
      severity: warning
```

### Rule Severity Levels

| Level | Effect |
|-------|--------|
| `error` | Fails the definition (like red flags) |
| `warning` | Triggers ITERATE status |

## Custom Prompt Templates

Override default prompts by placing template files in `templates/`:

### templates/generate.txt

```
Generate a formal ontology definition for ${label}.

IRI: ${iri}
Parent class: ${parent_class}
${siblings}

Requirements:
1. Follow genus-differentia pattern
2. Single sentence
3. Do not include "${label}" in the definition
```

### Template Variables

| Variable | Description |
|----------|-------------|
| `${iri}` | Class IRI |
| `${label}` | Class label |
| `${parent_class}` | Parent class IRI |
| `${is_ice}` | Whether class is ICE |
| `${siblings}` | Sibling class IRIs |
| `${current_definition}` | Existing definition |
| `${definition}` | Current definition (for critique/refine) |
| `${issues}` | Failed checks (for refine) |

## Strictness Levels

Control how strict the checklist is:

```yaml
checklist:
  strictness: standard  # lenient, standard, or strict
```

| Level | Behavior |
|-------|----------|
| `lenient` | Only red flags cause FAIL |
| `standard` | Red flags = FAIL, quality issues = ITERATE |
| `strict` | Any issue causes FAIL |

## Output Configuration

```yaml
output:
  format: turtle          # turtle, markdown, json
  include_comments: true  # add annotations
  include_metadata: true  # include generation info
```

## Environment Variables

Override config file settings:

| Variable | Overrides |
|----------|-----------|
| `ONTORALPH_MAX_ITERATIONS` | `loop.max_iterations` |
| `ONTORALPH_PROVIDER` | `llm.provider` |
| `ONTORALPH_MODEL` | `llm.model` |

## Example Configurations

### Minimal (testing)

```yaml
llm:
  provider: mock
```

### Development

```yaml
llm:
  provider: claude
loop:
  max_iterations: 3
output:
  format: markdown
```

### Production

```yaml
llm:
  provider: claude
  model: claude-sonnet-4-20250514
loop:
  max_iterations: 5
  use_hybrid_checking: true
checklist:
  strictness: strict
output:
  format: turtle
  include_comments: true
```

### CI/CD Pipeline

```yaml
llm:
  provider: claude
loop:
  max_iterations: 3
checklist:
  strictness: strict
  custom_rules:
    - name: "No WIP markers"
      pattern: '\b(TODO|FIXME|WIP)\b'
      message: "Remove work-in-progress markers"
      severity: error
```
