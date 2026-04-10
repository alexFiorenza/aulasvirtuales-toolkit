---
name: aulasvirtuales
description: Use when the user wants to interact with UTN FRBA Moodle virtual classrooms - listing courses, downloading resources, reading forums, checking events, or any university-related task. Also use when the user mentions courses, assignments, professors, exams, or study materials. This skill uses the AulasVirtuales MCP server tools.
allowed-tools: mcp__aulasvirtuales__* Bash Read Grep
license: MIT
---

# aulasvirtuales MCP

Interact with UTN FRBA's Moodle platform through the AulasVirtuales MCP server tools.

Authentication is handled automatically via stored credentials in the OS keychain (set up with `aulasvirtuales login` from the CLI) or via `MOODLE_USERNAME` / `MOODLE_PASSWORD` environment variables.

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

### `download_resource_to_disk(course_id, resource_id)`

Downloads a resource (File or Folder) to the local disk at the configured download directory (`~/aulasvirtuales` by default). Use this when the user wants to keep the file on disk.

### `read_resource_content(course_id, resource_id)`

Downloads a resource temporarily and extracts its text/markdown content, then returns it directly. The file is not persisted on disk. Use this when you need to read the content of a document (PDF, DOCX, PPTX, TXT, etc.) to answer questions or summarize it for the user.

## Typical Workflows

### List courses and browse resources

1. Call `get_courses` to find the course ID
2. Call `get_course_resources(course_id)` to see available materials
3. Call `read_resource_content(course_id, resource_id)` to read a specific document

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
- Use `read_resource_content` when you need to read/summarize a document for the user. Use `download_resource_to_disk` when the user wants the file saved locally.
- Only File, Folder, and Assignment resources can be read/downloaded. Other types (Quiz, Link, etc.) cannot.
- If authentication fails, tell the user to run `aulasvirtuales login` from the CLI to set up credentials, or set `MOODLE_USERNAME` and `MOODLE_PASSWORD` environment variables.
- For advanced features like file conversion with `--to`, OCR, or bulk downloads, use the `/aulasvirtuales-cli` skill instead.
