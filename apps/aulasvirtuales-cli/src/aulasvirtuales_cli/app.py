import asyncio
import os
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
from aulasvirtuales.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    get_credentials,
    get_token,
    is_session_valid,
    login,
    save_token,
)
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


def is_repl_context() -> bool:
    """Return True when the current command is being invoked from the interactive REPL."""
    return os.environ.get("AULASVIRTUALES_REPL") == "1"


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
    try:
        token = login(username, password)
    except InvalidCredentialsError:
        console.print(
            "❌ Las credenciales guardadas fueron rechazadas. "
            "Ejecutá [bold]aulasvirtuales login[/bold] para re-autenticar.",
            style="red",
        )
        raise typer.Exit(1)
    except AuthenticationError as e:
        console.print(f"❌ Error de autenticación: {e}", style="red")
        raise typer.Exit(1)
    save_token(token)
    return MoodleClient(token)


def convert_file(path: Path, to_format: str, output_dir: Path) -> Path:
    """Convert a downloaded file to the requested format.

    Fails fast with ``typer.Exit(1)`` on any conversion problem — intended
    for single-resource downloads where the user wants immediate feedback.
    """
    if path.suffix.lower() == f".{to_format}":
        return path

    from aulasvirtuales.converter import convert

    try:
        with console.status(
            f"[cyan]  ⚙ Converting {path.name} to {to_format}...[/cyan]",
            spinner="dots",
        ):
            return convert(path, to_format, output_dir, reporter=reporter)
    except ValueError as e:
        console.print(str(e), style="red")
        raise typer.Exit(1)
    except (ImportError, FileNotFoundError) as e:
        console.print(str(e), style="red")
        raise typer.Exit(1)


def convert_file_best_effort(path: Path, to_format: str, output_dir: Path) -> Path:
    """Convert a file, or warn and keep the original on unsupported formats.

    Used by batch operations (``download_all``) where one unsupported file
    should not abort the entire batch.
    """
    if path.suffix.lower() == f".{to_format}":
        return path

    from aulasvirtuales.converter import convert

    try:
        with console.status(
            f"[cyan]  ⚙ Converting {path.name} to {to_format}...[/cyan]",
            spinner="dots",
        ):
            return convert(path, to_format, output_dir, reporter=reporter)
    except ValueError:
        console.print(
            f"  [yellow]⚠[/yellow] Skipping conversion: no converter for "
            f"{path.suffix} → {to_format} (file kept as-is)",
            style="yellow",
        )
        return path
    except (ImportError, FileNotFoundError) as e:
        console.print(f"  [yellow]⚠[/yellow] {e}", style="yellow")
        return path


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

        async def on_status(message: str) -> None:
            progress.update(task_id, description=message)

        result = asyncio.run(
            ocr_and_save(
                path, provider, model,
                provider_config=provider_kwargs,
                output_format=output_format,
                output_dir=output_dir,
                on_page=on_page,
                on_status=on_status,
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
