import re
from dataclasses import dataclass, field
from datetime import datetime

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
    comments: list["SubmissionComment"]
    submission_status: str = ""


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
    description: str | None = None

    @property
    def type_label(self) -> str:
        return MODULE_TYPE_LABELS.get(self.module, self.module)


@dataclass
class ResourceContent:
    resource_id: int
    module: str
    content: str


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
