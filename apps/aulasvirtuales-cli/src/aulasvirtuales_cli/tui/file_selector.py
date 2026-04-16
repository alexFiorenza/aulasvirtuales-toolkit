from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, SelectionList
from textual.widgets.selection_list import Selection


class FileSelectorApp(App):
    """Textual checkbox screen for picking files to download from a folder."""

    CSS = """
    Screen {
        align: center middle;
    }

    #form {
        width: 90;
        height: 80%;
        padding: 1 2;
        border: round $accent;
    }

    SelectionList {
        height: 1fr;
        padding-top: 1;
    }

    #buttons {
        height: auto;
        align-horizontal: right;
        padding-top: 1;
    }

    Button {
        margin-left: 2;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, files: list[tuple[str, str]]) -> None:
        super().__init__()
        self._files = files
        self._result: list[str] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="form"):
            yield Label("[b]Select files to download[/b]")
            yield SelectionList[str](
                *[Selection(name, url, True) for name, url in self._files],
                id="files",
            )
            with Horizontal(id="buttons"):
                yield Button("Select all", id="select_all")
                yield Button("Deselect all", id="deselect_all")
                yield Button("Cancel", id="cancel")
                yield Button("Confirm", id="confirm", variant="primary")
        yield Footer()

    def action_cancel(self) -> None:
        self._result = None
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        selection_list = self.query_one("#files", SelectionList)
        if event.button.id == "select_all":
            selection_list.select_all()
            return
        if event.button.id == "deselect_all":
            selection_list.deselect_all()
            return
        if event.button.id == "cancel":
            self._result = None
            self.exit()
            return
        if event.button.id == "confirm":
            self._result = list(selection_list.selected)
            self.exit()


def select_files(files: list[tuple[str, str]]) -> list[str] | None:
    """Launch the selector and return the list of chosen URLs, or None if cancelled.

    Args:
        files: List of ``(filename, url)`` tuples to display.

    Returns:
        List of selected URLs, or ``None`` if the user cancelled.
    """
    app = FileSelectorApp(files)
    app.run()
    return app._result
