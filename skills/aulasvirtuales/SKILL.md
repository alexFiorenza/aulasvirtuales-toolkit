---
name: aulasvirtuales
description: Use when the user wants to interact with UTN FRBA Moodle virtual classrooms - listing courses, downloading resources, reading forums, checking events, or any university-related task. Also use when the user mentions courses, assignments, professors, exams, or study materials. This skill uses the AulasVirtuales MCP server tools.
allowed-tools: mcp__aulasvirtuales__* Bash Read Grep
license: MIT
---

# aulasvirtuales MCP

Interact with UTN FRBA's Moodle platform through the AulasVirtuales MCP server tools.

Authentication is handled automatically via stored credentials in the OS keychain (set up with `aulasvirtuales login` from the CLI) or via `MOODLE_USERNAME` / `MOODLE_PASSWORD` environment variables.

## Core Agent Behaviors

When interacting with this MCP server on behalf of the user, you MUST follow these conversational rules:

1. **Always Prompt OCR vs Native Extraction**: Whenever the user wants to download and convert a document to Markdown, explicitly ask them *before downloading* if they prefer to use "vision LLM OCR" (`ocr=true` with `ocr_provider`/`ocr_model` parameters) or standard fast local parsing (native `to="md"` via `pymupdf4llm`). Do NOT assume one or the other.
2. **Offer to Clean Up Downloads**: Once your main task is fully completed and all demanded output has been delivered to the user, politely ask if they would like you to clear temporary downloads from the download directory so their disk doesn't fill up. If they agree, call `clear_downloads(force=true)`.

## Available MCP Tools

### `get_courses`

Lists all enrolled courses. Returns course IDs and names. Always start here to get the `course_id` needed by other tools.

### `get_course_resources(course_id)`

Lists all sections and resources of a course. Returns section names with their resources (ID, type, name). Resource types include File, Folder, Forum, Assignment, Quiz, Link, Text, Page.

### `get_upcoming_events(course_id?)`

Shows upcoming events and deadlines. Pass a `course_id` to filter by course, or omit it to get events across all courses.

### `get_grades(course_id)`

Shows the grading table and feedback for a course, including assignments, quizzes, and course totals.

### `get_forums(course_id)`

Lists forums in a course. Returns forum IDs and names.

### `get_forum_discussions(forum_id, limit?)`

Lists discussion threads in a forum. Default limit is 10.

### `get_discussion_posts(discussion_id)`

Shows all messages in a forum discussion thread, including author, date, subject, and content.

### `read_downloaded_file(filename?)`

Reads a file from the local downloads directory (`~/aulasvirtuales` by default). If no filename is given, lists all available files. Text files are returned as text, PDFs as extracted text, and images as image content. Use this after `download` to read a converted file and pass its content to other tools or MCP servers (e.g. saving to Obsidian).

### `download(course_id, resource_id, output?, to?, file?, ocr?, ocr_provider?, ocr_model?)`

Full-featured download tool, equivalent to the CLI's `aulasvirtuales download` command. Supports format conversion and OCR.

**Parameters:**

- `course_id` (int) — The Moodle course ID.
- `resource_id` (int) — The resource ID (File or Folder).
- `output` (str, optional) — Destination directory or file path. Defaults to `~/aulasvirtuales`.
- `to` (str, optional) — Convert after download. Supported: `pdf`, `md`, `txt`. Conversion chains: `.docx`→`pdf`, `.docx`→`md`, `.pdf`→`md`, `.pptx`→`pdf`, `.pptx`→`md`.
- `file` (str, optional) — Filter: only download files whose name contains this substring (case-insensitive).
- `ocr` (bool, optional) — Use a vision LLM for OCR instead of native parsing. Defaults output to `md` if `to` is not set.
- `ocr_provider` (str, optional) — OCR provider override (`ollama`, `openrouter`). Falls back to CLI config.
- `ocr_model` (str, optional) — OCR model name override. Falls back to CLI config.

### `clear_downloads(force?)`

Clears all downloaded files from the configured download directory (`~/aulasvirtuales` by default). Use this to free disk space after completing download tasks.

**Parameters:**

- `force` (bool, optional) — If true, deletes immediately without confirmation. Default is false (returns a confirmation prompt message).

## Typical Workflows

### List courses and browse resources

1. Call `get_courses` to find the course ID
2. Call `get_course_resources(course_id)` to see available materials

### Download, convert, and read a document

1. Call `get_courses` to find the course ID
2. Call `get_course_resources(course_id)` to find the resource ID
3. **Ask the user** if they prefer OCR or native parsing for markdown conversion
4. Call `download(course_id, resource_id, to="md")` for native conversion
   — OR call `download(course_id, resource_id, ocr=true, ocr_provider="ollama", ocr_model="llava")` for OCR
5. Call `read_downloaded_file("filename.md")` to read the converted file
6. Deliver the content or pass it to another MCP (e.g. Obsidian)
7. **Ask the user** if they want to clean up downloads, and if yes call `clear_downloads(force=true)`

### Check deadlines

1. Call `get_upcoming_events()` for all courses, or `get_upcoming_events(course_id)` for a specific one

### Read forum posts

1. Call `get_forums(course_id)` to find the forum ID
2. Call `get_forum_discussions(forum_id)` to list threads
3. Call `get_discussion_posts(discussion_id)` to read a thread

### Check grades

1. Call `get_courses` to find the course ID
2. Call `get_grades(course_id)` to see grades and feedback

## Important Notes

- All IDs are integers returned by previous tool calls.
- Use `download` to save files to disk (with optional conversion/OCR). Use `read_downloaded_file` to read those files and get their content.
- `download` supports conversion (`to`), file filtering (`file`), OCR, and custom output paths.
- Only File, Folder, and Assignment resources can be read/downloaded. Other types (Quiz, Link, etc.) cannot.
- If authentication fails, tell the user to run `aulasvirtuales login` from the CLI to set up credentials, or set `MOODLE_USERNAME` and `MOODLE_PASSWORD` environment variables.
- OCR requires the `ocr` extra to be installed (`uv sync --extra ocr`) and a provider/model configured via `aulasvirtuales config` or passed directly as parameters.
