import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from aulasvirtuales_cli import __version__
from aulasvirtuales.auth import get_credentials, get_token, is_session_valid, login, save_token
from aulasvirtuales.client import MoodleClient
from aulasvirtuales.config import get_ocr_config

app = typer.Typer(name="aulasvirtuales")
console = Console()


class RichReporter:
    """CLI implementation of ProgressReporter using Rich console."""

    def on_step(self, message: str, output: Path) -> None:
        console.print(f"  [green]✓[/green] {output.name} ({message})")

    def on_error(self, message: str) -> None:
        console.print(message, style="red")


reporter = RichReporter()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"aulasvirtuales {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", callback=_version_callback, is_eager=True, help="Show version and exit"),
) -> None:
    if ctx.invoked_subcommand is None:
        from aulasvirtuales_cli.repl import start_repl
        start_repl(app)


def get_client() -> MoodleClient:
    token = get_token()
    if token and is_session_valid(token):
        return MoodleClient(token)

    creds = get_credentials()
    if not creds:
        console.print(
            "No credentials found. Run [bold]aulasvirtuales login[/bold] first.",
            style="red",
        )
        raise typer.Exit(1)

    console.print("Session expired or missing, logging in...", style="yellow")
    username, password = creds
    token = login(username, password)
    save_token(token)
    return MoodleClient(token)


def convert_file(path: Path, to_format: str, output_dir: Path) -> Path:
    """Convert a downloaded file to the requested format."""
    if path.suffix.lower() == f".{to_format}":
        return path

    from aulasvirtuales.converter import convert

    try:
        return convert(path, to_format, output_dir, reporter=reporter)
    except ValueError as e:
        console.print(str(e), style="red")
        raise typer.Exit(1)
    except (ImportError, FileNotFoundError) as e:
        console.print(str(e), style="red")
        raise typer.Exit(1)


def resolve_ocr_config(
    ocr_provider: str | None,
    ocr_model: str | None,
) -> tuple[str, str, dict]:
    """Resolve OCR provider, model, and provider kwargs from CLI args and config."""
    ocr_cfg = get_ocr_config()
    provider = ocr_provider or ocr_cfg.get("provider")
    model = ocr_model or ocr_cfg.get("model")
    if not provider or not model:
        console.print(
            "OCR provider and model required. Set with:\n"
            "  aulasvirtuales config --ocr-provider <provider> --ocr-model <model>",
            style="red",
        )
        raise typer.Exit(1)
    provider_kwargs = ocr_cfg.get(provider, {})
    return provider, model, provider_kwargs


def ocr_convert_file(
    path: Path,
    output_format: str,
    output_dir: Path,
    provider: str,
    model: str,
    provider_kwargs: dict,
) -> Path:
    """Convert a file using OCR via a vision LLM."""
    try:
        from aulasvirtuales.ocr import OCR_SUPPORTED_EXTENSIONS, ocr_and_save
    except ImportError:
        console.print(
            "OCR dependencies not installed. Run: uv sync --extra ocr",
            style="red",
        )
        raise typer.Exit(1)

    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return path
    if suffix not in OCR_SUPPORTED_EXTENSIONS:
        console.print(f"OCR not supported for {suffix} files.", style="red")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(f"🔍 OCR {path.name}", total=None)

        async def on_page(current: int, total: int) -> None:
            progress.update(task_id, completed=current, total=total)

        result = asyncio.run(
            ocr_and_save(
                path, provider, model,
                provider_config=provider_kwargs,
                output_format=output_format,
                output_dir=output_dir,
                on_page=on_page,
            )
        )

    ext_label = "markdown" if output_format == "md" else "text"
    console.print(f"  [green]✓[/green] {result.name} ({ext_label}, ocr)")
    return result


# Register command modules — each module adds its @app.command() on import
import aulasvirtuales_cli.commands.auth  # noqa: F401, E402
import aulasvirtuales_cli.commands.courses  # noqa: F401, E402
import aulasvirtuales_cli.commands.events  # noqa: F401, E402
import aulasvirtuales_cli.commands.forums  # noqa: F401, E402
import aulasvirtuales_cli.commands.grades  # noqa: F401, E402
import aulasvirtuales_cli.commands.settings  # noqa: F401, E402
