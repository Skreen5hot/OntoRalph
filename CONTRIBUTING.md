# Contributing to OntoRalph

Thank you for your interest in contributing to OntoRalph! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/ontoralph.git
   cd ontoralph
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Verify installation:
   ```bash
   ontoralph --help
   pytest tests/
   ```

## Development Workflow

### Code Style

We use the following tools to maintain code quality:

- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pytest** for testing

Before committing, run:
```bash
ruff check .
ruff format .
mypy ontoralph
pytest tests/
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=ontoralph --cov-report=html

# Run specific test file
pytest tests/test_checklist.py

# Run tests matching a pattern
pytest tests/ -k "red_flag"
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(checklist): add circularity detection
fix(cli): handle missing parent class gracefully
docs(readme): add installation instructions
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request

### PR Checklist

- [ ] Tests added/updated for new functionality
- [ ] Documentation updated if needed
- [ ] Code passes linting (`ruff check .`)
- [ ] Code is formatted (`ruff format .`)
- [ ] Type hints added for new code
- [ ] Commit messages follow convention

## Project Structure

```
ontoralph/
├── __init__.py         # Package initialization, version
├── __main__.py         # Entry point for `python -m ontoralph`
├── cli.py              # Click CLI implementation
├── core/
│   ├── models.py       # Pydantic data models
│   ├── checklist.py    # Checklist evaluation logic
│   └── loop.py         # Ralph Loop controller
├── llm/
│   ├── base.py         # Abstract LLM provider
│   ├── claude.py       # Claude API integration
│   └── openai.py       # OpenAI API integration
├── output/
│   ├── turtle.py       # Turtle generation
│   └── report.py       # Report generation
└── config/
    └── settings.py     # Configuration models
```

## Testing Guidelines

### Test Structure

- Place tests in `tests/` directory
- Mirror the source structure (e.g., `tests/test_checklist.py` for `ontoralph/core/checklist.py`)
- Use descriptive test names: `test_red_flag_detector_catches_extracted`

### Test Categories

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test full workflows

### Writing Good Tests

```python
def test_red_flag_detector_catches_represents():
    """RedFlagDetector should flag 'represents' as R2 violation."""
    detector = RedFlagDetector()
    definition = "An ICE that represents a concept"

    results = detector.check(definition)

    assert any(r.code == "R2" and not r.passed for r in results)
```

## Reporting Issues

### Bug Reports

Include:
- OntoRalph version (`ontoralph --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/stack traces

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternatives considered

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Questions?

- Open a GitHub issue for bugs/features
- Start a GitHub discussion for questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
