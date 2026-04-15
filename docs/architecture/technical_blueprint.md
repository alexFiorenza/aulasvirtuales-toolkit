# Technical Blueprint

## 1. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Core runtime |
| Package Manager | uv | Dependency management and workspaces |
| HTTP Client | httpx | Moodle AJAX API calls and file downloads |
| Browser Automation | Playwright (Chromium) | SSO authentication via Keycloak |
| Credential Storage | keyring | OS keychain integration |
| CLI Framework | Typer + Rich | Terminal interface with formatted output |
| Interactive Shell | prompt-toolkit | REPL with autocomplete and history |
| MCP Framework | FastMCP | Model Context Protocol server |
| PDF Processing | pymupdf4llm / PyMuPDF | PDF→Markdown + PDF→Image rendering |
| Document Conversion | docx2pdf, LibreOffice | DOCX→PDF, PPTX→PDF |
| OCR | LangChain (Ollama, OpenRouter) | Vision LLM-based text extraction |
| Configuration | JSON | Persistent user settings |

## 2. Monorepo Architecture

The project uses a **uv workspace monorepo** with shared core logic and separate application entrypoints:

```
aulasvirtuales-toolkit/           # Root workspace
├── packages/
│   └── core/                     # aulasvirtuales-core (shared library)
│       └── src/aulasvirtuales/
├── apps/
│   ├── aulasvirtuales-cli/       # aulasvirtuales-cli (CLI app)
│   │   └── src/aulasvirtuales_cli/
│   └── aulasvirtuales-mcp/       # aulasvirtuales-mcp (MCP server)
│       └── src/aulasvirtuales_mcp/
├── skills/                       # AI agent skill definitions
├── tests/                        # Test suite
└── docs/                         # Documentation
```

### Dependency Graph

```
aulasvirtuales-cli ──→ aulasvirtuales-core
aulasvirtuales-mcp ──→ aulasvirtuales-core
```

Both `apps/` depend on `packages/core` via uv workspace references. The core library has no knowledge of the CLI or MCP layers.

## 3. Authentication Flow

The Moodle instance at UTN FRBA uses **Keycloak SSO** with OAuth2. There is no public API token mechanism, so authentication must go through the browser-based SSO flow.

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌─────────┐
│  User creds │────→│ Playwright       │────→│ Keycloak SSO │────→│ Moodle  │
│ (or keyring)│     │ (headless Chrome) │     │ (login form) │     │ session │
└─────────────┘     └──────────────────┘     └──────────────┘     └────┬────┘
                                                                       │
                                                            MoodleSession cookie
                                                                       │
                                                                 ┌─────▼─────┐
                                                                 │  keyring   │
                                                                 │  (cached)  │
                                                                 └───────────┘
```

### Steps

1. **Credential retrieval**: Check environment variables (`MOODLE_USERNAME`, `MOODLE_PASSWORD`) → keyring → prompt user.
2. **Session check**: If a cached token exists, validate it with a lightweight GET to `/my/`.
3. **Login**: Launch headless Chromium via Playwright, navigate to the OAuth2 login page, fill credentials, submit.
4. **Cookie extraction**: Extract `MoodleSession` cookie from the browser context.
5. **Persistence**: Store the session cookie in the OS keychain. Store credentials separately.

### Session Lifecycle

- **Valid**: Cookie exists and GET `/my/` returns 200.
- **Expired**: Cookie exists but GET `/my/` redirects (302). Triggers automatic re-login.
- **Missing**: No cookie stored. Requires user login.

## 4. Data Flow

### Moodle Interaction Model

The toolkit communicates with Moodle through two mechanisms:

#### 4.1 AJAX Service API

Primary method for structured data. Calls `POST /lib/ajax/service.php?sesskey=...` with JSON payloads.

| Method | Data Retrieved |
|---|---|
| `core_course_get_enrolled_courses_by_timeline_classification` | Enrolled courses |
| `core_courseformat_get_state` | Course sections, modules, resources |
| `mod_forum_get_discussion_posts` | Forum post content |
| `core_calendar_get_action_events_by_course` | Events for a course |
| `core_calendar_get_action_events_by_timesort` | All upcoming events |

#### 4.2 HTML Scraping

Used when AJAX endpoints don't expose the needed data:

| Page | Data Extracted | Parsing Method |
|---|---|---|
| `/grade/report/user/index.php` | Grade table (items, grades, ranges, percentages, feedback) + assignment cmids from `gradeitemheader` links | Regex on HTML table; action-menu HTML stripped before text extraction |
| `/mod/forum/view.php` | Discussion links and titles | Regex on anchor tags |
| `/mod/assign/view.php` | Assignment grade + submission status ("Estado de la entrega") + comments | Regex + AJAX comment API |
| `/mod/resource/view.php` | File download URLs | Redirect following + regex |
| `/mod/folder/view.php` | Folder file URLs | Regex on pluginfile URLs |

### Request Flow

```
CLI/MCP Command
     │
     ▼
MoodleClient._ajax(method, args)
     │
     ├──→ POST /lib/ajax/service.php
     │         sesskey from _fetch_sesskey()
     │         MoodleSession cookie from auth
     │
     ▼
Parse JSON response → Dataclass instances
     │
     ▼
CLI: Rich table/formatted output
MCP: Return as tool result
```

## 5. Conversion Pipeline

### 5.1 Native Conversion

```
                    ┌──────────────┐
           .pdf ───→│ pymupdf4llm  │───→ .md
                    └──────────────┘

                    ┌──────────────┐     ┌──────────────┐
          .docx ───→│   docx2pdf   │───→│ pymupdf4llm  │───→ .md
                    └──────────────┘     └──────────────┘

                    ┌──────────────┐     ┌──────────────┐
          .pptx ───→│ LibreOffice  │───→│ pymupdf4llm  │───→ .md
                    │  (headless)  │     └──────────────┘
                    └──────────────┘
```

### 5.2 OCR Conversion

```
                    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
.pdf/.docx/.pptx ──→│  Convert to  │───→│   PyMuPDF    │───→│  Vision LLM  │───→ .md/.txt
                    │   PDF first  │     │ (page→image) │     │  (per page)  │
                    └──────────────┘     └──────────────┘     └──────────────┘

                    ┌──────────────┐
     .png/.jpg ────→│  Vision LLM  │───→ .md/.txt
                    │  (direct)    │
                    └──────────────┘
```

### OCR Provider Architecture

```
ocr.py
  │
  ├── _get_llm(provider, model, **kwargs)
  │       │
  │       ├── "ollama"     → langchain_ollama.ChatOllama
  │       └── "openrouter" → langchain_openrouter.ChatOpenRouter
  │
  └── _ocr_image(image_bytes, llm, mime_type, prompt)
          │
          └── LLM.invoke([HumanMessage with image]) → extracted text
```

## 6. Configuration Management

### Config File Location

```
~/.config/aulasvirtuales/config.json
```

### Schema

```json
{
  "download_dir": "/Users/username/aulasvirtuales",
  "ocr": {
    "provider": "openrouter",
    "model": "google/gemini-flash-1.5",
    "openrouter": {
      "api_key": "sk-..."
    },
    "ollama": {
      "base_url": "http://localhost:11434"
    }
  }
}
```

### Credential Storage (Keyring)

| Key | Service | Description |
|---|---|---|
| `username` | `aulasvirtuales-cli` | Moodle username |
| `password` | `aulasvirtuales-cli` | Moodle password |
| `token` | `aulasvirtuales-cli` | MoodleSession cookie |

## 7. Error Handling

### Current Patterns

| Module | Pattern | Notes |
|---|---|---|
| `auth.py` | Raises `AuthenticationError` | Clear, specific exception |
| `client.py` | Raises `MoodleClientError` on AJAX errors | Catches API-level errors |
| `client.py` | `except Exception: pass` in `get_assignment_details` | Silences comment fetch failures |
| `converter.py` | Raises `FileNotFoundError` for missing LibreOffice | Actionable error message |
| `downloader.py` | Uses `response.raise_for_status()` | Delegates to httpx |
| CLI (`app.py`) | Catches errors → `console.print(style="red")` + `typer.Exit(1)` | User-facing messages |
| MCP (`server.py`) | Raises `ValueError` / `RuntimeError` | Propagated to MCP client |

### Known Gaps

- No retry logic for transient network failures.
- No logging framework configured — errors are either printed (CLI) or silently caught.
- HTML parsing with regex is fragile and may break if Moodle updates its templates.
