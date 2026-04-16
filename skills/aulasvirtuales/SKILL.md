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

1. **Default to Native Conversion; Offer OCR Only When It Fits**: When the user asks to download and convert a document to Markdown, default to native parsing (`to="md"`, powered by `pdf-inspector` for PDFs and `mammoth` for DOCX). Only suggest OCR (`ocr=true`) if the user explicitly mentions it, if the file is an image, or if there's reason to believe the PDF is scanned (e.g., the user says "escaneado", the preview shows no selectable text, or native conversion returned suspiciously little content). The MCP server runs a smart classifier gate: if you call `ocr=true` on a text-based PDF it will refuse and ask you to use native conversion instead — do not pass `force_ocr=true` just to silence that error; only use `force_ocr=true` when the user has explicitly asked to run OCR anyway.
2. **Offer to Clean Up Downloads**: Once your main task is fully completed and all demanded output has been delivered to the user, politely ask if they would like you to clear temporary downloads from the download directory so their disk doesn't fill up. If they agree, call `clear_downloads(force=true)`.
3. **Do NOT Rapid-Poll OCR Status**: OCR jobs process each page through a vision LLM and take a long time. After starting an OCR job, wait **at least 30 seconds** before the first status check, and **at least 20 seconds** between subsequent checks. Always tell the user the current progress when you check (e.g. "processing page 3/10") instead of silently polling. Do not call `ocr_status` more than once per message turn.

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

### `download(course_id, resource_id, output?, to?, file?, ocr?, force_ocr?, ocr_provider?, ocr_model?)`

Full-featured download tool, equivalent to the CLI's `aulasvirtuales download` command. Supports format conversion and OCR.

When `ocr=true`, the download completes immediately and the OCR conversion runs **in the background**. The tool returns a `job_id` that you must poll with `ocr_status` until it completes.

**Classifier gate (PDFs only)**: when `ocr=true` targets a PDF, the server first classifies it. If it's `text_based`, the job is rejected with a message asking you to retry without OCR or with `force_ocr=true`. If it's `mixed`, the job runs a hybrid pipeline (native extraction for text pages, vision LLM only for scanned pages) — this is automatic and you don't need any extra flag. Native `to="md"` on a scanned PDF warns and suggests switching to `ocr=true`.

**Parameters:**

- `course_id` (int) — The Moodle course ID.
- `resource_id` (int) — The resource ID (File or Folder).
- `output` (str, optional) — Destination directory or file path. Defaults to `~/aulasvirtuales`.
- `to` (str, optional) — Convert after download. Supported: `pdf`, `md`, `txt`. Conversion chains: `.docx`→`pdf`, `.docx`→`md`, `.pdf`→`md`, `.pptx`→`pdf`, `.pptx`→`md`.
- `file` (str, optional) — Filter: only download files whose name contains this substring (case-insensitive).
- `ocr` (bool, optional) — Use a vision LLM for OCR instead of native parsing. Defaults output to `md` if `to` is not set.
- `force_ocr` (bool, optional) — Skip the classifier gate and force vision OCR even on text-based PDFs. Only pass `true` when the user has explicitly asked for OCR despite the warning.
- `ocr_provider` (str, optional) — OCR provider override (`ollama`, `openrouter`). Falls back to CLI config.
- `ocr_model` (str, optional) — OCR model name override. Falls back to CLI config.

### `ocr_status(job_id?)`

Checks the status of a background OCR job. Call without arguments to list all jobs, or pass a specific `job_id` returned by `download`.

**Returns one of:**

- `pending` — Job is queued but hasn't started yet.
- `processing page X/Y` — OCR is in progress, shows current page.
- `✓ completed → /path/to/file.md` — Done. The output file is ready to read with `read_downloaded_file`.
- `✗ failed — error message` — Something went wrong.

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
3. **Default to native conversion.** Only offer OCR if the user explicitly asks or if the file is an image / obvious scan.
4. **Native conversion:** Call `download(course_id, resource_id, to="md")` — synchronous, result is immediate. If this fails or the server warns that the PDF is scanned, retry with `ocr=true`.
5. **OCR conversion (only when justified):**
   a. Call `download(course_id, resource_id, ocr=true)` — returns immediately with a `job_id`
   b. **If the server rejects with "PDF is text-based"**: the PDF does not need OCR. Retry with native `to="md"` instead. Only pass `force_ocr=true` if the user has explicitly insisted on OCR despite the warning.
   c. **Wait before polling**: OCR processes each page through a vision LLM, which takes significant time. Do NOT poll immediately or in rapid succession. Wait **at least 30 seconds** before the first `ocr_status` check, and **at least 20 seconds** between subsequent checks. Inform the user that OCR is running and you'll check back shortly — do not silently poll in a loop.
   d. Call `ocr_status(job_id)` — if still `processing`, tell the user the current progress (e.g. "page 3/10") and wait another 20–30 seconds before checking again.
   e. Once the status is `completed` or `failed`, proceed accordingly.
6. Call `read_downloaded_file("filename.md")` to read the converted file
7. Deliver the content or pass it to another MCP (e.g. Obsidian)
8. **Ask the user** if they want to clean up downloads, and if yes call `clear_downloads(force=true)`

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
