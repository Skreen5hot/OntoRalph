# Local Server UI Implementation Plan

**Based on**: [Spec_Local_PythonServer_HTML_UI.md](Spec_Local_PythonServer_HTML_UI.md) v2.1
**Created**: 2025-01-24
**Status**: Ready for Implementation

---

## Overview

This plan breaks down the implementation of the OntoRalph Web UI into actionable tasks with clear acceptance criteria. Each phase builds on the previous, with testing gates between phases.

---

## Phase 1: Core Server

**Goal**: Establish the FastAPI backend with basic endpoints and static file serving.

### 1.1 Project Structure Setup

**Tasks**:
- [ ] Create `ontoralph/web/` directory structure
- [ ] Create `ontoralph/web/__init__.py`
- [ ] Create `ontoralph/web/server.py` (main FastAPI app)
- [ ] Create `ontoralph/web/routes/` package
- [ ] Create `ontoralph/web/models.py` (Pydantic models)
- [ ] Create `ontoralph/web/static/` directory for frontend files
- [ ] Add web dependencies to `pyproject.toml`

**Acceptance Criteria**:
- [ ] `pip install -e ".[web]"` installs FastAPI, uvicorn, sse-starlette
- [ ] `python -c "from ontoralph.web import server"` imports without error
- [ ] Directory structure matches spec file layout

**Files to Create**:
```
ontoralph/web/
├── __init__.py
├── server.py
├── models.py
├── session_store.py
├── routes/
│   ├── __init__.py
│   ├── health.py
│   ├── session.py
│   ├── validate.py
│   └── run.py
└── static/
    └── .gitkeep
```

---

### 1.2 Pydantic Models

**Tasks**:
- [ ] Define `ValidateRequest` / `ValidateResponse` models
- [ ] Define `ValidateBatchRequest` / `ValidateBatchResponse` models
- [ ] Define `RunRequest` / `RunResponse` models
- [ ] Define `SessionRequest` / `SessionResponse` models
- [ ] Define `ErrorResponse` model with error codes
- [ ] Define `CheckResultResponse` model (maps to core CheckResult)

**Acceptance Criteria**:
- [ ] All models have proper type hints
- [ ] All models pass mypy strict checks
- [ ] Models serialize/deserialize correctly (unit tests)
- [ ] Error codes enum matches spec (`RATE_LIMIT`, `API_ERROR`, etc.)

**Test File**: `tests/test_web_models.py`

---

### 1.3 Health Endpoint

**Tasks**:
- [ ] Implement `GET /api/health` in `routes/health.py`
- [ ] Return version from `ontoralph.__version__`
- [ ] Register route in main app

**Acceptance Criteria**:
- [ ] `GET /api/health` returns `{"status": "ok", "version": "1.0.0"}`
- [ ] Response status code is 200
- [ ] Response content-type is `application/json`

**Test Cases**:
```python
def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "version" in response.json()
```

---

### 1.4 Session Token Management

**Tasks**:
- [ ] Implement `SessionStore` class in `session_store.py`
  - [ ] Generate cryptographically random tokens (32 bytes, base64url)
  - [ ] Store token → (provider, api_key, expires_at) mapping
  - [ ] Implement token validation with TTL check
  - [ ] Implement token refresh on use
  - [ ] Implement token cleanup (expired tokens)
- [ ] Implement `POST /api/session` in `routes/session.py`
- [ ] Add dependency injection for session validation

**Acceptance Criteria**:
- [ ] Tokens are 43+ characters (32 bytes base64url encoded)
- [ ] Tokens expire after 30 minutes of inactivity
- [ ] Token validation extends TTL by 30 minutes
- [ ] Expired tokens return 401 with `SESSION_EXPIRED` error code
- [ ] Invalid tokens return 401 with `INVALID_TOKEN` error code
- [ ] Session store is thread-safe

**Test Cases**:
```python
def test_create_session_returns_token():
    response = client.post("/api/session", json={
        "provider": "claude",
        "api_key": "sk-ant-test123"
    })
    assert response.status_code == 200
    assert "session_token" in response.json()
    assert response.json()["session_token"].startswith("ort_")

def test_session_token_expires():
    # Create token, advance time 31 minutes, validate fails
    ...

def test_session_token_refreshes_on_use():
    # Create token, advance time 20 minutes, use token, advance 20 more, still valid
    ...
```

---

### 1.5 Validate Endpoint

**Tasks**:
- [ ] Implement `POST /api/validate` in `routes/validate.py`
- [ ] Support single definition validation
- [ ] Support batch comparison (multiple definitions)
- [ ] Map ChecklistEvaluator results to response models
- [ ] Determine overall status (pass/fail/iterate)

**Acceptance Criteria**:
- [ ] Single definition request returns check results with pass/fail counts
- [ ] Batch request returns comparison array with each definition's results
- [ ] Response includes all check codes (C1-C4, I1-I3, Q1-Q3, R1-R4)
- [ ] `is_ice=true` runs ICE-specific checks
- [ ] `is_ice=false` skips ICE-specific checks
- [ ] Empty definition returns 400 error

**Test Cases**:
```python
def test_validate_single_passing_definition():
    response = client.post("/api/validate", json={
        "definition": "An ICE that is about the temporal instant at which an event occurs.",
        "term": "Event Time",
        "is_ice": True
    })
    assert response.status_code == 200
    assert response.json()["status"] == "pass"

def test_validate_single_failing_definition():
    response = client.post("/api/validate", json={
        "definition": "A thing.",
        "term": "Event Time",
        "is_ice": True
    })
    assert response.status_code == 200
    assert response.json()["status"] == "fail"
    assert response.json()["failed_count"] > 0

def test_validate_batch_comparison():
    response = client.post("/api/validate", json={
        "definitions": [
            {"label": "A", "definition": "...", "term": "X", "is_ice": True},
            {"label": "B", "definition": "...", "term": "X", "is_ice": True}
        ]
    })
    assert response.status_code == 200
    assert "comparisons" in response.json()
    assert len(response.json()["comparisons"]) == 2
```

---

### 1.6 Run Endpoint (Blocking)

**Tasks**:
- [ ] Implement `POST /api/run` in `routes/run.py`
- [ ] Create ClassInfo from request
- [ ] Create LLM provider from api_key + provider
- [ ] Run RalphLoop.run() synchronously
- [ ] Map LoopResult to response model
- [ ] Handle LLM errors gracefully with error codes

**Acceptance Criteria**:
- [ ] Request with valid API key runs Ralph Loop
- [ ] Response includes final_definition, status, iterations, duration
- [ ] Mock provider works without real API key
- [ ] Invalid provider returns 400 error
- [ ] Missing API key (for non-mock) returns 400 error
- [ ] LLM errors (rate limit, timeout) return structured error response

**Test Cases**:
```python
def test_run_with_mock_provider():
    response = client.post("/api/run", json={
        "iri": ":TestClass",
        "label": "Test Class",
        "parent_class": "owl:Thing",
        "is_ice": False,
        "provider": "mock",
        "api_key": "not-needed",
        "max_iterations": 3
    })
    assert response.status_code == 200
    assert "final_definition" in response.json()
    assert response.json()["total_iterations"] <= 3

def test_run_without_api_key_fails():
    response = client.post("/api/run", json={
        "iri": ":TestClass",
        "label": "Test Class",
        "parent_class": "owl:Thing",
        "is_ice": False,
        "provider": "claude",
        # Missing api_key
        "max_iterations": 3
    })
    assert response.status_code == 400
```

---

### 1.7 Static File Serving

**Tasks**:
- [ ] Configure FastAPI to serve static files from `/static`
- [ ] Serve `index.html` at root path `/`
- [ ] Configure proper MIME types

**Acceptance Criteria**:
- [ ] `GET /` returns index.html (when it exists)
- [ ] `GET /css/styles.css` returns CSS with correct MIME type
- [ ] `GET /js/app.js` returns JS with correct MIME type
- [ ] 404 for non-existent static files

---

### 1.8 Error Handling Middleware

**Tasks**:
- [ ] Create custom exception classes for API errors
- [ ] Implement exception handler middleware
- [ ] Map exceptions to structured error responses
- [ ] Add request logging middleware

**Acceptance Criteria**:
- [ ] All errors return JSON with `code`, `message`, `retryable` fields
- [ ] 4xx errors have appropriate HTTP status codes
- [ ] 5xx errors don't leak internal details
- [ ] Requests are logged with method, path, status, duration

---

### 1.9 CORS Configuration

**Tasks**:
- [ ] Configure CORS middleware for localhost only
- [ ] Set strict `Access-Control-Allow-Origin`

**Acceptance Criteria**:
- [ ] Requests from `http://localhost:8765` are allowed
- [ ] Requests from other origins are blocked
- [ ] Preflight OPTIONS requests work correctly

---

## Phase 1 Gate

**Before proceeding to Phase 2**:
- [ ] All Phase 1 tests pass
- [ ] `ruff check ontoralph/web/` passes
- [ ] `mypy ontoralph/web/` passes
- [ ] Manual test: start server, hit `/api/health`, get response
- [ ] Manual test: `/api/validate` works via curl

**Command to verify**:
```bash
pytest tests/test_web*.py -v
ruff check ontoralph/web/
mypy ontoralph/web/ --ignore-missing-imports
```

---

## Phase 2: Basic Frontend

**Goal**: Create the HTML/CSS/JS foundation with Settings and Validate views.

### 2.1 HTML Structure

**Tasks**:
- [ ] Create `static/index.html` with Alpine.js integration
- [ ] Create tab navigation (Validate, Run, Batch, History, Settings)
- [ ] Create base layout with header, main content, footer
- [ ] Add meta tags for viewport, charset

**Acceptance Criteria**:
- [ ] Page loads without JavaScript errors
- [ ] Alpine.js initializes correctly
- [ ] Tab switching works (shows/hides content)
- [ ] Responsive on mobile (viewport meta tag)

**File**: `ontoralph/web/static/index.html`

---

### 2.2 CSS Styling

**Tasks**:
- [ ] Create `static/css/styles.css`
- [ ] Define CSS custom properties for theming
- [ ] Implement dark mode with `prefers-color-scheme`
- [ ] Style form elements (inputs, buttons, checkboxes)
- [ ] Style results tables
- [ ] Style error/success messages

**Acceptance Criteria**:
- [ ] Light theme looks professional
- [ ] Dark theme activates based on system preference
- [ ] Manual theme toggle overrides system preference
- [ ] Form elements are visually consistent
- [ ] Tables are readable with proper spacing

**File**: `ontoralph/web/static/css/styles.css`

---

### 2.3 IndexedDB Storage Module

**Tasks**:
- [ ] Create `static/js/storage.js`
- [ ] Implement database initialization (settings, prompts, history stores)
- [ ] Implement `getSetting(key)` / `setSetting(key, value)`
- [ ] Implement `getApiKey(provider)` / `setApiKey(provider, key)`
- [ ] Implement `clearAllData()` for "Forget Keys"

**Acceptance Criteria**:
- [ ] Database initializes on first load
- [ ] Settings persist across page reloads
- [ ] API keys can be stored and retrieved
- [ ] `clearAllData()` removes all stored data
- [ ] Errors are handled gracefully (private browsing mode)

**Test Method**: Manual browser testing + console verification

---

### 2.4 API Client Module

**Tasks**:
- [ ] Create `static/js/api.js`
- [ ] Implement `api.health()`
- [ ] Implement `api.createSession(provider, apiKey)`
- [ ] Implement `api.validate(definition, term, isIce)`
- [ ] Implement `api.validateBatch(definitions)`
- [ ] Implement `api.run(params)` (blocking)
- [ ] Add error handling and response parsing

**Acceptance Criteria**:
- [ ] All API methods return Promises
- [ ] Errors are thrown with meaningful messages
- [ ] Response data is properly parsed
- [ ] Network errors are caught and reported

**File**: `ontoralph/web/static/js/api.js`

---

### 2.5 Settings View

**Tasks**:
- [ ] Create Settings tab content in HTML
- [ ] Add Anthropic API key input (masked)
- [ ] Add OpenAI API key input (masked)
- [ ] Add default provider dropdown
- [ ] Add max iterations input
- [ ] Add theme toggle (Light/Dark/System)
- [ ] Add "Save Settings" button
- [ ] Add "Forget All Keys" button with confirmation
- [ ] Load saved settings on page load
- [ ] Save settings to IndexedDB on save

**Acceptance Criteria**:
- [ ] API keys are masked in input fields
- [ ] "Show" toggle reveals API key temporarily
- [ ] Settings persist after save and reload
- [ ] Theme changes apply immediately
- [ ] "Forget All Keys" clears storage with confirmation dialog
- [ ] Validation: max_iterations must be 1-10

---

### 2.6 Validate View

**Tasks**:
- [ ] Create Validate tab content in HTML
- [ ] Add definition textarea
- [ ] Add term input
- [ ] Add "Is ICE" checkbox
- [ ] Add "Validate" button
- [ ] Display results table (code, name, status, evidence)
- [ ] Show pass/fail summary
- [ ] Color-code passed (green) and failed (red) checks

**Acceptance Criteria**:
- [ ] Form submits on button click
- [ ] Form submits on Ctrl+Enter
- [ ] Loading state shown during API call
- [ ] Results table displays all checks
- [ ] Pass/fail counts are accurate
- [ ] Error messages display for API failures

---

### 2.7 Single Run View (Blocking Only)

**Tasks**:
- [ ] Create Run tab content in HTML
- [ ] Add form fields: IRI, Label, Parent, Siblings, Is ICE
- [ ] Add optional current definition textarea
- [ ] Add "Run Ralph Loop" button
- [ ] Display results panel (status, iterations, duration)
- [ ] Display final definition
- [ ] Display checks table

**Acceptance Criteria**:
- [ ] All form fields work correctly
- [ ] Siblings input accepts comma-separated values
- [ ] "Run" button triggers API call
- [ ] Loading state shown during processing
- [ ] Results display correctly on completion
- [ ] Error handling for API failures

---

## Phase 2 Gate

**Before proceeding to Phase 3**:
- [ ] All views render correctly
- [ ] Settings save/load works
- [ ] Validate view works end-to-end
- [ ] Run view works with mock provider
- [ ] Dark mode toggle works
- [ ] No JavaScript console errors

**Manual Test Checklist**:
1. [ ] Start server: `python -m ontoralph.web.server`
2. [ ] Open `http://localhost:8765`
3. [ ] Settings: Enter API key, save, reload, verify persisted
4. [ ] Settings: Toggle dark mode, verify it applies
5. [ ] Validate: Enter definition, validate, see results
6. [ ] Run: Fill form, run with mock provider, see results

---

## Phase 3: Real-Time Progress (SSE)

**Goal**: Add streaming progress updates for the Ralph Loop.

### 3.1 SSE Endpoint

**Tasks**:
- [ ] Implement `GET /api/run/stream` in `routes/run.py`
- [ ] Parse query parameters for run configuration
- [ ] Validate session token from query param
- [ ] Create async generator for SSE events
- [ ] Hook into RalphLoop iteration events
- [ ] Yield events: `iteration_start`, `generate`, `critique`, `refine`, `verify`, `complete`, `error`

**Acceptance Criteria**:
- [ ] Valid token allows SSE connection
- [ ] Invalid/expired token returns error event immediately
- [ ] Events stream in real-time as loop progresses
- [ ] `complete` event contains full result
- [ ] Connection closes after `complete` or `error`
- [ ] Client disconnect is handled gracefully

**Test Cases**:
```python
async def test_run_stream_sends_events():
    async with httpx.AsyncClient() as client:
        # Create session first
        session = await client.post("/api/session", json={...})
        token = session.json()["session_token"]

        # Connect to SSE
        async with client.stream("GET", f"/api/run/stream?token={token}&...") as response:
            events = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    events.append(line)

            assert any("iteration_start" in e for e in events)
            assert any("complete" in e for e in events)
```

---

### 3.2 Frontend SSE Handling

**Tasks**:
- [ ] Add SSE client code to `api.js`
- [ ] Implement `api.runStream(params, onEvent)`
- [ ] Handle reconnection on network errors
- [ ] Handle session expiry (auto-refresh token)
- [ ] Implement abort/cancel functionality

**Acceptance Criteria**:
- [ ] SSE connection established successfully
- [ ] Events received and parsed correctly
- [ ] `onEvent` callback called for each event
- [ ] Cancel button aborts connection
- [ ] Network errors show retry option

---

### 3.3 Live Progress Display

**Tasks**:
- [ ] Add progress section to Run view HTML
- [ ] Show current iteration number / max
- [ ] Show current phase (Generating/Critiquing/Refining)
- [ ] Show current definition preview
- [ ] Add Cancel button
- [ ] Transition to results on completion

**Acceptance Criteria**:
- [ ] Progress section appears when run starts
- [ ] Iteration counter updates in real-time
- [ ] Phase indicator changes as loop progresses
- [ ] Current definition updates after each generate/refine
- [ ] Cancel button stops the process
- [ ] Results section appears on completion

---

### 3.4 Keyboard Shortcuts

**Tasks**:
- [ ] Add global keyboard listener
- [ ] Implement `Ctrl+Enter` to submit current form
- [ ] Implement `Esc` to cancel running operation
- [ ] Implement `Ctrl+1-5` for tab switching
- [ ] Show shortcut hints in UI

**Acceptance Criteria**:
- [ ] `Ctrl+Enter` triggers Run/Validate on respective views
- [ ] `Esc` cancels in-progress SSE stream
- [ ] `Ctrl+1` through `Ctrl+5` switch tabs
- [ ] Shortcuts don't interfere with text input
- [ ] Shortcut hints visible in UI (e.g., button labels)

---

### 3.5 Error Handling & Retry

**Tasks**:
- [ ] Parse error events from SSE stream
- [ ] Display error modal with message
- [ ] Show retry countdown for retryable errors
- [ ] Implement manual retry button
- [ ] Auto-refresh session on `SESSION_EXPIRED`

**Acceptance Criteria**:
- [ ] Error modal appears on error event
- [ ] Retryable errors show countdown timer
- [ ] "Retry Now" button restarts the process
- [ ] Session expiry triggers automatic re-auth and retry
- [ ] Non-retryable errors show "Cancel" only

---

## Phase 3 Gate

**Before proceeding to Phase 4**:
- [ ] SSE streaming works end-to-end
- [ ] Progress updates display correctly
- [ ] Cancel button works
- [ ] Keyboard shortcuts work
- [ ] Error retry works

**Manual Test Checklist**:
1. [ ] Run with mock provider, observe live progress
2. [ ] Press Esc during run, verify cancellation
3. [ ] Press Ctrl+Enter to start run
4. [ ] Simulate error (e.g., invalid token), verify retry UI

---

## Phase 4: Batch Processing

**Goal**: Add async batch processing with progress tracking.

### 4.1 Batch Job Manager

**Tasks**:
- [ ] Create `batch_manager.py`
- [ ] Implement `BatchJob` class with state tracking
- [ ] Implement `BatchJobManager` singleton
- [ ] Store jobs in memory with cleanup for old jobs
- [ ] Run jobs in background asyncio tasks
- [ ] Support job cancellation

**Acceptance Criteria**:
- [ ] Jobs can be created and started
- [ ] Job state updates as classes are processed
- [ ] Completed jobs are retained for 1 hour
- [ ] Cancelled jobs stop processing new classes
- [ ] Thread-safe job access

---

### 4.2 Batch Endpoints

**Tasks**:
- [ ] Implement `POST /api/batch` in `routes/batch.py`
- [ ] Implement `GET /api/batch/{job_id}`
- [ ] Implement `GET /api/batch/{job_id}/stream` (SSE)
- [ ] Implement `DELETE /api/batch/{job_id}`

**Acceptance Criteria**:
- [ ] POST returns job_id immediately
- [ ] GET returns current job status and results
- [ ] SSE streams class-level progress events
- [ ] DELETE cancels running job
- [ ] 404 for non-existent job_id

**Test Cases**:
```python
def test_batch_creates_job():
    response = client.post("/api/batch", json={
        "classes": [{"iri": ":A", "label": "A", ...}],
        "provider": "mock",
        "api_key": "x"
    })
    assert response.status_code == 200
    assert "job_id" in response.json()

def test_batch_status():
    # Create job, poll status until complete
    ...

def test_batch_cancel():
    # Create job, cancel, verify status is "cancelled"
    ...
```

---

### 4.3 Batch View UI

**Tasks**:
- [ ] Create Batch tab content in HTML
- [ ] Add YAML textarea for class definitions
- [ ] Add file upload for YAML
- [ ] Add "Start Batch" button
- [ ] Display progress bar (completed/total)
- [ ] Display live results table
- [ ] Add "Cancel Batch" button
- [ ] Add "Download Results" button (ZIP)

**Acceptance Criteria**:
- [ ] YAML can be pasted or uploaded
- [ ] Invalid YAML shows validation error
- [ ] Progress bar updates as classes complete
- [ ] Results table shows each class status
- [ ] Cancel stops processing
- [ ] Download generates ZIP with all outputs

---

### 4.4 ZIP Generation

**Tasks**:
- [ ] Implement server-side ZIP generation
- [ ] Include individual Turtle/MD/JSON files per class
- [ ] Include SUMMARY.md

**Acceptance Criteria**:
- [ ] ZIP contains one file per processed class
- [ ] Files are named by IRI (sanitized)
- [ ] SUMMARY.md contains batch statistics

---

## Phase 4 Gate

**Before proceeding to Phase 5**:
- [ ] Batch job creation works
- [ ] Job status polling works
- [ ] SSE progress streaming works
- [ ] Cancel works
- [ ] Download ZIP works

---

## Phase 5: History & Polish

**Goal**: Add history tracking, advanced features, and polish.

### 5.1 History Storage

**Tasks**:
- [ ] Extend `storage.js` with history functions
- [ ] `addHistoryEntry(entry)` - save run to history
- [ ] `getHistory()` - retrieve all entries
- [ ] `getHistoryEntry(id)` - retrieve single entry
- [ ] `clearHistory()` - delete all history
- [ ] Auto-save after each run/validate

**Acceptance Criteria**:
- [ ] Runs are automatically saved to history
- [ ] History persists across sessions
- [ ] History entries contain full input/output data
- [ ] Clear history removes all entries

---

### 5.2 History View UI

**Tasks**:
- [ ] Create History tab content in HTML
- [ ] Display table: timestamp, term, status, duration
- [ ] Click row to expand and see details
- [ ] "Re-run" button loads into Run view
- [ ] "Compare" button loads into Validate comparison
- [ ] "Clear History" button with confirmation
- [ ] Export history as JSON

**Acceptance Criteria**:
- [ ] History displays in reverse chronological order
- [ ] Row click expands to show full details
- [ ] Re-run pre-fills Run form correctly
- [ ] Compare works with Validate batch mode
- [ ] Clear history works with confirmation

---

### 5.3 Validate Comparison Mode

**Tasks**:
- [ ] Add "Add Comparison" button to Validate view
- [ ] Support multiple definition inputs
- [ ] Display side-by-side results
- [ ] Highlight differences between definitions

**Acceptance Criteria**:
- [ ] Can add 2-4 definitions to compare
- [ ] Each definition gets its own results column
- [ ] Overall winner (most passes) is highlighted
- [ ] Can remove definitions from comparison

---

### 5.4 Advanced Mode (Custom Prompts)

**Tasks**:
- [ ] Add "Advanced Mode" toggle to Settings
- [ ] Show prompt editors when enabled
- [ ] Load default prompts from library
- [ ] Save custom prompts to IndexedDB
- [ ] Pass custom prompts to API when running

**Acceptance Criteria**:
- [ ] Toggle shows/hides prompt editors
- [ ] Default prompts are pre-filled
- [ ] Custom prompts persist across sessions
- [ ] Custom prompts are used in Run requests
- [ ] "Reset to Defaults" restores original prompts

---

### 5.5 Export Functionality

**Tasks**:
- [ ] Add export buttons to Run results: Turtle, Markdown, JSON
- [ ] Implement download as file
- [ ] Add "Copy to Clipboard" button for definition

**Acceptance Criteria**:
- [ ] Turtle download generates valid .ttl file
- [ ] Markdown download generates readable .md file
- [ ] JSON download generates valid .json file
- [ ] Copy button copies definition text
- [ ] Success toast shown on copy

---

### 5.6 Accessibility & Polish

**Tasks**:
- [ ] Add ARIA labels to interactive elements
- [ ] Ensure proper focus management
- [ ] Add loading spinners/skeletons
- [ ] Add success/error toast notifications
- [ ] Test with keyboard-only navigation
- [ ] Test with screen reader

**Acceptance Criteria**:
- [ ] All buttons have accessible labels
- [ ] Focus moves logically through forms
- [ ] Loading states are visually clear
- [ ] Toasts appear and auto-dismiss
- [ ] Tab navigation works throughout

---

## Phase 5 Gate

**Before proceeding to Phase 6**:
- [ ] History view works
- [ ] Comparison mode works
- [ ] Advanced mode works
- [ ] Export functionality works
- [ ] Accessibility audit passes

---

## Phase 6: CLI Integration & Testing

**Goal**: Add CLI command and comprehensive testing.

### 6.1 CLI Serve Command

**Tasks**:
- [ ] Add `serve` command to `cli.py`
- [ ] Implement `--port` option (default: 8765)
- [ ] Implement `--host` option (default: 127.0.0.1)
- [ ] Implement `--open` / `--no-open` flags
- [ ] Show warning when `--host 0.0.0.0`
- [ ] Auto-open browser on start

**Acceptance Criteria**:
- [ ] `ontoralph serve` starts server on localhost:8765
- [ ] `ontoralph serve --port 9000` uses custom port
- [ ] `ontoralph serve --host 0.0.0.0` shows security warning
- [ ] Browser opens automatically (unless `--no-open`)
- [ ] Ctrl+C stops server gracefully

**Test Cases**:
```python
def test_serve_command_exists():
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
```

---

### 6.2 Integration Tests

**Tasks**:
- [ ] Create `tests/test_web_integration.py`
- [ ] Test full validate flow
- [ ] Test full run flow with mock provider
- [ ] Test session token lifecycle
- [ ] Test batch job lifecycle

**Acceptance Criteria**:
- [ ] All integration tests pass
- [ ] Tests use test client (no real server needed)
- [ ] Tests are isolated and repeatable

---

### 6.3 E2E Tests (Optional)

**Tasks**:
- [ ] Set up Playwright for E2E testing
- [ ] Test Settings → save → reload flow
- [ ] Test Validate end-to-end
- [ ] Test Run with mock provider end-to-end
- [ ] Test keyboard shortcuts

**Acceptance Criteria**:
- [ ] E2E tests pass in CI
- [ ] Tests run in headless browser
- [ ] Tests cover critical user flows

---

### 6.4 Documentation

**Tasks**:
- [ ] Add Web UI section to docs
- [ ] Document `ontoralph serve` command
- [ ] Document keyboard shortcuts
- [ ] Add screenshots of UI

**Acceptance Criteria**:
- [ ] Documentation is accurate
- [ ] Screenshots are current
- [ ] Quick start guide covers web UI

---

## Phase 6 Gate (Release Ready)

**Before release**:
- [ ] All tests pass (unit, integration, E2E)
- [ ] `ruff check` passes
- [ ] `mypy` passes
- [ ] Documentation complete
- [ ] Manual QA checklist passed
- [ ] Version bumped if needed

---

## Final QA Checklist

### Functional Testing
- [ ] Settings: Save/load API keys
- [ ] Settings: Theme toggle (light/dark/system)
- [ ] Validate: Single definition
- [ ] Validate: Batch comparison
- [ ] Run: With mock provider
- [ ] Run: With Claude (if API key available)
- [ ] Run: Progress streaming
- [ ] Run: Cancel mid-process
- [ ] Batch: Submit batch job
- [ ] Batch: Track progress
- [ ] Batch: Cancel batch
- [ ] Batch: Download results
- [ ] History: View past runs
- [ ] History: Re-run from history
- [ ] Export: Turtle, Markdown, JSON

### Error Handling
- [ ] Invalid API key shows error
- [ ] Network failure shows retry option
- [ ] Rate limit shows countdown
- [ ] Session expiry auto-refreshes

### Security
- [ ] API keys not visible in DevTools network tab (after initial send)
- [ ] Server binds to localhost only by default
- [ ] CORS blocks cross-origin requests

### Accessibility
- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] Screen reader announces key elements

### Performance
- [ ] Page loads in < 2 seconds
- [ ] SSE updates render smoothly
- [ ] No memory leaks on long sessions

---

## Appendix: Test Commands

```bash
# Run all web tests
pytest tests/test_web*.py -v

# Run with coverage
pytest tests/test_web*.py --cov=ontoralph/web --cov-report=term

# Lint
ruff check ontoralph/web/

# Type check
mypy ontoralph/web/ --ignore-missing-imports

# Start dev server
python -c "import uvicorn; uvicorn.run('ontoralph.web.server:app', reload=True)"

# E2E tests (if configured)
playwright test
```

---

*Implementation Plan Version: 1.0*
*Created: 2025-01-24*
