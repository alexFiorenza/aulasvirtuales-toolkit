<p align="center">
  <img src="apps/aulasvirtuales-cli/src/aulasvirtuales_cli/resources/logo.png" alt="Aulas Virtuales" width="200">
</p>

<h1 align="center">aulasvirtuales-toolkit</h1>

<p align="center">
  Toolkit to interact with <a href="https://aulasvirtuales.frba.utn.edu.ar">UTN FRBA's Moodle virtual classrooms</a>.<br>
  Includes a CLI, an MCP server, and AI agent skills. Browse courses, download resources, convert documents to markdown (native or OCR), read forum posts, check grades, and track upcoming events.
</p>

Authentication is handled automatically via SSO (Keycloak) using headless Playwright.

## Agent Skills

Install the skills for your AI agent (Claude Code, Cursor, Copilot, etc.):

```bash
npx skills add alexFiorenza/aulasvirtuales-toolkit
```

This installs two skills:

| Skill | Description |
|---|---|
| **`aulasvirtuales`** | Uses the MCP server tools. Preferred for general interactions — browsing courses, downloading with conversion/OCR, reading files, forums, grades, and events. |
| **`aulasvirtuales-cli`** | Runs CLI commands directly. Use for bulk downloads, authentication management, or CLI-specific features. |

## MCP Server

The MCP server exposes Moodle functionality as tools for AI agents. It can be used with any MCP-compatible client.

### Setup

Clone the repo and install dependencies:

```bash
git clone https://github.com/alexFiorenza/aulasvirtuales-toolkit.git
cd aulasvirtuales-toolkit
uv venv && source .venv/bin/activate
uv sync --all-extras
playwright install chromium
```

Then configure it in your MCP client (e.g. Claude Desktop, Cursor) as a stdio server:

```json
{
  "mcpServers": {
    "aulasvirtuales": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/aulasvirtuales-toolkit", "aulasvirtuales-mcp"],
      "env": {
        "MOODLE_USERNAME": "your_username",
        "MOODLE_PASSWORD": "your_password"
      }
    }
  }
}
```

> Credentials can also be provided via the OS keychain (set up with `aulasvirtuales login` from the CLI).

<!-- TODO: Once published to PyPI, users will be able to run `uvx aulasvirtuales-mcp` directly without cloning. -->

### Available MCP tools

| Tool | Description |
|---|---|
| `get_courses` | List enrolled courses |
| `get_course_resources` | List sections and resources of a course |
| `get_upcoming_events` | Show upcoming events and deadlines |
| `get_grades` | Show grades and feedback for a course |
| `get_forums` | List forums in a course |
| `get_forum_discussions` | List discussion threads in a forum |
| `get_discussion_posts` | Show messages in a discussion thread |
| `download` | Download a resource with optional format conversion and OCR |
| `read_downloaded_file` | Read a file from the local downloads directory |
| `clear_downloads` | Clear all downloaded files from the downloads directory |

## Installation

### macOS / Linux (Recommended)

Install the CLI globally using Homebrew. This automatically provisions the Python environment and isolated Playwright browsers without polluting your system.

```bash
brew tap alexFiorenza/aulasvirtuales-toolkit https://github.com/alexFiorenza/aulasvirtuales-toolkit
brew install aulasvirtuales
```

### From Source (Development)

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

## CLI Usage

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

# Convert to markdown (native)
aulasvirtuales download <course_id> <resource_id> --to md

# Convert to markdown (OCR via vision LLM)
aulasvirtuales download <course_id> <resource_id> --ocr

# Custom output directory
aulasvirtuales download <course_id> <resource_id> -o ~/notes

# Save to a specific file path
aulasvirtuales download <course_id> <resource_id> -o ~/notes/resumen.pdf
```

The `-o` flag accepts a directory (keeps original filename) or a full file path (renames the file). If omitted, files are saved to `~/aulasvirtuales` by default.

### Download all files from a course

```bash
aulasvirtuales download-all <course_id>
aulasvirtuales download-all <course_id> --to md
aulasvirtuales download-all <course_id> --ocr
```

### Upcoming events and assignments

```bash
# All courses
aulasvirtuales events

# Specific course
aulasvirtuales events <course_id>
```

### Grades

```bash
aulasvirtuales grades <course_id>
aulasvirtuales grades <course_id> --with-comments
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

### Clear downloads

```bash
aulasvirtuales clear-downloads
aulasvirtuales clear-downloads -y
```

### OCR Configuration

Configure OCR provider and model for vision LLM-based document conversion:

```bash
aulasvirtuales config --ocr-provider ollama --ocr-model llava
aulasvirtuales config --ocr-provider openrouter --ocr-model google/gemini-flash-1.5 --openrouter-api-key sk-...
```

## Project structure

```
packages/
└── core/                            # Core library (shared by CLI and MCP)
    └── src/aulasvirtuales/
        ├── auth.py                  # SSO login via Playwright + credential/session management
        ├── client.py                # Moodle HTTP/AJAX client
        ├── config.py                # Persistent configuration
        ├── converter.py             # File format conversion (PDF→md, DOCX→PDF, PPTX→PDF)
        ├── downloader.py            # File download from Moodle
        └── ocr.py                   # OCR via vision LLMs (LangChain)
apps/
├── aulasvirtuales-cli/              # CLI tool (Typer)
│   └── src/aulasvirtuales_cli/
│       ├── app.py                   # CLI commands
│       ├── repl.py                  # Interactive shell (prompt_toolkit)
│       └── resources/               # Logo and banner assets
└── aulasvirtuales-mcp/              # MCP server (FastMCP)
    └── src/aulasvirtuales_mcp/
        └── server.py                # MCP tool definitions
skills/
├── aulasvirtuales/                  # MCP skill for AI agents
│   └── SKILL.md
└── aulasvirtuales-cli/              # CLI skill for AI agents
    └── SKILL.md
```

## Dependencies

- **fastmcp** — MCP server framework
- **typer** + **rich** — CLI with formatted output
- **playwright** — Headless SSO authentication
- **httpx** — HTTP client
- **keyring** — Secure credential and session storage in OS keychain
- **prompt-toolkit** — Interactive REPL with autocomplete

### Optional extras

| Extra | Dependencies | Purpose |
|---|---|---|
| `markdown` | pymupdf4llm | Native PDF → markdown conversion |
| `docx` | docx2pdf | DOCX → PDF conversion |
| `ocr` | langchain-core, langchain-ollama, langchain-openrouter, pymupdf | OCR via vision LLMs |

### Optional: LibreOffice (for .pptx conversion)

Converting `.pptx` files to PDF requires [LibreOffice](https://www.libreoffice.org/) installed on your system:

```bash
# macOS
brew install --cask libreoffice

# Linux
sudo apt install libreoffice
```

LibreOffice is used in headless mode — no GUI is launched during conversion.
