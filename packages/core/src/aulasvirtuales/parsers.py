"""Pure HTML parsing functions for Moodle page scraping.

Each function takes raw HTML and returns structured data.
No HTTP calls, no side effects — independently testable.
"""

import json
import re

from aulasvirtuales.models import Discussion, GradeItem


def strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    clean = re.sub(r"<[^>]+>", " ", text).strip()
    return re.sub(r"\s+", " ", clean).strip()


def clean_html_cell(raw: str) -> str:
    """Full cleaning pipeline for a grade table cell.

    Strips action-menu HTML, removes tags, replaces entities,
    and normalizes whitespace.
    """
    clean = re.sub(r'<div class="action-menu.*', "", raw, flags=re.DOTALL)
    clean = re.sub(r"<[^>]+>", " ", clean).strip()
    clean = clean.replace("&ndash;", "-").replace("&nbsp;", "")
    return re.sub(r"\s+", " ", clean).strip()


def parse_grade_table(html: str) -> list[tuple[GradeItem, int | None]]:
    """Parse the Moodle grade report HTML into (GradeItem, assign_cmid) pairs.

    assign_cmid is the course-module id when the item links to
    ``/mod/assign/view.php``; ``None`` otherwise.
    """
    tables = re.findall(
        r'<table[^>]*class="[^"]*user-grade[^"]*"[^>]*>(.*?)</table>',
        html,
        re.DOTALL,
    )
    if not tables:
        return []

    results: list[tuple[GradeItem, int | None]] = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tables[0], re.DOTALL)
    for row in rows:
        cols = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL)
        if not cols:
            continue

        assign_cmid: int | None = None
        href_match = re.search(r"/mod/assign/view\.php\?id=(\d+)", cols[0])
        if href_match:
            assign_cmid = int(href_match.group(1))

        clean_cols = [clean_html_cell(c) for c in cols]

        if not any(clean_cols):
            continue
        if clean_cols[0] == "Ítem de calificación" or len(clean_cols) < 6:
            continue

        name = clean_cols[0]
        grade = clean_cols[2] if len(clean_cols) > 2 else ""

        results.append((
            GradeItem(
                name=name,
                grade=grade,
                range=clean_cols[3] if len(clean_cols) > 3 else "",
                percentage=clean_cols[4] if len(clean_cols) > 4 else "",
                feedback=clean_cols[5] if len(clean_cols) > 5 else "",
            ),
            assign_cmid,
        ))
    return results


def parse_forum_discussions(html: str, limit: int = 10) -> list[Discussion]:
    """Extract discussion ids and titles from a forum page."""
    raw = re.findall(r'discuss\.php\?d=(\d+)"[^>]*>([^<]+)', html)
    seen: set[str] = set()
    discussions: list[Discussion] = []
    for did, title in raw:
        if did in seen:
            continue
        seen.add(did)
        discussions.append(Discussion(id=int(did), title=title.strip()))
        if len(discussions) >= limit:
            break
    return discussions


def parse_url_redirect(html: str) -> str | None:
    """Extract the external redirect URL from a Moodle url-module view page."""
    block = re.search(
        r'class="urlworkaround"[^>]*>(.*?)</div>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if block:
        href = re.search(r'href="([^"]+)"', block.group(1))
        if href:
            return href.group(1)
    meta = re.search(
        r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\']?\d+;\s*url=([^\'">\s]+)',
        html,
        re.IGNORECASE,
    )
    if meta:
        return meta.group(1)
    return None


def parse_page_content(html: str) -> str:
    """Extract readable text from a Moodle page-module view page."""
    block = re.search(
        r'<div[^>]+class="[^"]*generalbox[^"]*"[^>]*>(.*?)</div\s*>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not block:
        block = re.search(
            r'<div[^>]+role="main"[^>]*>(.*?)</div\s*>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
    raw = block.group(1) if block else html
    return strip_html(raw)


def parse_assignment_page(html: str) -> tuple[str, str, dict | None]:
    """Extract grade, submission status, and comment config from an assignment page.

    Returns:
        (grade_str, submission_status, comment_config_or_None)
    """
    grade_match = re.search(
        r"<th[^>]*>Calificación</th>(.*?)</td>", html, re.DOTALL | re.IGNORECASE
    )
    grade_str = ""
    if grade_match:
        grade_str = re.sub(r"<[^>]+>", "", grade_match.group(1)).strip()

    status_match = re.search(
        r"<th[^>]*>\s*Estado de la entrega\s*</th>\s*<td[^>]*>(.*?)</td>",
        html,
        re.DOTALL,
    )
    submission_status = ""
    if status_match:
        submission_status = re.sub(r"<[^>]+>", "", status_match.group(1)).strip()

    comment_config: dict | None = None
    config_match = re.search(r"M\.core_comment\.init\([^,]+,\s*({[^}]+})\);", html)
    if config_match:
        try:
            comment_config = json.loads(config_match.group(1))
        except (json.JSONDecodeError, KeyError):
            pass

    return grade_str, submission_status, comment_config
