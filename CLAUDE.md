# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Toolkit for interacting with UTN FRBA's Moodle virtual classrooms ("Aulas Virtuales"). Provides a CLI, an MCP server for AI agents, and agent skill definitions. Features: course browsing, file download with format conversion and OCR, forum reading, grades, and events.

## Monorepo Structure

uv workspace monorepo with three packages:

- **`packages/core`** (`aulasvirtuales-core`) — Shared library: auth (Playwright SSO via Keycloak), Moodle HTTP client, config, downloader, converter, OCR pipeline (LangChain). All other packages depend on this.
- **`apps/aulasvirtuales-cli`** (`aulasvirtuales-cli`) — CLI built with Typer/Rich, includes interactive REPL (prompt-toolkit). Entry point: `aulasvirtuales_cli.app:app`.
- **`apps/aulasvirtuales-mcp`** (`aulasvirtuales-mcp`) — MCP server built with FastMCP. Entry point: `aulasvirtuales_mcp.server:main`.

## Setup

```bash
uv venv && source .venv/bin/activate
uv sync --all-extras
playwright install chromium
```

## Commands

### Run tests
```bash
pytest                          # all tests
pytest -m unit                  # unit tests only
pytest -m integration           # integration tests only
pytest tests/unit/core/test_client.py          # single file
pytest tests/unit/core/test_client.py::test_name  # single test
```

Tests use `pytest-asyncio` (auto mode), `pytest-mock`, and `respx` for HTTP mocking.

### Run CLI (dev)
```bash
uv run aulasvirtuales [command]
```

### Run MCP server (dev)
```bash
uv run aulasvirtuales-mcp
```

### Versioning and changelog
```bash
cz bump        # bump version using commitizen
```

## Conventions

- **Python 3.11+** required
- **Conventional Commits** format (enforced): `feat(scope):`, `fix(scope):`, `docs:`, etc.
- Type hints on all function signatures
- Branches from `develop`; PRs target `master`
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Integration tests mock external services (Moodle, keyring) — they don't hit real endpoints
- Shared test fixtures in `tests/conftest.py` (Moodle HTML/JSON samples, mock keyring, mock HTTP client)
- Optional extras are separate: `ocr`, `markdown` (PDF→MD via `pdf-inspector`), `docx` (DOCX→MD via `mammoth`). Install via `uv sync --all-extras` for full dev.
- `pdf-inspector` publishes wheels for CPython 3.12 only. Python 3.11 / 3.13 will fall back to building from sdist and need a Rust toolchain; the `markdown` extra is optional precisely for that reason.

## Architecture Notes

- **Authentication flow**: Playwright drives headless Chromium through Keycloak SSO → captures MoodleSession cookie → stores in OS keyring via `keyring`. Session reuse avoids repeated logins.
- **Moodle client** (`client.py`): Uses AJAX service endpoints (`/lib/ajax/service.php`) with sesskey extracted from dashboard HTML. Not the official Moodle Web Services API — it scrapes/parses the student-facing web interface (see ADR-004).
- **PDF classifier gate** (`ocr.py`): Before running the vision OCR pipeline, `pdf-inspector` classifies the input PDF. If it's `text_based` the gate aborts and suggests the native `convert` path — the user can override with `--force-ocr` (CLI) or `force_ocr=true` (MCP). `mixed` PDFs go through a hybrid path: `pdf-inspector` extracts text pages, the vision LLM processes only the pages it flags in `pages_needing_ocr`. `scanned` / `image_based` / `unknown` run the full vision pipeline.
- **OCR pipeline** (`ocr.py`): LangChain-based, supports Ollama and OpenRouter providers. PDF pages rendered to images via PyMuPDF, sent to vision LLM for markdown extraction. MCP server runs OCR as background jobs with status polling.
- **Native PDF→Markdown** (`converter.py`): `pdf-inspector` (Rust, traditional parsing) replaces `pymupdf4llm`. Same library also powers the gate classification, so adding OCR-gating cost zero extra dependencies. Complementary: on a `convert --to md` of a `scanned` PDF, the CLI warns that the output will be empty and points at `--ocr`.
- **Downloads directory**: defaults to `~/aulasvirtuales`, configurable. MCP `read_downloaded_file` reads from this directory.
