# OntoRalph Implementation Plan

**Version**: 1.0
**Date**: 2026-01-24
**Status**: Draft

---

## Executive Summary

This plan outlines the phased implementation of OntoRalph, a tool for iterative ontology definition refinement using the Ralph Loop technique. The tool will automate the Generate → Critique → Refine → Verify cycle for BFO/CCO-compliant definitions.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OntoRalph System                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │    INPUT     │    │    CORE      │    │   OUTPUT     │              │
│  │              │    │   ENGINE     │    │              │              │
│  │ • Class IRI  │───▶│              │───▶│ • Turtle     │              │
│  │ • Label      │    │ ┌──────────┐ │    │ • Report     │              │
│  │ • Parent     │    │ │ GENERATE │ │    │ • Log        │              │
│  │ • Siblings   │    │ └────┬─────┘ │    │              │              │
│  │ • Current    │    │      ▼       │    └──────────────┘              │
│  │   Definition │    │ ┌──────────┐ │                                  │
│  └──────────────┘    │ │ CRITIQUE │ │    ┌──────────────┐              │
│                      │ └────┬─────┘ │    │   CONFIG     │              │
│  ┌──────────────┐    │      ▼       │    │              │              │
│  │   LLM API    │◀──▶│ ┌──────────┐ │    │ • Max iters  │              │
│  │              │    │ │  REFINE  │ │    │ • Model      │              │
│  │ • Claude     │    │ └────┬─────┘ │    │ • Strictness │              │
│  │ • OpenAI     │    │      ▼       │    │              │              │
│  │ • Local LLM  │    │ ┌──────────┐ │    └──────────────┘              │
│  └──────────────┘    │ │  VERIFY  │ │                                  │
│                      │ └──────────┘ │                                  │
│                      └──────────────┘                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Repository Foundation

**Duration**: Week 1
**Goal**: Establish project structure, tooling, and development environment.

### Deliverables

| Item | Description |
|------|-------------|
| Repository structure | Standard Python project layout |
| Development environment | pyproject.toml, dependencies, virtual env |
| CI/CD pipeline | GitHub Actions for linting, testing |
| Core documentation | Contributing guide, code of conduct |
| CLI skeleton | Basic argparse/click structure |

### Tasks

- [ ] **1.1** Initialize repository with `.gitignore`, `LICENSE` (MIT)
- [ ] **1.2** Create Python package structure:
  ```
  ontoralph/
  ├── __init__.py
  ├── __main__.py
  ├── cli.py
  ├── core/
  │   ├── __init__.py
  │   ├── loop.py
  │   ├── checklist.py
  │   └── models.py
  ├── llm/
  │   ├── __init__.py
  │   ├── base.py
  │   ├── claude.py
  │   └── openai.py
  ├── output/
  │   ├── __init__.py
  │   ├── turtle.py
  │   └── report.py
  └── config/
      ├── __init__.py
      └── settings.py
  ```
- [ ] **1.3** Set up `pyproject.toml` with dependencies:
  - `click` (CLI framework)
  - `pydantic` (data validation)
  - `rdflib` (Turtle parsing/generation)
  - `anthropic` (Claude API)
  - `openai` (OpenAI API)
  - `rich` (terminal formatting)
  - `pytest` (testing)
- [ ] **1.4** Create GitHub Actions workflow for CI
- [ ] **1.5** Implement basic CLI entry point with `--help`
- [ ] **1.6** Write `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC1.1 | `pip install -e .` succeeds without errors | Run installation in clean venv |
| AC1.2 | `ontoralph --help` displays usage information | Run CLI command |
| AC1.3 | `pytest` runs (even with 0 tests) without errors | Run test suite |
| AC1.4 | GitHub Actions CI passes on push | Check Actions tab |
| AC1.5 | All core package imports work | `python -c "import ontoralph"` |

---

## Phase 2: Data Models & Checklist Engine

**Duration**: Week 2
**Goal**: Implement the data structures and checklist evaluation logic.

### Deliverables

| Item | Description |
|------|-------------|
| Pydantic models | ClassInfo, Definition, CheckResult, LoopState |
| Checklist evaluator | Automated rule checking (where possible) |
| Red flag detector | Pattern-based anti-pattern detection |
| Scoring logic | PASS/FAIL/ITERATE determination |

### Tasks

- [ ] **2.1** Define `ClassInfo` model:
  ```python
  class ClassInfo(BaseModel):
      iri: str
      label: str
      parent_class: str
      sibling_classes: list[str]
      is_ice: bool
      current_definition: str | None
  ```
- [ ] **2.2** Define `CheckResult` model:
  ```python
  class CheckResult(BaseModel):
      code: str  # e.g., "C1", "I2", "R3"
      name: str
      passed: bool
      evidence: str
      severity: Literal["required", "ice_required", "quality", "red_flag"]
  ```
- [ ] **2.3** Define `LoopIteration` and `LoopState` models
- [ ] **2.4** Implement `RedFlagDetector` class:
  - R1: Detect "extracted", "detected", "identified", "parsed"
  - R2: Detect "represents" (should be "denotes")
  - R3: Detect "serves to", "used to", "functions to"
  - R4: Detect "noun phrase", "verb phrase", "encoded as"
- [ ] **2.5** Implement `CircularityChecker`:
  - Check if term appears in definition
  - Check for synonyms/morphological variants
- [ ] **2.6** Implement `ChecklistEvaluator` orchestrator
- [ ] **2.7** Implement scoring logic:
  - PASS: All Core + All applicable ICE + No Red Flags
  - FAIL: Any Core fails OR any Red Flag present
  - ITERATE: Quality checks fail but Core passes
- [ ] **2.8** Write unit tests for all checkers

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC2.1 | `RedFlagDetector` catches all 4 red flag categories | Unit tests with known bad definitions |
| AC2.2 | `CircularityChecker` detects term-in-definition | Test "A verb phrase is a phrase with a verb" |
| AC2.3 | Scoring returns correct PASS/FAIL/ITERATE | Test matrix of definition qualities |
| AC2.4 | Models serialize/deserialize to JSON correctly | Round-trip tests |
| AC2.5 | ≥90% code coverage on checklist module | pytest-cov report |

---

## Phase 3: LLM Integration

**Duration**: Weeks 3-4
**Goal**: Integrate with LLM APIs for generation, critique, and refinement.

### Deliverables

| Item | Description |
|------|-------------|
| LLM abstraction layer | Provider-agnostic interface |
| Claude integration | Anthropic API client |
| OpenAI integration | OpenAI API client |
| Prompt templates | Structured prompts for each loop phase |
| Response parser | Extract structured data from LLM responses |

### Tasks

- [ ] **3.1** Define `LLMProvider` abstract base class:
  ```python
  class LLMProvider(ABC):
      @abstractmethod
      async def generate(self, class_info: ClassInfo) -> str: ...

      @abstractmethod
      async def critique(self, class_info: ClassInfo, definition: str) -> list[CheckResult]: ...

      @abstractmethod
      async def refine(self, class_info: ClassInfo, definition: str, issues: list[CheckResult]) -> str: ...
  ```
- [ ] **3.2** Create prompt templates in `prompts/` directory:
  - `generate.md` - Initial definition generation
  - `critique.md` - Checklist evaluation
  - `refine.md` - Issue-driven refinement
- [ ] **3.3** Implement `ClaudeProvider`:
  - API key management (env var, config file)
  - Retry logic with exponential backoff
  - Token counting and cost tracking
- [ ] **3.4** Implement `OpenAIProvider` (same interface)
- [ ] **3.5** Implement `ResponseParser`:
  - Extract definition text from generation response
  - Parse checklist results from critique response
  - Handle malformed responses gracefully
- [ ] **3.6** Add configuration for model selection:
  ```yaml
  llm:
    provider: claude  # or openai
    model: claude-sonnet-4-20250514
    max_tokens: 2000
    temperature: 0.3
  ```
- [ ] **3.7** Implement mock provider for testing
- [ ] **3.8** Write integration tests (with mocked API responses)

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC3.1 | Claude provider successfully generates definition | Integration test with real API (optional, gated) |
| AC3.2 | OpenAI provider successfully generates definition | Integration test with real API (optional, gated) |
| AC3.3 | Response parser extracts definition from ≥95% of valid responses | Test against 20+ sample responses |
| AC3.4 | API errors result in graceful failure with clear message | Test timeout, auth failure, rate limit |
| AC3.5 | Mock provider allows full loop testing without API calls | Unit tests use mock |
| AC3.6 | Cost tracking reports tokens used per iteration | Check logs after run |

---

## Phase 4: Ralph Loop Controller

**Duration**: Week 5
**Goal**: Implement the core loop orchestration logic.

### Deliverables

| Item | Description |
|------|-------------|
| Loop controller | Orchestrates Generate → Critique → Refine → Verify |
| Iteration tracking | Maintains state across iterations |
| Convergence detection | Determines when to stop |
| Event hooks | Callbacks for logging, UI updates |

### Tasks

- [ ] **4.1** Implement `RalphLoop` class:
  ```python
  class RalphLoop:
      def __init__(self, llm: LLMProvider, config: LoopConfig): ...

      async def run(self, class_info: ClassInfo) -> LoopResult:
          """Execute the full loop until PASS or max iterations."""

      async def step(self, state: LoopState) -> LoopState:
          """Execute one iteration of the loop."""
  ```
- [ ] **4.2** Implement iteration state management:
  - Track current iteration number
  - Store history of definitions and check results
  - Record timestamps for performance analysis
- [ ] **4.3** Implement convergence detection:
  - Primary: All required checks pass
  - Secondary: No improvement after N iterations
  - Tertiary: Max iterations reached
- [ ] **4.4** Implement event hooks:
  ```python
  class LoopHooks:
      on_iteration_start: Callable[[int, LoopState], None]
      on_generate: Callable[[str], None]
      on_critique: Callable[[list[CheckResult]], None]
      on_refine: Callable[[str], None]
      on_verify: Callable[[VerifyResult], None]
      on_complete: Callable[[LoopResult], None]
  ```
- [ ] **4.5** Implement hybrid checking:
  - Run automated checks first (red flags, circularity)
  - Only call LLM for checks requiring semantic understanding
- [ ] **4.6** Add detailed logging throughout loop
- [ ] **4.7** Write end-to-end tests with mock LLM

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC4.1 | Loop terminates on PASS within max iterations | Test with known-good input |
| AC4.2 | Loop terminates at max iterations if no convergence | Test with impossible-to-satisfy input |
| AC4.3 | All hooks fire at correct points in loop | Test with hook counters |
| AC4.4 | Loop state is fully recoverable from JSON | Serialize mid-loop, deserialize, continue |
| AC4.5 | Hybrid checking reduces API calls by ≥30% | Compare with LLM-only baseline |

---

## Phase 5: Output Generation

**Duration**: Week 6
**Goal**: Generate valid Turtle output and quality reports.

### Deliverables

| Item | Description |
|------|-------------|
| Turtle generator | Produces valid OWL/Turtle syntax |
| Turtle validator | Validates output against RDF spec |
| Report generator | Markdown/HTML iteration reports |
| Diff generator | Shows changes between iterations |

### Tasks

- [ ] **5.1** Implement `TurtleGenerator`:
  ```python
  class TurtleGenerator:
      def generate(self, class_info: ClassInfo, definition: str) -> str:
          """Generate Turtle block for a class definition."""
  ```
- [ ] **5.2** Use `rdflib` for Turtle generation:
  - Proper IRI handling
  - Correct literal escaping (especially multi-line strings)
  - Standard prefix declarations
- [ ] **5.3** Implement Turtle validation:
  - Parse generated Turtle with rdflib
  - Check for syntax errors
  - Validate against OWL constraints (optional)
- [ ] **5.4** Implement `ReportGenerator`:
  - Markdown output showing each iteration
  - Checklist results with ✓/✗ indicators
  - Final definition highlighted
- [ ] **5.5** Implement iteration diff:
  - Show what changed between iterations
  - Highlight added/removed phrases
- [ ] **5.6** Add export formats:
  - `.ttl` - Turtle file
  - `.md` - Markdown report
  - `.json` - Machine-readable log
- [ ] **5.7** Write output validation tests

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC5.1 | Generated Turtle parses without errors in rdflib | Parse test on 50+ outputs |
| AC5.2 | Generated Turtle parses in Protégé | Manual test with Protégé |
| AC5.3 | Multi-line definitions use correct `"""` escaping | Test with definitions containing quotes |
| AC5.4 | Report clearly shows iteration progression | Visual inspection |
| AC5.5 | JSON output can reconstruct full loop history | Round-trip test |

---

## Phase 6: CLI Implementation

**Duration**: Week 7
**Goal**: Full-featured command-line interface.

### Deliverables

| Item | Description |
|------|-------------|
| Single-class mode | Process one class interactively |
| Batch mode | Process multiple classes from file |
| Watch mode | Re-run on file changes |
| Progress display | Rich terminal output |

### Tasks

- [ ] **6.1** Implement `ontoralph run` command:
  ```bash
  ontoralph run \
    --iri ":VerbPhrase" \
    --label "Verb Phrase" \
    --parent "cco:InformationContentEntity" \
    --siblings ":NounPhrase,:DiscourseReferent" \
    --ice \
    --definition "An ICE representing a verb phrase."
  ```
- [ ] **6.2** Implement `ontoralph batch` command:
  ```bash
  ontoralph batch classes.yaml --output results/
  ```
- [ ] **6.3** Define batch input format (YAML):
  ```yaml
  classes:
    - iri: ":VerbPhrase"
      label: "Verb Phrase"
      parent: "cco:InformationContentEntity"
      siblings: [":NounPhrase", ":DiscourseReferent"]
      is_ice: true
      definition: "An ICE representing a verb phrase."
  ```
- [ ] **6.4** Implement rich progress display:
  - Current iteration indicator
  - Checklist status (live updating)
  - Spinner during LLM calls
- [ ] **6.5** Implement `ontoralph validate` command:
  - Check definition against checklist without refinement
  - Output issues found
- [ ] **6.6** Implement `ontoralph init` command:
  - Generate sample config file
  - Generate sample batch input
- [ ] **6.7** Add `--verbose` and `--quiet` flags
- [ ] **6.8** Add `--dry-run` flag (show what would happen)
- [ ] **6.9** Write CLI integration tests

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC6.1 | `ontoralph run` processes single class end-to-end | Manual test |
| AC6.2 | `ontoralph batch` processes 10+ classes from YAML | Test with sample file |
| AC6.3 | Progress display updates in real-time | Visual verification |
| AC6.4 | `--dry-run` produces no API calls | Check with mocked provider |
| AC6.5 | `--help` on all commands shows clear usage | Run help on each command |
| AC6.6 | Exit codes: 0=success, 1=failure, 2=partial | Test each scenario |

---

## Phase 7: Batch Processing & Sibling Analysis

**Duration**: Week 8
**Goal**: Advanced batch features including cross-class analysis.

### Deliverables

| Item | Description |
|------|-------------|
| Parallel processing | Process multiple classes concurrently |
| Sibling exclusivity checker | Verify mutual exclusivity across siblings |
| Dependency ordering | Process classes in correct order |
| Batch report | Consolidated results across all classes |

### Tasks

- [ ] **7.1** Implement parallel batch processing:
  - Configurable concurrency limit
  - Respect API rate limits
  - Handle partial failures gracefully
- [ ] **7.2** Implement `SiblingExclusivityChecker`:
  ```python
  class SiblingExclusivityChecker:
      def check(self, definitions: dict[str, str]) -> list[ExclusivityIssue]:
          """Check if sibling definitions are mutually exclusive."""
  ```
- [ ] **7.3** Implement dependency ordering:
  - Parse parent relationships
  - Topological sort
  - Process parents before children
- [ ] **7.4** Implement cross-class consistency checks:
  - Terminology consistency
  - Pattern consistency
  - No contradictions between definitions
- [ ] **7.5** Implement batch report generator:
  - Summary statistics (pass/fail counts)
  - Per-class results
  - Cross-class issues
- [ ] **7.6** Add `--continue-on-error` flag for batch mode
- [ ] **7.7** Implement batch resume (skip already-processed)

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC7.1 | Batch of 20 classes completes in <5 min (with parallelism) | Timed test |
| AC7.2 | Sibling exclusivity check catches overlapping definitions | Test with known-overlapping pair |
| AC7.3 | Classes processed in correct dependency order | Test with parent-child pairs |
| AC7.4 | Partial batch failure doesn't lose completed results | Kill mid-batch, check output |
| AC7.5 | Batch report shows aggregate statistics | Visual inspection |

---

## Phase 8: Configuration & Extensibility

**Duration**: Week 9
**Goal**: Flexible configuration and plugin architecture.

### Deliverables

| Item | Description |
|------|-------------|
| Config file support | YAML/TOML configuration |
| Custom checklist rules | User-defined checks |
| Custom prompt templates | Override default prompts |
| Plugin system | Extend functionality |

### Tasks

- [ ] **8.1** Implement configuration file loading:
  ```yaml
  # ontoralph.yaml
  llm:
    provider: claude
    model: claude-sonnet-4-20250514

  loop:
    max_iterations: 5
    fail_fast: false

  output:
    format: turtle
    include_comments: true

  checklist:
    strictness: standard  # or strict, lenient
    custom_rules:
      - name: "No jargon"
        pattern: "\\b(NLP|ML|AI)\\b"
        message: "Avoid technical jargon in definitions"
  ```
- [ ] **8.2** Implement config precedence:
  1. CLI flags (highest)
  2. Environment variables
  3. Project config file
  4. User config file (~/.ontoralph.yaml)
  5. Defaults (lowest)
- [ ] **8.3** Implement custom checklist rules:
  - Regex-based pattern matching
  - Custom severity levels
  - Enable/disable per-project
- [ ] **8.4** Implement custom prompt templates:
  - Override path in config
  - Template variable substitution
  - Validation on load
- [ ] **8.5** Implement plugin discovery:
  - Entry points mechanism
  - `ontoralph.plugins` namespace
- [ ] **8.6** Document extension points

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC8.1 | Config file overrides defaults | Test with custom max_iterations |
| AC8.2 | CLI flags override config file | Test flag vs config conflict |
| AC8.3 | Custom rule triggers on matching definition | Test with custom regex rule |
| AC8.4 | Custom prompt template used when configured | Check LLM input in logs |
| AC8.5 | Invalid config produces clear error message | Test with malformed YAML |

---

## Phase 9: Testing & Documentation

**Duration**: Week 10
**Goal**: Comprehensive testing and user documentation.

### Deliverables

| Item | Description |
|------|-------------|
| Unit test suite | ≥90% coverage |
| Integration test suite | End-to-end scenarios |
| User documentation | Installation, usage, examples |
| API documentation | For library use |
| Tutorial | Step-by-step guide |

### Tasks

- [ ] **9.1** Achieve ≥90% unit test coverage
- [ ] **9.2** Create integration test suite:
  - Happy path (definition passes on first try)
  - Multi-iteration convergence
  - Max iterations reached
  - API failure handling
  - Batch processing
- [ ] **9.3** Create golden file tests:
  - Known inputs → expected outputs
  - Regression detection
- [ ] **9.4** Write user documentation:
  - Installation guide
  - Quick start
  - CLI reference
  - Configuration reference
  - Troubleshooting
- [ ] **9.5** Write API documentation:
  - Module docstrings
  - Type hints
  - Usage examples
- [ ] **9.6** Create tutorial:
  - "Your first definition refinement"
  - "Batch processing an ontology"
  - "Customizing the checklist"
- [ ] **9.7** Add docstrings to all public functions
- [ ] **9.8** Generate API docs with mkdocs/sphinx

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC9.1 | Unit test coverage ≥90% | pytest-cov report |
| AC9.2 | All integration tests pass | CI pipeline |
| AC9.3 | Golden file tests detect regressions | Intentionally break, verify caught |
| AC9.4 | New user can install and run in <5 minutes following docs | User test |
| AC9.5 | API docs build without warnings | mkdocs build |
| AC9.6 | Tutorial works end-to-end | Follow tutorial manually |

---

## Phase 10: Polish & Release

**Duration**: Week 11-12
**Goal**: Production readiness and initial release.

### Deliverables

| Item | Description |
|------|-------------|
| Performance optimization | Response time improvements |
| Error handling polish | Clear, actionable error messages |
| PyPI package | Published to PyPI |
| Release automation | GitHub releases, changelog |
| Launch materials | Blog post, demo video |

### Tasks

- [ ] **10.1** Performance profiling and optimization:
  - Identify bottlenecks
  - Optimize hot paths
  - Add caching where appropriate
- [ ] **10.2** Error message review:
  - All errors have actionable guidance
  - No stack traces in normal operation
  - Debug mode for verbose errors
- [ ] **10.3** Security review:
  - API key handling
  - No secrets in logs
  - Input sanitization
- [ ] **10.4** Prepare PyPI package:
  - Package metadata complete
  - README renders correctly
  - Classifiers accurate
- [ ] **10.5** Set up release automation:
  - Version bumping
  - Changelog generation
  - GitHub release creation
  - PyPI upload
- [ ] **10.6** Create demo video (2-3 minutes)
- [ ] **10.7** Write announcement blog post
- [ ] **10.8** Tag v1.0.0 release

### Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC10.1 | Single definition processes in <30s (excluding LLM time) | Timed test |
| AC10.2 | All error messages include remediation steps | Error message audit |
| AC10.3 | `pip install ontoralph` works from PyPI | Test in clean environment |
| AC10.4 | `ontoralph --version` shows correct version | Run command |
| AC10.5 | GitHub release includes changelog and assets | Check release page |
| AC10.6 | Demo video demonstrates core workflow | Watch video |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM output inconsistency | High | Medium | Structured output prompts, response validation, retry logic |
| API rate limits | Medium | Medium | Configurable concurrency, backoff, caching |
| Turtle generation edge cases | Medium | Low | Comprehensive test suite, rdflib validation |
| Checklist false positives | Medium | Medium | Tunable strictness, override mechanism |
| Scope creep | High | High | Strict phase gating, MVP focus |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Definition pass rate | ≥80% pass within 3 iterations | Track across user base |
| Time to first PASS | <2 minutes median | Telemetry (opt-in) |
| User adoption | 100 GitHub stars in 3 months | GitHub metrics |
| Documentation quality | <5% support questions answered in docs | Issue analysis |
| Reliability | 99% runs complete without crash | Error tracking |

---

## Timeline Summary

```
Week 1:   Phase 1 - Repository Foundation
Week 2:   Phase 2 - Data Models & Checklist Engine
Week 3-4: Phase 3 - LLM Integration
Week 5:   Phase 4 - Ralph Loop Controller
Week 6:   Phase 5 - Output Generation
Week 7:   Phase 6 - CLI Implementation
Week 8:   Phase 7 - Batch Processing & Sibling Analysis
Week 9:   Phase 8 - Configuration & Extensibility
Week 10:  Phase 9 - Testing & Documentation
Week 11-12: Phase 10 - Polish & Release
```

**Total Duration**: 12 weeks to v1.0.0

---

## Appendix A: Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.11+ | Ecosystem, LLM library support |
| CLI Framework | Click | Mature, well-documented |
| Data Validation | Pydantic v2 | Type safety, serialization |
| RDF Handling | rdflib | Standard Python RDF library |
| LLM (Claude) | anthropic | Official SDK |
| LLM (OpenAI) | openai | Official SDK |
| Terminal UI | Rich | Beautiful output, progress bars |
| Testing | pytest + pytest-cov | Standard, good coverage tools |
| Docs | MkDocs + Material | Modern, searchable docs |
| Packaging | Hatch | Modern Python packaging |

---

## Appendix B: Sample Test Cases

### Red Flag Detection

```python
@pytest.mark.parametrize("definition,expected_flags", [
    ("An ICE extracted from text", ["R1"]),
    ("An ICE that represents meaning", ["R2"]),
    ("An ICE that serves to link entities", ["R3"]),
    ("An ICE encoded as a noun phrase", ["R4"]),
    ("An ICE extracted from text that represents a verb phrase", ["R1", "R2", "R4"]),
    ("An ICE that denotes an occurrent", []),  # Clean
])
def test_red_flag_detection(definition, expected_flags):
    detector = RedFlagDetector()
    results = detector.check(definition)
    assert [r.code for r in results if not r.passed] == expected_flags
```

### Loop Convergence

```python
async def test_loop_converges_on_good_input():
    mock_llm = MockLLMProvider(
        generate_response="An ICE that is about an occurrent as introduced in discourse...",
        critique_response=[CheckResult(code="C1", passed=True, ...)],
    )
    loop = RalphLoop(mock_llm, config)
    result = await loop.run(sample_class_info)

    assert result.status == "PASS"
    assert result.iterations <= 3
```

---

## Appendix C: Definition Quality Rubric

For manual verification of output quality:

| Score | Criteria |
|-------|----------|
| **5 - Excellent** | Passes all checks, could appear in published BFO ontology |
| **4 - Good** | Passes all required checks, minor style issues |
| **3 - Acceptable** | Passes core checks, some quality issues |
| **2 - Needs Work** | Fails 1-2 core checks, requires human revision |
| **1 - Poor** | Fails multiple core checks or has red flags |

---

**End of Implementation Plan**
