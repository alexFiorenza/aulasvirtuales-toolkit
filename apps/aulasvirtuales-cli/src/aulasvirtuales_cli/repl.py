import os
import re
import shlex
from importlib.resources import files

from prompt_toolkit import PromptSession
from prompt_toolkit.application import get_app
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.filters import has_completions
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console

from aulasvirtuales.config import CONFIG_DIR

console = Console()

HISTORY_FILE = CONFIG_DIR / "history"

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")

_TEXT_LINES = [
    "╔═╗╦ ╦╦  ╔═╗╔═╗",
    "╠═╣║ ║║  ╠═╣╚═╗",
    "╩ ╩╚═╝╩═╝╩ ╩╚═╝",
    "",
    "╦  ╦╦╦═╗╔╦╗╦ ╦╔═╗╦  ╔═╗╔═╗",
    "╚╗╔╝║╠╦╝ ║ ║ ║╠═╣║  ║╣ ╚═╗",
    " ╚╝ ╩╩╚═ ╩ ╚═╝╩ ╩╩═╝╚═╝╚═╝",
]

_COLOR = "\x1b[38;2;183;18;52m"  # #b71234
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"


def _build_banner() -> str:
    logo_raw = files("aulasvirtuales_cli.resources").joinpath("logo_art.txt").read_text()
    logo_lines = logo_raw.splitlines()
    # Drop cursor-hide/show control lines
    logo_lines = [l for l in logo_lines if _ANSI_RE.sub("", l).strip() or _ANSI_RE.sub("", l)]
    # Remove last line if it's just a cursor restore
    if logo_lines and not _ANSI_RE.sub("", logo_lines[-1]).strip():
        logo_lines.pop()

    logo_visible_width = max(len(_ANSI_RE.sub("", l)) for l in logo_lines)
    gap = "   "
    total_logo_lines = len(logo_lines)

    # Vertically center the text block next to the logo
    text_height = len(_TEXT_LINES)
    top_offset = (total_logo_lines - text_height) // 2

    combined = []
    for i, logo_line in enumerate(logo_lines):
        visible_len = len(_ANSI_RE.sub("", logo_line))
        pad = " " * (logo_visible_width - visible_len)
        text_idx = i - top_offset
        if 0 <= text_idx < text_height:
            right = f"{_BOLD}{_COLOR}{_TEXT_LINES[text_idx]}{_RESET}"
        else:
            right = ""
        combined.append(f"{logo_line}{pad}{gap}{right}")

    return "\n".join(combined)


_BANNER = _build_banner()

BANNER_HELP = "[dim]Tab to autocomplete, ↑/↓ for history, Ctrl+D to quit[/dim]"


class CommandCompleter(Completer):
    """Two-level completer: commands first, then their options/arguments."""

    def __init__(self, commands: dict[str, str], click_app) -> None:
        self.commands = commands
        self.click_app = click_app

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        parts = text.split()

        # No input or still typing the command name → suggest commands
        if len(parts) == 0 or (len(parts) == 1 and not text.endswith(" ")):
            word = parts[0] if parts else ""
            for name, description in self.commands.items():
                if name.startswith(word):
                    yield Completion(
                        name,
                        start_position=-len(word),
                        display_meta=description,
                    )
            return

        # Command is complete, suggest its parameters
        cmd_name = parts[0]
        click_commands = getattr(self.click_app, "commands", {})
        cmd = click_commands.get(cmd_name)
        if not cmd:
            return

        current_word = parts[-1] if not text.endswith(" ") else ""
        already_used = set(parts[1:])

        for param in cmd.params:
            if param.hidden:
                continue
            help_text = getattr(param, "help", "") or ""

            if param.human_readable_name == "ARGS" or hasattr(param, "opts"):
                # Options (--flag style)
                for opt in getattr(param, "opts", []):
                    if opt in already_used:
                        continue
                    if opt.startswith(current_word):
                        display = f"{cmd_name} {opt}"
                        yield Completion(
                            opt,
                            start_position=-len(current_word),
                            display=display,
                            display_meta=help_text,
                        )

            if hasattr(param, "type") and not getattr(param, "opts", []):
                # Positional arguments
                arg_name = f"<{param.human_readable_name}>"
                if arg_name.startswith(current_word) or not current_word:
                    display = f"{cmd_name} {arg_name}"
                    yield Completion(
                        "",
                        start_position=0,
                        display=display,
                        display_meta=help_text,
                    )


def start_repl(app) -> None:
    """Launch the interactive REPL for the aulasvirtuales CLI."""
    import typer
    from typer.main import get_command

    click_app = get_command(app)
    commands = {}
    if hasattr(click_app, "commands"):
        for name, cmd in click_app.commands.items():
            commands[name] = cmd.get_short_help_str() if cmd.help else ""

    commands["clear"] = "Clear the screen"
    commands["help"] = "Show this help message"
    commands["exit"] = "Quit the interactive shell"

    print(_BANNER)
    console.print(BANNER_HELP)

    completer = CommandCompleter(commands, click_app)

    bindings = KeyBindings()

    @bindings.add("enter", filter=has_completions)
    def accept_completion(event):
        buf = event.current_buffer
        state = buf.complete_state
        if state and state.current_completion:
            buf.apply_completion(state.current_completion)
        else:
            buf.validate_and_handle()

    style = Style.from_dict({
        "completion-menu":                          "bg:default default",
        "completion-menu.completion":               "bg:default default",
        "completion-menu.completion.current":        "bg:default bold underline",
        "completion-menu.meta.completion":           "bg:default #888888",
        "completion-menu.meta.completion.current":   "bg:default #bbbbbb bold",
    })

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        completer=completer,
        complete_while_typing=True,
        style=style,
        key_bindings=bindings,
    )

    os.environ["AULASVIRTUALES_REPL"] = "1"
    try:
        while True:
            try:
                def _show_completions():
                    get_app().current_buffer.start_completion()

                text = session.prompt(
                    HTML("<ansigreen>> </ansigreen>"),
                    pre_run=_show_completions,
                ).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\nBye!", style="dim")
                break

            if not text:
                continue

            if text == "exit":
                console.print("Bye!", style="dim")
                break

            if text == "clear":
                console.clear()
                print(_BANNER)
                console.print(BANNER_HELP)
                continue

            if text == "help":
                _print_help(commands)
                continue

            try:
                args = shlex.split(text)
            except ValueError as e:
                console.print(f"Invalid input: {e}", style="red")
                continue

            try:
                click_app(args, standalone_mode=False)
            except SystemExit:
                pass
            except Exception as e:
                console.print(f"Error: {e}", style="red")
    finally:
        os.environ.pop("AULASVIRTUALES_REPL", None)


def _print_help(commands: dict[str, str]) -> None:
    """Print available commands in a formatted table."""
    from rich.table import Table

    table = Table(show_header=False, box=None, padding=(0, 4))
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="dim")

    for name, help_text in sorted(commands.items()):
        table.add_row(name, help_text)

    console.print()
    console.print(table)
    console.print()
