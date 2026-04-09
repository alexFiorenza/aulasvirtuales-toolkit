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
