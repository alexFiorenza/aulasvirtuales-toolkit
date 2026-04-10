---
name: aulasvirtuales
description: Use when the user wants to interact with UTN FRBA Moodle virtual classrooms - listing courses, downloading resources, reading forums, checking events, or any university-related task. Also use when the user mentions courses, assignments, professors, exams, or study materials.
allowed-tools: Bash Read Grep
license: MIT
---

# aulasvirtuales CLI

A CLI tool to interact with UTN FRBA's Moodle platform. Installed as `aulasvirtuales` command.

**Always run commands directly** (e.g. `aulasvirtuales courses`), never with `uv run`.

## Authentication

- `aulasvirtuales login` — prompts for username/password, stores session in OS keychain
- `aulasvirtuales logout` — removes credentials from keychain
- `aulasvirtuales status` — shows if logged in and session active
- Session auto-renews using stored credentials if expired

## Commands

### `aulasvirtuales courses`

Lists enrolled courses. Output: ID, Name.

### `aulasvirtuales resources <course_id>`

Lists sections and resources in a course. Output: ID, Type, Name.

Resource types: File, Folder, Forum, Assignment, Quiz, Link, Text, Page. Only File and Folder are downloadable.

### `aulasvirtuales download <course_id> <resource_id> [OPTIONS]`

Downloads a resource (File or Folder).

```bash
aulasvirtuales download 3641 106231
aulasvirtuales download 3641 106231 --to pdf
aulasvirtuales download 3641 106231 --to md
aulasvirtuales download 3641 106231 -o ~/notes
aulasvirtuales download 3641 106231 -o ~/notes/resumen.pdf
```

Options:

- `--to FORMAT` — Convert after download. Supported: `.docx` -> `pdf`, `.pdf` -> `md`, `.docx` -> `md` (chains docx->pdf->md), `.pptx` -> `pdf`, `.pptx` -> `md` (chains pptx->pdf->md). `.pptx` conversions require LibreOffice installed. No conversion if already in target format.
- `-o, --output PATH` — Destination directory or file path (default: `~/aulasvirtuales` or configured dir). File extension = full file path; no extension = directory.
- `--ocr` — Use a vision LLM to extract text via OCR instead of the default converter. Supports `.pdf`, `.docx`, `.pptx`, and images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`). Requires `uv sync --extra ocr`. When `--ocr` is used, `--to` defaults to `md`. Valid OCR output formats: `md`, `txt`.
- `--ocr-provider PROVIDER` — Override the configured OCR provider for this command (`ollama` or `openrouter`).
- `--ocr-model MODEL` — Override the configured OCR model for this command.

```bash
# OCR examples
aulasvirtuales download 3641 106231 --ocr                          # OCR to markdown (default)
aulasvirtuales download 3641 106231 --ocr --to txt                  # OCR to plain text
aulasvirtuales download 3641 106231 --ocr --ocr-provider ollama --ocr-model llava  # one-off override
```

### `aulasvirtuales download-all <course_id> [OPTIONS]`

Downloads every File and Folder from a course. Same options as `download` (including `--ocr`, `--ocr-provider`, `--ocr-model`).

```bash
aulasvirtuales download-all 3641
aulasvirtuales download-all 3641 --to pdf -o ~/study/math
```

### `aulasvirtuales clear-downloads [OPTIONS]`

Clears all downloaded files from the configured default download directory.

Options:

- `--force, -y` — Skipt the explicit confirmation prompt.

```bash
aulasvirtuales clear-downloads
aulasvirtuales clear-downloads -y
```

### `aulasvirtuales events [course_id]`

Shows upcoming events and deadlines. Omit course_id for all courses.

```bash
aulasvirtuales events
aulasvirtuales events 29595
```

### `aulasvirtuales grades <course_id> [OPTIONS]`

Shows the grading table and feedback for a course (like assignments, quizzes, and course totals).

Options:

- `--with-comments` — Iterates through assignments to extract specific text grades (e.g., "Entrega Muy bien") and fetches internal dynamic submission comments left by professors. Slower runtime due to additional HTTP requests.

```bash
aulasvirtuales grades 3641
aulasvirtuales grades 3641 --with-comments
```

### `aulasvirtuales forums <course_id>`

Lists forums in a course. Output: ID, Name.

### `aulasvirtuales discussions <forum_id> [-n LIMIT]`

Lists discussion threads in a forum. Default limit: 10.

### `aulasvirtuales posts <discussion_id>`

Shows all messages in a discussion thread.

### `aulasvirtuales config [OPTIONS]`

View or update CLI configuration.

- `-d, --download-dir PATH` — Set default download directory.
- `--ocr-provider PROVIDER` — Set OCR provider (`ollama` or `openrouter`).
- `--ocr-model MODEL` — Set OCR model name.
- `--openrouter-api-key KEY` — Set OpenRouter API key (stored in provider config).
- `--ollama-base-url URL` — Set Ollama base URL (default: `http://localhost:11434`).

```bash
aulasvirtuales config --ocr-provider ollama --ocr-model llava
aulasvirtuales config --ocr-provider openrouter --ocr-model google/gemini-flash-1.5 --openrouter-api-key sk-...
aulasvirtuales config   # show current config
```

## Typical Workflows

### Download and convert a file

```bash
aulasvirtuales courses                          # find course ID
aulasvirtuales resources 3641                   # find resource ID
aulasvirtuales download 3641 106231 --to pdf -o ~/notes
```

### Check what's due soon

```bash
aulasvirtuales events
```

### Read announcements

```bash
aulasvirtuales forums 3641                      # find forum ID
aulasvirtuales discussions 23491 -n 5           # find discussion ID
aulasvirtuales posts 406838                     # read the thread
```

### Download with OCR

```bash
aulasvirtuales config --ocr-provider ollama --ocr-model llava   # configure once
aulasvirtuales download 3641 106231 --ocr                       # OCR to markdown
aulasvirtuales download-all 3641 --ocr --to txt                 # OCR all files to plain text
```

## Important Notes

- All IDs are integers from previous command outputs.
- Downloaded files default to `~/aulasvirtuales` or the directory set via `aulasvirtuales config -d`.
- If a `--to` conversion fails, the CLI shows which extra to install.
- OCR requires `uv sync --extra ocr`. For `.docx` OCR, also needs `--extra docx` or LibreOffice. For `.pptx` OCR, needs LibreOffice.
- OCR provider config is stored in `~/.config/aulasvirtuales/config.json` under `ocr.<provider>` as kwargs passed directly to the LangChain class (`ChatOllama`, `ChatOpenRouter`).
- Session tokens persist in the OS keychain. Auth is automatic.
