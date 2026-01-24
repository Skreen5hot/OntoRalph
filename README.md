# OntoRalph

[![PyPI version](https://badge.fury.io/py/ontoralph.svg)](https://badge.fury.io/py/ontoralph)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is OntoRalph?

OntoRalph helps you write better definitions for ontology terms. Think of it as a smart assistant that:

1. **Writes** a definition for your term
2. **Checks** if the definition follows best practices
3. **Improves** the definition if needed
4. **Repeats** until the definition is high quality

This process is called the "Ralph Loop" - it keeps refining definitions until they meet rigorous standards.

## Why Use OntoRalph?

Writing good ontology definitions is hard. Common problems include:

- **Circular definitions** - "A car is a vehicle that is car-like" (doesn't actually explain anything)
- **Too vague** - "A thing related to documents" (could mean anything)
- **Missing key details** - "An entity" (what KIND of entity?)

OntoRalph catches these problems automatically and helps create definitions that experts would approve.

---

## Getting Started (Easy Way - Web Interface)

The easiest way to use OntoRalph is through the web interface. No command line needed!

### Step 1: Install OntoRalph

If you don't have Python installed, download it first from [python.org](https://www.python.org/downloads/) (choose version 3.11 or newer).

Then open a terminal (Command Prompt on Windows, Terminal on Mac) and type:

```
pip install ontoralph
```

### Step 2: Start the Web Server

In the same terminal, type:

```
ontoralph serve
```

You should see a message saying the server is running.

### Step 3: Open the Web Interface

Open your web browser (Chrome, Firefox, Safari, etc.) and go to:

```
http://localhost:8000
```

### Step 4: Enter Your API Key

OntoRalph uses AI to generate definitions. You'll need an API key from one of these providers:

- **Claude (Anthropic)** - Get a key at [console.anthropic.com](https://console.anthropic.com/)
- **OpenAI** - Get a key at [platform.openai.com](https://platform.openai.com/)

Enter your API key in the Settings tab. Don't worry - your key stays in your browser and is never sent to our servers.

### Step 5: Generate Your First Definition

1. Go to the **Single** tab
2. Fill in the form:
   - **IRI**: A unique identifier for your term (e.g., `:PersonName`)
   - **Label**: The human-readable name (e.g., `Person Name`)
   - **Parent Class**: What broader category this belongs to (e.g., `cco:DesignativeICE`)
   - **Is ICE**: Check this if it's an Information Content Entity
3. Click **Run Ralph Loop**
4. Watch as OntoRalph generates, critiques, and refines the definition!

---

## Web Interface Features

### Single Mode
Process one term at a time. Great for learning how OntoRalph works or refining individual definitions.

### Batch Mode
Process many terms at once. Upload a list of terms and let OntoRalph work through them automatically. You can download all results as a ZIP file when done.

### History
All your runs are saved automatically. You can:
- Search through past definitions
- Filter by success/failure
- Re-run any previous definition
- Export your history as a backup

### Settings
- Choose your AI provider (Claude or OpenAI)
- Switch between light and dark themes
- Test without using API credits (Mock mode)

---

## Frequently Asked Questions

### Do I need to know how to code?
No! The web interface is designed to be easy to use without any programming knowledge.

### Is my API key safe?
Yes. Your API key is stored only in your browser's local storage. It's never sent to our servers - it goes directly from your browser to the AI provider.

### What's an IRI?
IRI stands for "Internationalized Resource Identifier." It's just a unique name for your term. You can use simple formats like `:MyTermName` or full URLs like `http://example.org/MyTermName`.

### What's an ICE?
ICE stands for "Information Content Entity." These are things like names, documents, or data - things that carry information. If your term represents information rather than a physical object, it's probably an ICE.

### How many iterations does it take?
Usually 1-3 iterations. Simple terms might pass on the first try, while complex terms might need more refinement. The maximum is 5 iterations by default.

### Can I use this without an API key?
Yes! Choose "Mock" as your provider in Settings. This uses fake AI responses for testing - great for learning how the interface works before using real AI credits.

---

## Troubleshooting

### "Server not found" or "Connection refused"

Make sure the server is running. Open a terminal and run:
```
ontoralph serve
```

Keep this terminal window open while using the web interface.

### "Invalid API key" error

- Double-check that you copied your full API key
- Make sure you selected the correct provider (Claude vs OpenAI)
- Check that your API key hasn't expired

### "Rate limit exceeded"

You've made too many requests too quickly. Wait a few minutes and try again. Consider processing terms in smaller batches.

### Web page won't load

- Try a different browser
- Make sure you're going to `http://localhost:8000` (not `https://`)
- Check that nothing else is using port 8000

### "pip not found"

Make sure Python is installed correctly:
1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, check the box that says "Add Python to PATH"
3. Restart your terminal and try again

---

## For Advanced Users & Developers

### Command Line Interface

If you prefer the command line:

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-api-key"
# or on Windows: set ANTHROPIC_API_KEY=your-api-key

# Process a single term
ontoralph run --iri ":PersonName" --label "Person Name" --parent "cco:DesignativeICE" --ice

# Validate an existing definition
ontoralph validate "An ICE that denotes a person by name." --ice

# Batch process from a YAML file
ontoralph batch classes.yaml --output results/
```

### Configuration File

Create `ontoralph.yaml` in your project folder:

```yaml
llm:
  provider: claude
  model: claude-sonnet-4-20250514

loop:
  max_iterations: 5

checklist:
  strictness: standard
```

### Available Commands

| Command | Description |
|---------|-------------|
| `ontoralph serve` | Start the web interface |
| `ontoralph run` | Process a single class (CLI) |
| `ontoralph batch` | Process multiple classes from YAML |
| `ontoralph validate` | Check a definition without AI |
| `ontoralph init` | Create configuration files |

### API Documentation

For programmatic access, see:
- [API Reference](https://ontoralph.github.io/ontoralph/api/)
- [CLI Reference](https://ontoralph.github.io/ontoralph/cli-reference/)

---

## How the Ralph Loop Works

```
[GENERATE] --> [CRITIQUE] --> [REFINE] --> [VERIFY]
     ^                                         |
     |                                    Pass? --> Done!
     |                                         |
     +-------------------- No ----------------+
                    (max 5 iterations)
```

1. **Generate**: AI writes an initial definition based on the term and its context
2. **Critique**: The definition is checked against quality rules (no circular logic, proper specificity, etc.)
3. **Refine**: If problems are found, AI improves the definition
4. **Verify**: Final check - if it passes, you're done! If not, loop back and try again

---

## Background

OntoRalph is built on established ontology standards:

- **BFO (Basic Formal Ontology)** - A foundational framework for scientific ontologies
- **CCO (Common Core Ontologies)** - Widely-used ontology patterns
- **The Ralph Loop technique** - An iterative refinement approach developed by Huntley (2025)

---

## Getting Help

- **Issues or bugs**: Report them at [GitHub Issues](https://github.com/anthropics/ontoralph/issues)
- **Questions**: Check the FAQ above or open a GitHub issue

---

## License

MIT License - free to use, modify, and distribute.
