from aulasvirtuales.models import GradeItem
from aulasvirtuales.parsers import parse_grade_table
from aulasvirtuales.services.assignments import AssignmentsService
from aulasvirtuales.session import MoodleSession


class GradesService:
    def __init__(self, session: MoodleSession, assignments: AssignmentsService) -> None:
        self._session = session
        self._assignments = assignments

    def get_grades(self, course_id: int) -> list[GradeItem]:
        response = self._session.http.get(
            f"/grade/report/user/index.php?id={course_id}", follow_redirects=True,
        )
        return [item for item, _ in parse_grade_table(response.text)]

    def get_grades_with_status(self, course_id: int) -> list[GradeItem]:
        response = self._session.http.get(
            f"/grade/report/user/index.php?id={course_id}", follow_redirects=True,
        )
        parsed = parse_grade_table(response.text)
        items: list[GradeItem] = []
        for item, cmid in parsed:
            if cmid is not None:
                try:
                    details = self._assignments.get_assignment_details(cmid)
                    item.status = details.submission_status
                except Exception:
                    pass
            items.append(item)
        return items
