from pathlib import Path
from typing import Protocol


class ProgressReporter(Protocol):
    def on_step(self, message: str, output: Path) -> None: ...
    def on_error(self, message: str) -> None: ...
