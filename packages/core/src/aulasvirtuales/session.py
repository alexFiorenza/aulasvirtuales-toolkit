import re

import httpx

BASE_URL = "https://aulasvirtuales.frba.utn.edu.ar"


class MoodleClientError(Exception):
    pass


class MoodleSession:
    """Shared infrastructure: HTTP client, session key, and AJAX wrapper."""

    def __init__(self, session_cookie: str) -> None:
        self.http = httpx.Client(
            base_url=BASE_URL,
            cookies={"MoodleSession": session_cookie},
        )
        self.sesskey = self._fetch_sesskey()

    def _fetch_sesskey(self) -> str:
        response = self.http.get("/my/", follow_redirects=True)
        match = re.search(r'"sesskey":"(\w+)"', response.text)
        if not match:
            raise MoodleClientError("Could not extract sesskey from dashboard")
        return match.group(1)

    def ajax(self, method: str, args: dict) -> dict:
        response = self.http.post(
            f"/lib/ajax/service.php?sesskey={self.sesskey}",
            json=[{"index": 0, "methodname": method, "args": args}],
        )
        data = response.json()
        if data[0].get("error"):
            raise MoodleClientError(data[0]["exception"]["message"])
        return data[0]["data"]
