# Installation

## Requirements

- Python 3.11 or higher
- pip package manager

## Install from PyPI

```bash
pip install ontoralph
```

## Install from Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/ontoralph/ontoralph.git
cd ontoralph
pip install -e ".[dev]"
```

## Verify Installation

```bash
ontoralph --version
```

You should see the version number displayed.

## API Key Setup

OntoRalph requires an LLM API key for production use.

### Anthropic (Claude)

Set your Anthropic API key:

```bash
# Linux/macOS
export ANTHROPIC_API_KEY="your-api-key-here"

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your-api-key-here"

# Windows (CMD)
set ANTHROPIC_API_KEY=your-api-key-here
```

### OpenAI

Set your OpenAI API key:

```bash
# Linux/macOS
export OPENAI_API_KEY="your-api-key-here"

# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"

# Windows (CMD)
set OPENAI_API_KEY=your-api-key-here
```

## Testing Without API Key

Use the mock provider for testing without an API key:

```bash
ontoralph run --provider mock --iri ":Test" --label "Test Class" --parent "owl:Thing"
```

## Optional Dependencies

For documentation development:

```bash
pip install -e ".[docs]"
```

For running tests:

```bash
pip install -e ".[dev]"
pytest
```
