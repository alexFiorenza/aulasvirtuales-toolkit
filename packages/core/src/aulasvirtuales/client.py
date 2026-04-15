import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

BASE_URL = "https://aulasvirtuales.frba.utn.edu.ar"

MODULE_TYPE_LABELS = {
    "resource": "File",
    "folder": "Folder",
    "forum": "Forum",
    "assign": "Assignment",
    "quiz": "Quiz",
    "url": "Link",
    "label": "Text",
    "page": "Page",
}


@dataclass
class GradeItem:
    name: str
    grade: str
    range: str
    percentage: str
    feedback: str
    status: str = ""


@dataclass
class SubmissionComment:
    author: str
    date: str
    content: str


@dataclass
class AssignmentDetails:
    grade: str
    comments: list[SubmissionComment]
    submission_status: str = ""


class MoodleClient:
    def __init__(self, session_cookie: str) -> None:
        self._http = httpx.Client(
            base_url=BASE_URL,
            cookies={"MoodleSession": session_cookie},
        )
        self._sesskey = self._fetch_sesskey()

    def _fetch_sesskey(self) -> str:
        response = self._http.get("/my/", follow_redirects=True)
        match = re.search(r'"sesskey":"(\w+)"', response.text)
        if not match:
            raise MoodleClientError("Could not extract sesskey from dashboard")
        return match.group(1)

    def _ajax(self, method: str, args: dict) -> dict:
        response = self._http.post(
            f"/lib/ajax/service.php?sesskey={self._sesskey}",
            json=[{"index": 0, "methodname": method, "args": args}],
        )
        data = response.json()
        if data[0].get("error"):
            raise MoodleClientError(data[0]["exception"]["message"])
        return data[0]["data"]

    def get_courses(self) -> list["Course"]:
        data = self._ajax(
            "core_course_get_enrolled_courses_by_timeline_classification",
            {"offset": 0, "limit": 0, "classification": "all", "sort": "fullname"},
        )
        return [
            Course(id=c["id"], fullname=c["fullname"], url=c["viewurl"])
            for c in data["courses"]
        ]

    def get_course_contents(self, course_id: int) -> list["Section"]:
        raw = self._ajax("core_courseformat_get_state", {"courseid": course_id})
        state = json.loads(raw) if isinstance(raw, str) else raw

        modules_by_section: dict[str, list[Resource]] = {}
        for cm in state.get("cm", []):
            if not cm.get("uservisible"):
                continue
            resource = Resource(
                id=int(cm["id"]),
                name=cm["name"],
                module=cm["module"],
                url=cm.get("url"),
            )
            modules_by_section.setdefault(cm["sectionid"], []).append(resource)

        sections = []
        for s in state.get("section", []):
            if not s.get("visible"):
                continue
            sections.append(
                Section(
                    id=int(s["id"]),
                    number=s["number"],
                    name=s["title"],
                    resources=modules_by_section.get(s["id"], []),
                )
            )
        return sections

    def get_forums(self, course_id: int) -> list["Resource"]:
        sections = self.get_course_contents(course_id)
        return [
            r for s in sections for r in s.resources if r.module == "forum"
        ]

    def get_forum_discussions(self, forum_cmid: int, limit: int = 10) -> list["Discussion"]:
        response = self._http.get(
            f"/mod/forum/view.php?id={forum_cmid}", follow_redirects=True,
        )
        raw = re.findall(r'discuss\.php\?d=(\d+)"[^>]*>([^<]+)', response.text)
        seen = set()
        discussions = []
        for did, title in raw:
            if did in seen:
                continue
            seen.add(did)
            discussions.append(Discussion(id=int(did), title=title.strip()))
            if len(discussions) >= limit:
                break
        return discussions

    def get_discussion_posts(self, discussion_id: int) -> list["ForumPost"]:
        data = self._ajax(
            "mod_forum_get_discussion_posts",
            {"discussionid": discussion_id},
        )
        return [
            ForumPost(
                id=p["id"],
                subject=p.get("subject", ""),
                author=p.get("author", {}).get("fullname", ""),
                message=p.get("message", ""),
                timestamp=p.get("timecreated", 0),
            )
            for p in data.get("posts", [])
        ]

    def get_upcoming_events(self, course_id: int | None = None, limit: int = 20) -> list["Event"]:
        if course_id:
            data = self._ajax(
                "core_calendar_get_action_events_by_course",
                {"courseid": course_id, "limitnum": limit},
            )
        else:
            data = self._ajax(
                "core_calendar_get_action_events_by_timesort",
                {"limitnum": limit, "timesortfrom": int(time.time())},
            )
        return [
            Event(
                id=e["id"],
                name=e["name"],
                course_name=e.get("course", {}).get("fullname", "") if isinstance(e.get("course"), dict) else "",
                module=e.get("modulename", ""),
                timestamp=e.get("timesort", e.get("timestart", 0)),
                url=e.get("url", ""),
                action=e.get("action", {}).get("name", "") if e.get("action") else "",
            )
            for e in data.get("events", [])
        ]

    def _parse_grade_table(self, html: str) -> list[tuple["GradeItem", int | None]]:
        """Parse the grade report HTML and return (GradeItem, assign_cmid) pairs.

        assign_cmid is the course-module id when the item links to
        ``/mod/assign/view.php``; ``None`` otherwise.
        """
        tables = re.findall(
            r'<table[^>]*class="[^"]*user-grade[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL
        )
        if not tables:
            return []

        results: list[tuple[GradeItem, int | None]] = []
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[0], re.DOTALL)
        for row in rows:
            cols = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            if not cols:
                continue

            assign_cmid: int | None = None
            href_match = re.search(r'/mod/assign/view\.php\?id=(\d+)', cols[0])
            if href_match:
                assign_cmid = int(href_match.group(1))

            clean_cols = []
            for c in cols:
                clean = re.sub(r'<div class="action-menu.*', '', c, flags=re.DOTALL)
                clean = re.sub(r'<[^>]+>', ' ', clean).strip()
                clean = clean.replace('&ndash;', '-').replace('&nbsp;', '')
                clean = re.sub(r'\s+', ' ', clean).strip()
                clean_cols.append(clean)

            if not any(clean_cols):
                continue
            if clean_cols[0] == 'Ítem de calificación' or len(clean_cols) < 6:
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

    def get_grades(self, course_id: int) -> list["GradeItem"]:
        response = self._http.get(
            f"/grade/report/user/index.php?id={course_id}", follow_redirects=True
        )
        return [item for item, _ in self._parse_grade_table(response.text)]

    def get_grades_with_status(self, course_id: int) -> list["GradeItem"]:
        """Like ``get_grades`` but also fetches submission status for assignments."""
        response = self._http.get(
            f"/grade/report/user/index.php?id={course_id}", follow_redirects=True
        )
        parsed = self._parse_grade_table(response.text)
        items: list[GradeItem] = []
        for item, cmid in parsed:
            if cmid is not None:
                try:
                    details = self.get_assignment_details(cmid)
                    item.status = details.submission_status
                except Exception:
                    pass
            items.append(item)
        return items

    def get_assignment_details(self, assignment_cmid: int) -> "AssignmentDetails":
        resp = self._http.get(f"/mod/assign/view.php?id={assignment_cmid}")
        html = resp.text

        grade_match = re.search(r'<th[^>]*>Calificación</th>(.*?)</td>', html, re.DOTALL | re.IGNORECASE)
        grade_str = ""
        if grade_match:
            grade_str = re.sub(r'<[^>]+>', '', grade_match.group(1)).strip()

        status_match = re.search(
            r'<th[^>]*>\s*Estado de la entrega\s*</th>\s*<td[^>]*>(.*?)</td>',
            html, re.DOTALL,
        )
        submission_status = ""
        if status_match:
            submission_status = re.sub(r'<[^>]+>', '', status_match.group(1)).strip()

        details = AssignmentDetails(grade=grade_str, comments=[], submission_status=submission_status)

        config_match = re.search(r'M\.core_comment\.init\([^,]+,\s*({[^}]+})\);', html)
        if not config_match:
            return details

        try:
            config = json.loads(config_match.group(1))
            payload = {
                "action": "get",
                "client_id": config["client_id"],
                "itemid": config["itemid"],
                "area": config["commentarea"],
                "courseid": config["courseid"],
                "contextid": config["contextid"],
                "component": config["component"],
                "sesskey": self._sesskey
            }
            res = self._http.post("/comment/comment_ajax.php", data=payload)
            data = res.json()

            if "list" not in data:
                return details

            for c in data["list"]:
                clean_content = re.sub(r'<[^>]+>', ' ', c.get("content", "")).strip()
                clean_content = re.sub(r'\s+', ' ', clean_content)
                details.comments.append(
                    SubmissionComment(
                        author=c.get("fullname", "Unknown"),
                        date=c.get("time", ""),
                        content=clean_content,
                    )
                )

        except Exception as e:
            pass  # Fail gracefully for comments if AJAX fails, keeping the parsed grade
            
        return details


@dataclass
class Course:
    id: int
    fullname: str
    url: str


@dataclass
class Resource:
    id: int
    name: str
    module: str
    url: str | None = None

    @property
    def type_label(self) -> str:
        return MODULE_TYPE_LABELS.get(self.module, self.module)


@dataclass
class Section:
    id: int
    number: int
    name: str
    resources: list[Resource] = field(default_factory=list)


@dataclass
class Event:
    id: int
    name: str
    course_name: str
    module: str
    timestamp: int
    url: str
    action: str

    @property
    def date(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%d/%m/%Y %H:%M")


@dataclass
class Discussion:
    id: int
    title: str


@dataclass
class ForumPost:
    id: int
    subject: str
    author: str
    message: str
    timestamp: int

    @property
    def date(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%d/%m/%Y %H:%M")

    @property
    def clean_message(self) -> str:
        return re.sub(r"<[^>]+>", "", self.message).strip()


class MoodleClientError(Exception):
    pass
