import re

from aulasvirtuales.models import AssignmentDetails, SubmissionComment
from aulasvirtuales.parsers import parse_assignment_page, strip_html
from aulasvirtuales.session import MoodleSession


class AssignmentsService:
    def __init__(self, session: MoodleSession) -> None:
        self._session = session

    def get_assignment_details(self, assignment_cmid: int) -> AssignmentDetails:
        resp = self._session.http.get(f"/mod/assign/view.php?id={assignment_cmid}")
        grade_str, submission_status, comment_config = parse_assignment_page(resp.text)

        details = AssignmentDetails(
            grade=grade_str, comments=[], submission_status=submission_status,
        )

        if not comment_config:
            return details

        try:
            payload = {
                "action": "get",
                "client_id": comment_config["client_id"],
                "itemid": comment_config["itemid"],
                "area": comment_config["commentarea"],
                "courseid": comment_config["courseid"],
                "contextid": comment_config["contextid"],
                "component": comment_config["component"],
                "sesskey": self._session.sesskey,
            }
            res = self._session.http.post("/comment/comment_ajax.php", data=payload)
            data = res.json()

            if "list" not in data:
                return details

            for c in data["list"]:
                clean_content = strip_html(c.get("content", ""))
                details.comments.append(
                    SubmissionComment(
                        author=c.get("fullname", "Unknown"),
                        date=c.get("time", ""),
                        content=clean_content,
                    )
                )
        except Exception:
            pass

        return details
