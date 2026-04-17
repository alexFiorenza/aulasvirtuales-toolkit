import json

from aulasvirtuales.models import Course, Resource, Section
from aulasvirtuales.session import MoodleSession


class CoursesService:
    def __init__(self, session: MoodleSession) -> None:
        self._session = session

    def get_courses(self) -> list[Course]:
        data = self._session.ajax(
            "core_course_get_enrolled_courses_by_timeline_classification",
            {"offset": 0, "limit": 0, "classification": "all", "sort": "fullname"},
        )
        return [
            Course(id=c["id"], fullname=c["fullname"], url=c["viewurl"])
            for c in data["courses"]
        ]

    def get_course_contents(self, course_id: int) -> list[Section]:
        raw = self._session.ajax("core_courseformat_get_state", {"courseid": course_id})
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
                description=cm.get("description") or None,
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
