import time

from aulasvirtuales.models import Event
from aulasvirtuales.session import MoodleSession


class EventsService:
    def __init__(self, session: MoodleSession) -> None:
        self._session = session

    def get_upcoming_events(self, course_id: int | None = None, limit: int = 20) -> list[Event]:
        if course_id:
            data = self._session.ajax(
                "core_calendar_get_action_events_by_course",
                {"courseid": course_id, "limitnum": limit},
            )
        else:
            data = self._session.ajax(
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
