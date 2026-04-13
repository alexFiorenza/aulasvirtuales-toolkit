# Product Requirements Document (PRD)

## 1. Overview

**aulasvirtuales-toolkit** is an open-source toolkit that provides programmatic access to [UTN FRBA's Moodle virtual classrooms](https://aulasvirtuales.frba.utn.edu.ar). It enables students and AI agents to browse courses, download and convert resources, read forum posts, check grades, and track assignments — all from the terminal or an MCP-compatible client.

## 2. Problem Statement

UTN FRBA students interact with the Moodle platform exclusively through a web browser. There is no public API and no way to integrate with productivity tools or AI agents. Common pain points include:

- **Manual file downloads**: Students must navigate multiple pages to download course materials, one file at a time.
- **No format conversion**: PDF lecture slides and DOCX documents cannot be easily converted to markdown for note-taking workflows.
- **No AI integration**: AI coding assistants (Claude, Cursor, Copilot) cannot access course content to help with assignments.
- **No bulk operations**: Downloading all resources from a course requires dozens of manual clicks.
- **No notification integration**: Upcoming deadlines and events require checking the Moodle calendar manually.

## 3. Target Users

### 3.1 Primary: UTN FRBA Students

Technical students comfortable with the terminal who want to:

- Download and organize course materials efficiently.
- Convert documents to markdown for note-taking (Obsidian, Notion, etc.).
- Check grades and upcoming deadlines quickly.
- Use OCR to extract text from scanned PDFs or slides.

### 3.2 Secondary: AI Agents

MCP-compatible AI agents (Claude Desktop, Cursor, Copilot) that need to:

- Access course content to assist with assignments.
- Browse forum discussions for context.
- Track deadlines and grades on behalf of the student.

## 4. Core Features

### 4.1 Authentication

| Feature | Description |
|---|---|
| SSO Login | Authenticate via UTN's Keycloak SSO using headless Playwright. |
| Credential Storage | Securely store credentials in the OS keychain (macOS Keychain, GNOME Keyring). |
| Session Management | Cache MoodleSession cookies, auto-refresh on expiration. |
| Status Check | Verify authentication status and session validity. |

### 4.2 Course Management

| Feature | Description |
|---|---|
| List Courses | Retrieve all enrolled courses with IDs and names. |
| List Resources | Browse course sections and resources (files, folders, forums, assignments). |
| Resource Filtering | Filter resources by type (file, folder, forum, assignment, etc.). |

### 4.3 File Operations

| Feature | Description |
|---|---|
| Download | Download individual files or entire folders. |
| Bulk Download | Download all files from a course in one command. |
| File Filter | Download only files matching a substring pattern. |
| Custom Output | Specify output directory or file path. |

### 4.4 Format Conversion

| Conversion | Method | Dependency |
|---|---|---|
| PDF → Markdown | Native parsing | pymupdf4llm |
| DOCX → PDF | Native conversion | docx2pdf |
| PPTX → PDF | Headless conversion | LibreOffice |
| Any → Markdown (OCR) | Vision LLM | LangChain + Ollama/OpenRouter |

### 4.5 OCR Pipeline

| Feature | Description |
|---|---|
| Multi-provider | Support for Ollama (local) and OpenRouter (cloud). |
| Multi-format | Process PDF, DOCX, PPTX, and image files. |
| Page-by-page | Process multi-page documents with progress tracking. |
| Background jobs | MCP server runs OCR in the background with status polling. |
| Configurable | Provider, model, and API keys configurable via CLI. |

### 4.6 Academic Features

| Feature | Description |
|---|---|
| Grades | View grades, ranges, percentages, and feedback. |
| Deep Comments | Fetch inline submission comments from assignments. |
| Forums | Browse forums, discussions, and individual posts. |
| Events | View upcoming events and deadlines across all courses. |

### 4.7 Interactive Shell

| Feature | Description |
|---|---|
| REPL | Interactive shell with command autocomplete and history. |
| Tab Completion | Two-level completer: commands → options/arguments. |
| Banner | ASCII art banner with version info. |

## 5. Distribution Channels

| Channel | Target | Method |
|---|---|---|
| Homebrew | macOS/Linux users | `brew install aulasvirtuales` |
| Source | Developers | `git clone` + `uv sync` |
| MCP Server | AI agents | stdio server via `uv run aulasvirtuales-mcp` |
| Agent Skills | AI coding assistants | `npx skills add alexFiorenza/aulasvirtuales-toolkit` |

## 6. Non-Functional Requirements

### 6.1 Security

- Credentials are **never** stored in plaintext config files.
- All credential storage uses the OS keychain via the `keyring` library.
- Session cookies are cached for performance but validated before use.
- No credentials are transmitted except to UTN's official SSO endpoint.

### 6.2 Compatibility

- **Python**: 3.11+
- **OS**: macOS, Linux (primary targets)
- **Browsers**: Chromium (via Playwright, for SSO only)

### 6.3 Performance

- Session cookies are cached to avoid re-authentication on every command.
- AJAX calls to Moodle are minimal — one call per operation where possible.
- OCR runs in background threads (MCP) to avoid blocking the server.
- File downloads use streaming to handle large files.

### 6.4 Reliability

- Graceful degradation when optional dependencies are missing (OCR, DOCX, LibreOffice).
- Clear error messages guiding users to install missing extras.
- Session auto-refresh when expired.

## 7. Roadmap

### Short-term

- [ ] PyPI publication (`uvx aulasvirtuales-mcp` without cloning).

### Medium-term

- [ ] Course content caching for offline access.
- [ ] Windows support.
