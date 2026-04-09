<p align="center">
  <img src="packages/aulasvirtuales-cli/src/aulasvirtuales_cli/resources/logo.png" alt="Aulas Virtuales" width="200">
</p>

<h1 align="center">aulasvirtuales-toolkit</h1>

<p align="center">
  Toolkit to interact with <a href="https://aulasvirtuales.frba.utn.edu.ar">UTN FRBA's Moodle virtual classrooms</a>.<br>
  Includes a CLI and an MCP server. Browse courses, download resources, convert PDFs to markdown, read forum posts, and check upcoming events.
</p>

Authentication is handled automatically via SSO (Keycloak) using headless Playwright.

## Agent Skill

Install the skill for your AI agent (Claude Code, Cursor, Copilot, etc.):

```bash
npx skills add alexFiorenza/aulasvirtuales-toolkit
```

This teaches your agent how to use the `aulasvirtuales` CLI to interact with Moodle on your behalf.

## Installation

```bash
git clone https://github.com/alexFiorenza/aulasvirtuales-toolkit.git
cd aulasvirtuales-toolkit

uv venv
source .venv/bin/activate
uv sync --all-extras
playwright install chromium
```

## Authentication

Log in with your SIU Guarani credentials. They are stored securely in your OS keychain (macOS Keychain, GNOME Keyring, etc.):

```bash
aulasvirtuales login
```

Check status or log out:

```bash
aulasvirtuales status
aulasvirtuales logout
```

## Usage

### Interactive mode

Run `aulasvirtuales` with no arguments to open an interactive shell with autocomplete and command history.

```bash
aulasvirtuales
```

### List courses

```bash
aulasvirtuales courses
```

### List resources in a course

```bash
aulasvirtuales resources <course_id>
```

### Download a resource

```bash
aulasvirtuales download <course_id> <resource_id>

# Convert PDFs to markdown
aulasvirtuales download <course_id> <resource_id> --md

# Custom output directory
aulasvirtuales download <course_id> <resource_id> -o ~/notes

# Save to a specific file path
aulasvirtuales download <course_id> <resource_id> -o ~/notes/resumen.pdf
```

The `-o` flag accepts a directory (keeps original filename) or a full file path (renames the file). If omitted, files are saved to `~/aulasvirtuales` by default.

### Download all files from a course

```bash
aulasvirtuales download-all <course_id>
aulasvirtuales download-all <course_id> --md
```

### Upcoming events and assignments

```bash
# All courses
aulasvirtuales events

# Specific course
aulasvirtuales events <course_id>
```

### Forums

```bash
# List forums in a course
aulasvirtuales forums <course_id>

# List discussions in a forum
aulasvirtuales discussions <forum_id>
aulasvirtuales discussions <forum_id> -n 20

# Read posts in a discussion
aulasvirtuales posts <discussion_id>
```

## Project structure

```
packages/
├── aulasvirtuales/              # Core library (shared by CLI and MCP)
│   └── src/aulasvirtuales/
│       ├── auth.py              # SSO login via Playwright + credential/session management
│       ├── client.py            # Moodle HTTP/AJAX client
│       ├── config.py            # Persistent configuration
│       ├── converter.py         # File format conversion (PDF→md, DOCX→PDF, PPTX→PDF)
│       ├── downloader.py        # File download from Moodle
│       └── ocr.py               # OCR via vision LLMs
├── aulasvirtuales-cli/          # CLI tool
│   └── src/aulasvirtuales_cli/
│       ├── app.py               # CLI commands (Typer)
│       ├── repl.py              # Interactive shell (prompt_toolkit)
│       └── resources/           # Logo and banner assets
└── aulasvirtuales-mcp/          # MCP server (coming soon)
    └── src/aulasvirtuales_mcp/
```

## Dependencies

- **typer** + **rich** — CLI with formatted output
- **playwright** — Headless SSO authentication
- **httpx** — HTTP client
- **keyring** — Secure credential and session storage in OS keychain
- **prompt-toolkit** — Interactive REPL with autocomplete

### Optional: LibreOffice (for .pptx conversion)

Converting `.pptx` files to PDF requires [LibreOffice](https://www.libreoffice.org/) installed on your system:

```bash
# macOS
brew install --cask libreoffice

# Linux
sudo apt install libreoffice
```

LibreOffice is used in headless mode — no GUI is launched during conversion.
