# ADR 004: HTML Scraping vs Moodle Web Services API

## Status

Accepted

## Date

2024-12-01

## Context

Moodle provides two ways to access data programmatically:

1. **AJAX Service API** (`/lib/ajax/service.php`) — Internal API used by Moodle's own JavaScript frontend. Requires a valid session cookie and a `sesskey`. Provides structured JSON responses for many operations.
2. **Web Services API** (`/webservice/rest/server.php`) — Official external API that uses API tokens. Requires site-level configuration to enable specific functions for specific user roles.
3. **HTML scraping** — Parse data directly from rendered HTML pages.

### Data Access Availability

| Data | AJAX API | Web Services API | HTML Scraping |
|---|---|---|---|
| Courses | ✅ Available | ❌ Not enabled | N/A |
| Course contents | ✅ Available | ❌ Not enabled | N/A |
| Forum posts | ✅ Available | ❌ Not enabled | N/A |
| Calendar events | ✅ Available | ❌ Not enabled | N/A |
| **Grades** | ❌ No endpoint | ❌ Not enabled | ✅ Required |
| **Forum discussion list** | ❌ Incomplete | ❌ Not enabled | ✅ Required |
| **Assignment details** | ❌ No endpoint | ❌ Not enabled | ✅ Required |
| **File download URLs** | ❌ No endpoint | ❌ Not enabled | ✅ Required |

## Decision

We use a **hybrid approach**:

- **AJAX API** as the primary data source for courses, contents, forum posts, and events.
- **HTML scraping with regex** for grades, forum discussion listings, assignment details, and file download URL extraction.

HTML is parsed using Python's `re` module rather than an HTML parser like BeautifulSoup, to avoid adding a dependency for what are relatively simple extraction patterns.

## Consequences

### Positive

- **Works without admin access**: We don't need UTN to enable Web Services API functions or create API tokens.
- **Full data coverage**: By combining AJAX + scraping, we can access all the data students need.
- **Minimal dependencies**: Using `re` instead of BeautifulSoup keeps the dependency tree small.
- **AJAX is semi-stable**: The AJAX methods map to well-defined Moodle PHP functions and change less frequently than HTML templates.

### Negative

- **Fragile scraping**: HTML parsing with regex is inherently fragile. Moodle template updates could break grade parsing, discussion listing, or URL extraction without warning.
- **No semantic guarantees**: The AJAX API is internal and undocumented. Method signatures could change across Moodle versions.
- **Regex limitations**: Complex HTML structures can be incorrectly parsed by regex. For example, nested tables or dynamically-loaded content may be missed.
- **Localization dependency**: The grade parsing relies on Spanish locale text ("Ítem de calificación", "Calificación") and assignment status labels ("Estado de la entrega") which would break for other locales.

### Mitigations

- Integration tests with sample HTML fixtures can detect breakage early.
- The AJAX methods used (`core_course_*`, `mod_forum_*`, `core_calendar_*`) are part of Moodle's stable core and unlikely to be removed.
- If UTN enables the Web Services API in the future, we can migrate scraping functions to use it without changing the public interface.
