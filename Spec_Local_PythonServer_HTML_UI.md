# Specification: Local Python Server + HTML/JS UI

**Version**: 2.1 (Production Ready)
**Created**: 2025-01-24
**Updated**: 2025-01-24

---

## Overview

A local web-based user interface for OntoRalph that allows users to interactively refine ontology definitions through their browser. The system consists of a FastAPI backend server that wraps the existing OntoRalph library, and a vanilla HTML/JS frontend with Alpine.js for reactivity.

## Goals

1. **Ease of Use**: Provide a graphical interface for users unfamiliar with CLI
2. **Local-First**: All processing happens locally; API keys never leave the user's machine
3. **Real-Time Feedback**: Show iteration progress as the Ralph Loop runs
4. **Minimal Dependencies**: Use vanilla JS + Alpine.js (CDN, no build step)
5. **Seamless Integration**: Reuse existing OntoRalph library code
6. **Production Ready**: Handle edge cases, timeouts, and errors gracefully

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   HTML/JS Frontend                       ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  ││
│  │  │ Settings │  │  Single  │  │    Batch Processing   │  ││
│  │  │  (Keys)  │  │   Run    │  │                       │  ││
│  │  └──────────┘  └──────────┘  └──────────────────────┘  ││
│  │                      │                                   ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │              IndexedDB                               │││
│  │  │  - API Keys                                          │││
│  │  │  - Run History                                       │││
│  │  │  - Custom Prompt Templates                           │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (localhost:8765)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /api/health      - Health check                     │   │
│  │  /api/session     - Exchange API key for session     │   │
│  │  /api/validate    - Validate definitions (no LLM)    │   │
│  │  /api/run         - Run Ralph Loop (single class)    │   │
│  │  /api/run/stream  - Run with SSE progress updates    │   │
│  │  /api/batch       - Start async batch job            │   │
│  │  /api/batch/{id}  - Get batch job status             │   │
│  │  /api/batch/{id}/stream - SSE for batch progress     │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Middleware                               │   │
│  │  - CORS (strict localhost)                            │   │
│  │  - Session Token Validation                           │   │
│  │  - Request Logging                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                               │
│                              ▼                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              OntoRalph Library                        │   │
│  │  - ChecklistEvaluator                                 │   │
│  │  - RalphLoop                                          │   │
│  │  - LLM Providers (Claude, OpenAI)                     │   │
│  │  - Output Generators                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
                    ┌─────────────────┐
                    │  Anthropic API  │
                    │   OpenAI API    │
                    └─────────────────┘
```

---

## API Endpoints

### `GET /api/health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### `POST /api/session`

Exchange an API key for a short-lived session token. This solves the problem that browser `EventSource` does not support custom headers.

**Request:**
```json
{
  "provider": "claude",
  "api_key": "sk-ant-..."
}
```

**Response:**
```json
{
  "session_token": "ort_abc123...",
  "expires_at": "2025-01-24T12:30:00Z",
  "provider": "claude"
}
```

**Implementation Notes:**
- Token expires after 30 minutes of inactivity
- Token stored in server memory only (never persisted)
- Token tied to specific provider
- Used as query param `?token=ort_abc123` for SSE endpoints

---

### `POST /api/validate`

Validate one or more definitions against the checklist without LLM refinement.

**Request (single):**
```json
{
  "definition": "An event time is a temporal instant...",
  "term": "Event Time",
  "is_ice": true
}
```

**Request (batch comparison):**
```json
{
  "definitions": [
    {
      "label": "Original",
      "definition": "An event time is a temporal instant...",
      "term": "Event Time",
      "is_ice": true
    },
    {
      "label": "Candidate A",
      "definition": "An ICE that is about the temporal instant...",
      "term": "Event Time",
      "is_ice": true
    }
  ]
}
```

**Response (single):**
```json
{
  "status": "pass",
  "results": [
    {
      "code": "C1",
      "name": "Has Genus",
      "passed": true,
      "severity": "required",
      "evidence": "Found genus: 'temporal instant'"
    }
  ],
  "passed_count": 10,
  "failed_count": 2
}
```

**Response (batch comparison):**
```json
{
  "comparisons": [
    {
      "label": "Original",
      "status": "fail",
      "passed_count": 8,
      "failed_count": 4,
      "results": [...]
    },
    {
      "label": "Candidate A",
      "status": "pass",
      "passed_count": 12,
      "failed_count": 0,
      "results": [...]
    }
  ]
}
```

---

### `POST /api/run`

Run the Ralph Loop for a single class (blocking, returns final result).

**Request:**
```json
{
  "iri": ":EventTime",
  "label": "Event Time",
  "parent_class": "cco:InformationContentEntity",
  "sibling_classes": [":StartTime", ":EndTime"],
  "is_ice": true,
  "current_definition": null,
  "max_iterations": 5,
  "provider": "claude",
  "api_key": "sk-ant-...",
  "custom_prompts": null
}
```

**Response:**
```json
{
  "status": "pass",
  "converged": true,
  "final_definition": "An ICE that is about the temporal instant...",
  "total_iterations": 3,
  "duration_seconds": 12.5,
  "iterations": [
    {
      "iteration": 1,
      "definition": "...",
      "status": "iterate",
      "failed_checks": ["I2", "Q1"]
    }
  ],
  "final_checks": [...]
}
```

---

### `GET /api/run/stream`

Run the Ralph Loop with Server-Sent Events (SSE) for real-time progress.

**Query Parameters:**
- `iri`, `label`, `parent_class`, `is_ice`, `max_iterations` (same as POST body)
- `sibling_classes` - comma-separated string
- `token` - session token from `/api/session`

**Example:**
```
GET /api/run/stream?iri=:EventTime&label=Event%20Time&parent_class=cco:ICE&is_ice=true&token=ort_abc123
```

**SSE Events:**
```
event: iteration_start
data: {"iteration": 1, "max_iterations": 5}

event: generate
data: {"definition": "An ICE that..."}

event: critique
data: {"status": "iterate", "failed_checks": ["I2"], "failed_count": 1}

event: refine
data: {"definition": "An ICE that is about..."}

event: verify
data: {"status": "pass", "passed_count": 12, "failed_count": 0}

event: complete
data: {"result": {...}}

event: error
data: {"code": "RATE_LIMIT", "message": "API rate limit exceeded. Retry after 60s.", "retryable": true, "retry_after": 60}
```

**Error Codes:**
| Code | Description | Retryable |
|------|-------------|-----------|
| `RATE_LIMIT` | LLM API rate limit hit | Yes |
| `API_ERROR` | LLM API returned error | Maybe |
| `TIMEOUT` | LLM request timed out | Yes |
| `INVALID_RESPONSE` | Could not parse LLM response | Yes |
| `SESSION_EXPIRED` | Session token expired | No (re-auth) |
| `PROVIDER_UNAVAILABLE` | LLM service down | Yes |

---

### `POST /api/batch`

Start an asynchronous batch processing job. Returns immediately with a job ID.

**Request:**
```json
{
  "classes": [
    {
      "iri": ":EventTime",
      "label": "Event Time",
      "parent_class": "cco:ICE",
      "is_ice": true
    }
  ],
  "max_iterations": 5,
  "provider": "claude",
  "api_key": "sk-ant-..."
}
```

**Response:**
```json
{
  "job_id": "batch_abc123",
  "status": "pending",
  "total_classes": 5,
  "created_at": "2025-01-24T12:00:00Z"
}
```

---

### `GET /api/batch/{job_id}`

Get the current status of a batch job.

**Response (in progress):**
```json
{
  "job_id": "batch_abc123",
  "status": "running",
  "total_classes": 5,
  "completed": 2,
  "passed": 1,
  "failed": 1,
  "current_class": ":NounPhrase",
  "results": [
    {
      "iri": ":EventTime",
      "status": "pass",
      "final_definition": "..."
    },
    {
      "iri": ":VerbPhrase",
      "status": "fail",
      "final_definition": "...",
      "error": null
    }
  ]
}
```

**Response (complete):**
```json
{
  "job_id": "batch_abc123",
  "status": "complete",
  "total_classes": 5,
  "completed": 5,
  "passed": 4,
  "failed": 1,
  "duration_seconds": 75.3,
  "results": [...]
}
```

---

### `GET /api/batch/{job_id}/stream`

SSE stream for batch job progress.

**Query Parameters:**
- `token` - session token

**SSE Events:**
```
event: job_start
data: {"job_id": "batch_abc123", "total_classes": 5}

event: class_start
data: {"iri": ":EventTime", "index": 0}

event: class_iteration
data: {"iri": ":EventTime", "iteration": 2, "status": "iterate"}

event: class_complete
data: {"iri": ":EventTime", "status": "pass", "definition": "..."}

event: job_complete
data: {"passed": 4, "failed": 1, "duration_seconds": 75.3}

event: error
data: {"code": "RATE_LIMIT", "message": "...", "retryable": true}
```

---

### `DELETE /api/batch/{job_id}`

Cancel a running batch job.

**Response:**
```json
{
  "job_id": "batch_abc123",
  "status": "cancelled",
  "completed": 3,
  "cancelled_at": "2025-01-24T12:05:00Z"
}
```

---

## Frontend Structure

### Pages/Views

1. **Settings View**
   - API key input (Anthropic and/or OpenAI)
   - Provider selection (default)
   - Max iterations default
   - Theme toggle (light/dark/system)
   - **Advanced Mode toggle**:
     - Custom system prompt editor
     - Custom critique prompt editor
     - Custom refine prompt editor
   - Keys stored in IndexedDB

2. **Validate View**
   - Definition textarea
   - Term input
   - Is ICE checkbox
   - **"Add Comparison" button** - compare multiple definition variants
   - Results table showing all checks
   - Side-by-side comparison mode

3. **Single Run View**
   - Form inputs: IRI, Label, Parent, Siblings, Is ICE checkbox
   - Optional: Current definition textarea
   - "Run" button (Ctrl+Enter shortcut)
   - Live progress display:
     - Current iteration / max
     - Current definition preview
     - Status indicator (generating/critiquing/refining)
   - "Cancel" button (Esc shortcut)
   - Results panel (final definition, check results table)
   - Export buttons (Turtle, Markdown, JSON, Copy)

4. **Batch View**
   - YAML text input or file upload
   - "Start Batch" button
   - Progress bar with class-level detail
   - Live results table (updates as each class completes)
   - "Cancel Batch" button
   - Download all results button (ZIP with individual files)

5. **History View** (new)
   - Table of past runs (timestamp, term, status, duration)
   - Click to view full details
   - "Re-run" button to load settings into Single Run view
   - "Compare" button to load into Validate comparison mode
   - Export/clear history

### File Structure

```
ontoralph/
├── web/
│   ├── __init__.py
│   ├── server.py          # FastAPI application
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py      # Health endpoint
│   │   ├── session.py     # Session token management
│   │   ├── validate.py    # Validate endpoint
│   │   ├── run.py         # Single run endpoints
│   │   └── batch.py       # Batch endpoints
│   ├── models.py          # Pydantic request/response models
│   ├── session_store.py   # In-memory session token store
│   ├── batch_manager.py   # Async batch job management
│   └── static/
│       ├── index.html     # Main HTML (SPA-style with tabs)
│       ├── css/
│       │   └── styles.css # Styling with dark mode support
│       └── js/
│           ├── app.js     # Main Alpine.js application
│           ├── api.js     # API client (fetch + SSE handling)
│           ├── storage.js # IndexedDB wrapper
│           └── utils.js   # Helpers (debounce, formatters, etc.)
```

---

## Security Considerations

### API Key Handling

1. **Browser Storage**
   - Keys stored in IndexedDB (not localStorage for better security)
   - Keys never logged or displayed after entry (masked input)
   - "Forget Keys" button to clear from storage

2. **Transmission**
   - Keys sent only to localhost FastAPI server
   - For POST endpoints: sent in request body (HTTPS not needed for localhost)
   - For SSE endpoints: exchanged for session token first

3. **Server Handling**
   - Keys used immediately to create LLM provider
   - Never written to disk, logs, or persisted
   - Session tokens stored in memory with TTL

### Session Token Security

- Tokens are cryptographically random (32 bytes, base64url encoded)
- Expire after 30 minutes of inactivity
- Automatically extended on each use
- Stored in server memory only
- Invalidated on server restart

### Network Security

1. **Localhost Binding**
   - Server binds to `127.0.0.1` by default
   - Optional `--host 0.0.0.0` for LAN access (with warning)

2. **CORS Policy**
   - Strict `Access-Control-Allow-Origin: http://localhost:8765`
   - No wildcards

3. **Optional Password Protection**
   - Set `ONTORALPH_PASSWORD` environment variable
   - Required for all API endpoints if set
   - Useful for LAN/HomeLab deployments

---

## Data Flow: Single Run with SSE

```
1. User fills form, clicks "Run" (or Ctrl+Enter)
2. JS reads API key from IndexedDB
3. JS calls POST /api/session to get session token
4. JS opens EventSource to /api/run/stream?token=xxx&...
5. Server validates session token
6. Server creates ClassInfo and LLM provider
7. Server runs RalphLoop.run(class_info) with hooks
8. On each hook event, server yields SSE event
9. JS updates UI in real-time (iteration count, current def)
10. On "complete" event, JS displays final results
11. JS saves run to IndexedDB history
12. User can export to Turtle/Markdown/JSON
```

---

## IndexedDB Schema

### Store: `settings`
```javascript
{
  key: "anthropic_api_key",
  value: "sk-ant-...",
  updated_at: 1706097600000
}
{
  key: "openai_api_key",
  value: "sk-...",
  updated_at: 1706097600000
}
{
  key: "default_provider",
  value: "claude",
  updated_at: 1706097600000
}
{
  key: "max_iterations",
  value: 5,
  updated_at: 1706097600000
}
{
  key: "theme",
  value: "dark",  // "light" | "dark" | "system"
  updated_at: 1706097600000
}
```

### Store: `prompts` (Advanced Mode)
```javascript
{
  key: "system_prompt",
  value: "You are an ontology expert...",
  updated_at: 1706097600000
}
{
  key: "critique_prompt",
  value: "Evaluate the following definition...",
  updated_at: 1706097600000
}
```

### Store: `history`
```javascript
{
  id: "run_abc123",
  type: "single",  // "single" | "batch" | "validate"
  timestamp: 1706097600000,
  input: {
    iri: ":EventTime",
    label: "Event Time",
    parent_class: "cco:ICE",
    is_ice: true,
    initial_definition: null
  },
  output: {
    status: "pass",
    converged: true,
    final_definition: "An ICE that...",
    total_iterations: 3,
    duration_seconds: 12.5
  }
}
```

---

## Implementation Phases

### Phase 1: Core Server
- [ ] FastAPI application setup with proper project structure
- [ ] Pydantic models for all request/response types
- [ ] `/api/health` endpoint
- [ ] `/api/session` endpoint with token management
- [ ] `/api/validate` endpoint (single + batch comparison)
- [ ] `/api/run` endpoint (blocking)
- [ ] Static file serving from `/static`
- [ ] Error handling middleware with proper error codes
- [ ] Request logging

### Phase 2: Basic Frontend
- [ ] HTML structure with Alpine.js integration
- [ ] CSS styling with CSS custom properties for theming
- [ ] Dark mode support (`prefers-color-scheme` + toggle)
- [ ] IndexedDB storage module
- [ ] Settings view with API key management
- [ ] Validate view with single definition
- [ ] Single run view with form + blocking results

### Phase 3: Real-Time Progress (SSE)
- [ ] `/api/run/stream` SSE endpoint
- [ ] Frontend SSE handling with `fetch-event-source` pattern
- [ ] Live progress display (iteration count, current definition)
- [ ] Cancel button (abort EventSource + send cancel signal)
- [ ] Retry button for retryable errors
- [ ] Keyboard shortcuts (Ctrl+Enter, Esc)

### Phase 4: Batch Processing
- [ ] Async batch job manager (in-memory job store)
- [ ] `POST /api/batch` endpoint
- [ ] `GET /api/batch/{id}` status endpoint
- [ ] `GET /api/batch/{id}/stream` SSE endpoint
- [ ] `DELETE /api/batch/{id}` cancel endpoint
- [ ] Batch view UI with progress tracking
- [ ] Results download (ZIP generation)

### Phase 5: History & Polish
- [ ] History storage in IndexedDB
- [ ] History view UI
- [ ] Validate comparison mode (multiple definitions)
- [ ] Advanced mode (custom prompts)
- [ ] Export functionality (download Turtle/MD/JSON)
- [ ] Mobile-responsive layout
- [ ] Focus management and accessibility

### Phase 6: CLI Integration & Testing
- [ ] `ontoralph serve` CLI command
- [ ] `--port`, `--host`, `--open` options
- [ ] Integration tests for API endpoints
- [ ] E2E tests with Playwright (optional)

---

## Dependencies

### Backend (add to pyproject.toml)
```toml
[project.optional-dependencies]
web = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sse-starlette>=2.0.0",
    "python-multipart>=0.0.6",  # For file uploads
]
```

### Frontend (CDN, no build step)
```html
<!-- Alpine.js for reactivity -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

<!-- Optional: js-yaml for YAML parsing in batch view -->
<script src="https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/dist/js-yaml.min.js"></script>
```

---

## CLI Integration

```bash
# Start the web server
ontoralph serve

# Options:
#   --port PORT      Port to listen on (default: 8765)
#   --host HOST      Host to bind to (default: 127.0.0.1)
#   --open           Open browser automatically (default)
#   --no-open        Don't open browser

# Examples:
ontoralph serve                      # Start on localhost:8765, open browser
ontoralph serve --port 9000          # Use different port
ontoralph serve --host 0.0.0.0       # Allow LAN access (shows warning)
ontoralph serve --no-open            # Don't auto-open browser
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Enter` | Run / Validate (submit current form) |
| `Esc` | Cancel running operation |
| `Ctrl + S` | Save settings (in Settings view) |
| `Ctrl + 1-5` | Switch tabs (1=Validate, 2=Run, 3=Batch, 4=History, 5=Settings) |
| `Tab / Shift+Tab` | Navigate form fields |

---

## UI Mockup (ASCII)

```
┌─────────────────────────────────────────────────────────────────┐
│  OntoRalph v1.0.0                          [History] [Settings]│
├─────────────────────────────────────────────────────────────────┤
│  [Validate]  [Single Run]  [Batch]                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ IRI:        [:EventTime                               ]     ││
│  │ Label:      [Event Time                               ]     ││
│  │ Parent:     [cco:InformationContentEntity             ]     ││
│  │ Siblings:   [:StartTime, :EndTime                     ]     ││
│  │ [✓] Is ICE                                                  ││
│  │                                                              ││
│  │ Current Definition (optional):                              ││
│  │ ┌───────────────────────────────────────────────────────┐   ││
│  │ │                                                       │   ││
│  │ └───────────────────────────────────────────────────────┘   ││
│  │                                                              ││
│  │           [ Run Ralph Loop ]  (Ctrl+Enter)                  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ─────────────────── Progress ──────────────────                │
│  Iteration 2 of 5 • Refining...                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Current: An ICE that is about a temporal instant...        ││
│  └─────────────────────────────────────────────────────────────┘│
│                           [ Cancel ] (Esc)                      │
│                                                                  │
│  ─────────────────── Results ───────────────────                │
│                                                                  │
│  Status: ✓ PASS  │  Iterations: 3  │  Time: 12.5s              │
│                                                                  │
│  Final Definition:                                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ An ICE that is about the temporal instant at which an      ││
│  │ event begins or occurs.                                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Checks:                                                        │
│  ┌──────┬────────────────────────┬────────┬──────────────────┐ │
│  │ Code │ Check                  │ Status │ Evidence         │ │
│  ├──────┼────────────────────────┼────────┼──────────────────┤ │
│  │ C1   │ Has Genus              │ ✓ PASS │ "temporal..."    │ │
│  │ C2   │ Has Differentia        │ ✓ PASS │ "at which..."    │ │
│  │ I1   │ ICE Pattern            │ ✓ PASS │ "An ICE that..." │ │
│  └──────┴────────────────────────┴────────┴──────────────────┘ │
│                                                                  │
│  [ Turtle ] [ Markdown ] [ JSON ] [ Copy ]    [ Save to History]│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Error Handling Strategy

### Frontend Error Display

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠ Rate Limit Exceeded                                    [×]  │
│                                                                  │
│  The Claude API rate limit was exceeded.                        │
│  Retry available in 45 seconds.                                 │
│                                                                  │
│                              [ Retry Now ] [ Cancel ]           │
└─────────────────────────────────────────────────────────────────┘
```

### Error Recovery

1. **Retryable errors**: Show countdown timer, then auto-retry or manual retry button
2. **Session expired**: Automatically refresh session token and retry
3. **Network errors**: Show "Check connection" message with retry
4. **Fatal errors**: Show error details with "Report Issue" link

---

## Theme Support

### CSS Custom Properties

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --accent: #0066cc;
  --success: #22c55e;
  --error: #ef4444;
  --warning: #f59e0b;
  --border: #e5e5e5;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2a2a2a;
    --text-primary: #f5f5f5;
    --text-secondary: #a0a0a0;
    --accent: #3b82f6;
    --border: #404040;
  }
}

[data-theme="dark"] {
  --bg-primary: #1a1a1a;
  /* ... dark theme overrides ... */
}
```

---

## Summary of Changes from v1.0

| Area | v1.0 | v2.1 |
|------|------|------|
| **SSE Auth** | Custom header (broken) | Session token exchange |
| **Batch Mode** | Blocking POST | Async job + polling/SSE |
| **Validate** | Single definition | Multi-definition comparison |
| **Storage** | API keys only | Keys + History + Prompts |
| **Error Handling** | Basic | Structured codes + retry |
| **Theme** | None | Dark mode + system preference |
| **Keyboard** | None | Full shortcut support |
| **History** | None | Full run history |
| **Advanced Mode** | None | Custom prompt editing |

---

*Spec Version: 2.1 (Production Ready)*
*Created: 2025-01-24*
*Updated: 2025-01-24*
