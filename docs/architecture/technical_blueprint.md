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
| Interactive TUI | Textual | In-REPL configuration and folder-file selection screens |
| MCP Framework | FastMCP | Model Context Protocol server |
| PDF Parsing & Classification | pdf-inspector (Rust) | PDF→Markdown + detection of text/scanned/mixed PDFs (powers the OCR gate) |
| PDF→Image Rendering | PyMuPDF | Page rasterization for the vision OCR pipeline |
| Document Conversion | mammoth (DOCX→MD), LibreOffice (DOCX/PPTX→PDF) | Native document conversion |
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

### Error States

The login flow distinguishes between two failure modes so the CLI can surface actionable messages instead of a raw Playwright traceback:

| Exception | Trigger | CLI message |
|---|---|---|
| `InvalidCredentialsError` | Keycloak form returns an error element (e.g., `#input-error`) after submitting credentials. | `❌ Usuario o contraseña incorrectos.` |
| `AuthenticationError` | SSO page did not load, network timeout, redirect never completed, or no `MoodleSession` cookie was extracted. | `❌ Error de autenticación: …` |

Both are raised from `packages/core/src/aulasvirtuales/auth.py::login` and caught by `apps/aulasvirtuales-cli/src/aulasvirtuales_cli/commands/auth.py::login_cmd` and the auto-relogin path in `apps/aulasvirtuales-cli/src/aulasvirtuales_cli/app.py::get_client`. When auto-relogin hits `InvalidCredentialsError` (stored password no longer valid), the CLI prompts the user to run `aulasvirtuales login` again.

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
           .pdf ───→│ pdf-inspector│───→ .md
                    └──────────────┘

                    ┌──────────────┐
          .docx ───→│   mammoth    │───→ .md
                    └──────────────┘

                    ┌──────────────┐
          .docx ───→│ LibreOffice  │───→ .pdf
                    │  (headless)  │
                    └──────────────┘

                    ┌──────────────┐     ┌──────────────┐
          .pptx ───→│ LibreOffice  │───→│ pdf-inspector│───→ .md
                    │  (headless)  │     └──────────────┘
                    └──────────────┘

                    ┌──────────────┐
          .pptx ───→│ LibreOffice  │───→ .pdf
                    │  (headless)  │
                    └──────────────┘
```

### 5.1.1 Strategy Dispatcher

`packages/core/src/aulasvirtuales/converter.py` exposes a single `convert(input, to_format, ...)` entry point that delegates to a `(extension, target_format) → ConversionStrategy` table:

| Key | Strategy | Backing library |
|---|---|---|
| `(".pdf", "md")` | `PdfToMarkdown` | `pdf-inspector` (Rust; traditional PDF parsing, no LLM) |
| `(".docx", "md")` | `DocxToMarkdown` | `mammoth` (pure Python, no system deps) |
| `(".docx", "pdf")` | `DocxToPdf` | LibreOffice headless |
| `(".pptx", "md")` | `PptxToMarkdown` | LibreOffice → `pdf-inspector` (chained) |
| `(".pptx", "pdf")` | `PptxToPdf` | LibreOffice headless |

Same-format requests (e.g., a `.pdf` file asked to become `pdf`) short-circuit in the CLI wrapper (`convert_file`) before hitting the dispatcher.

When `PdfToMarkdown` receives a PDF that `pdf-inspector` classifies as `scanned` or `image_based`, the CLI wrapper emits a warning and points the user at `--ocr` — the native path would otherwise produce an empty document. This is the symmetric counterpart of the OCR gate (§5.2).

### 5.1.2 Batch Error Handling

`download_all` iterates over every downloadable resource in a course. When a single file's extension has no matching strategy (e.g., `.xlsx` with `--to pdf`) the conversion is skipped with an informational log and the batch continues with the next file. This prevents one unsupported file from aborting a multi-gigabyte download. Single-resource `download` still fails loudly on unsupported conversions so the user gets immediate feedback.

### 5.2 OCR Conversion

OCR requests are not executed blindly. The pipeline first asks `pdf-inspector` what kind of PDF it is and dispatches accordingly:

```
                                                 ┌── text_based ──→  refuse (suggest --to md, or --force-ocr to override)
                                                 │
.pdf/.docx/.pptx ──→ Convert to PDF ──→ classify ┼── mixed      ──→  hybrid: native text for clean pages,
                     (if not .pdf)      via      │                    vision LLM only for pages_needing_ocr
                                     pdf-inspector│
                                                 └── scanned /      → full vision pipeline (render every page,
                                                    image_based /     send to vision LLM)
                                                    unknown

                    ┌──────────────┐     ┌──────────────┐
  vision pipeline:  │   PyMuPDF    │───→│  Vision LLM  │───→ .md/.txt
                    │ (page→image) │     │  (per page)  │
                    └──────────────┘     └──────────────┘

                    ┌──────────────┐
     .png/.jpg ────→│  Vision LLM  │───→ .md/.txt
                    │  (direct)    │
                    └──────────────┘
```

### 5.2.1 Classifier Gate

The gate is the behavior that protects users (and tokens) from pointless OCR runs and from scanned PDFs silently yielding empty markdown.

| Input classification | Gate decision | Override |
|---|---|---|
| `text_based` | Refuse. The native path is orders of magnitude faster and produces equivalent markdown. | CLI `--force-ocr` / MCP `force_ocr=true` |
| `mixed` | Proceed with hybrid extraction. | — |
| `scanned` / `image_based` / `unknown` | Proceed with full vision pipeline. | — |

The reverse gate lives in §5.1: `--to md` on a `scanned` PDF warns and exits instead of writing an empty file.

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
| `auth.py` | Raises `AuthenticationError` or `InvalidCredentialsError` | Keycloak error element detection to distinguish wrong-credentials from SSO/network failure |
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

## 8. Interactive UX Layer

Interactive Textual screens are reserved for the REPL, where a human user is guaranteed to be present. The REPL loop sets an environment variable that commands can consult to decide whether to launch a TUI:

```python
# repl.py::start_repl
os.environ["AULASVIRTUALES_REPL"] = "1"
try:
    ...  # prompt loop
finally:
    os.environ.pop("AULASVIRTUALES_REPL", None)

# app.py
def is_repl_context() -> bool:
    return os.environ.get("AULASVIRTUALES_REPL") == "1"
```

### Screens

| Screen | Module | Launched by |
|---|---|---|
| Config form | `aulasvirtuales_cli/tui/config_screen.py` | `config` command with no flags in REPL, or `--ui` anywhere |
| Folder file selector | `aulasvirtuales_cli/tui/file_selector.py` | `download <folder>` with no `--file` filter in REPL, or `--select` anywhere |

### Override flags

| Flag | Effect |
|---|---|
| `config --ui` | Force the config screen outside the REPL. |
| `download --select` | Force the file selector outside the REPL. |
| `download --all` | Skip the file selector inside the REPL. |

See [ADR 007](../adr/007-textual-for-interactive-tui.md) and [ADR 008](../adr/008-repl-only-interactive-gui.md) for the full rationale.
