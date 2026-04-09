from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from aulasvirtuales.auth import (
    delete_credentials,
    delete_token,
    get_credentials,
    get_token,
    is_session_valid,
    login,
    save_credentials,
    save_token,
)
from aulasvirtuales.client import MoodleClient
from aulasvirtuales.config import (
    get_download_dir,
    get_ocr_config,
    set_download_dir,
    set_ocr_model,
    set_ocr_provider,
    set_ocr_provider_kwarg,
)
from aulasvirtuales.downloader import download_file, get_resource_files, filename_from_url

app = typer.Typer(name="aulasvirtuales")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from aulasvirtuales_cli.repl import start_repl
        start_repl(app)


CONVERSIONS: dict[tuple[str, str], tuple[str, str]] = {
    (".docx", "pdf"): ("docx", "uv sync --extra docx"),
    (".docx", "md"): ("docx,markdown", "uv sync --extra docx --extra markdown"),
    (".pdf", "md"): ("markdown", "uv sync --extra markdown"),
    (".pptx", "pdf"): ("libreoffice", "brew install --cask libreoffice"),
    (".pptx", "md"): ("libreoffice,markdown", "brew install --cask libreoffice && uv sync --extra markdown"),
}


def _convert_file(path: Path, to_format: str, output_dir: Path) -> Path:
    """Convert a downloaded file to the requested format."""
    suffix = path.suffix.lower()
    if suffix == f".{to_format}":
        return path

    key = (suffix, to_format)
    if key not in CONVERSIONS:
        console.print(
            f"Conversion from {suffix} to {to_format} is not supported.",
            style="red",
        )
        raise typer.Exit(1)

    if suffix == ".pptx" and to_format in ("pdf", "md"):
        try:
            from aulasvirtuales.converter import pptx_to_pdf
        except ImportError:
            console.print(
                "LibreOffice is required. Install: brew install --cask libreoffice",
                style="red",
            )
            raise typer.Exit(1)
        try:
            pdf_path = pptx_to_pdf(path, output_dir)
        except FileNotFoundError as e:
            console.print(str(e), style="red")
            raise typer.Exit(1)
        console.print(f"  [green]✓[/green] {pdf_path.name} (pdf)")
        if to_format == "pdf":
            return pdf_path
        path = pdf_path
        suffix = ".pdf"

    if suffix == ".docx" and to_format in ("pdf", "md"):
        try:
            from aulasvirtuales.converter import docx_to_pdf
        except ImportError:
            console.print(
                "docx2pdf is not installed. Run: uv sync --extra docx",
                style="red",
            )
            raise typer.Exit(1)
        pdf_path = docx_to_pdf(path, output_dir)
        console.print(f"  [green]✓[/green] {pdf_path.name} (pdf)")
        if to_format == "pdf":
            return pdf_path
        path = pdf_path
        suffix = ".pdf"

    if suffix == ".pdf" and to_format == "md":
        try:
            from aulasvirtuales.converter import convert_and_save
        except ImportError:
            console.print(
                "pymupdf4llm is not installed. Run: uv sync --extra markdown",
                style="red",
            )
            raise typer.Exit(1)
        md_path = convert_and_save(path, output_dir)
        console.print(f"  [green]✓[/green] {md_path.name} (markdown)")
        return md_path

    return path


def _resolve_ocr_config(
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


def _ocr_convert_file(
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

    with console.status("") as status:
        def on_page(current: int, total: int) -> None:
            status.update(f"  [cyan]OCR page {current}/{total}...[/cyan]")

        result = ocr_and_save(
            path, provider, model,
            provider_config=provider_kwargs,
            output_format=output_format,
            output_dir=output_dir,
            on_page=on_page,
        )

    ext_label = "markdown" if output_format == "md" else "text"
    console.print(f"  [green]✓[/green] {result.name} ({ext_label}, ocr)")
    return result


def _get_client() -> MoodleClient:
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


@app.command(name="login")
def login_cmd() -> None:
    """Authenticate and store credentials securely in the OS keychain."""
    import getpass

    username = console.input("[cyan]Username:[/cyan] ")
    password = getpass.getpass("Password: ")

    console.print("Authenticating...", style="yellow")
    token = login(username, password)
    save_credentials(username, password)
    save_token(token)
    console.print("Logged in successfully. Credentials stored in keychain.", style="green")


@app.command(name="logout")
def logout_cmd() -> None:
    """Remove stored credentials and session from the OS keychain."""
    delete_credentials()
    delete_token()
    console.print("Credentials and session removed from keychain.", style="green")


@app.command()
def status() -> None:
    """Check authentication status."""
    creds = get_credentials()
    if not creds:
        console.print("Not logged in. Run [bold]aulasvirtuales login[/bold].", style="red")
        return

    username, _ = creds
    token = get_token()
    if token and is_session_valid(token):
        console.print(f"Logged in as [bold]{username}[/bold] (session active).", style="green")
    else:
        console.print(f"Logged in as [bold]{username}[/bold] (session expired, will re-auth on next command).", style="yellow")


@app.command()
def courses() -> None:
    """List enrolled courses."""
    client = _get_client()
    course_list = client.get_courses()

    table = Table(title="My Courses")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="white")

    for c in course_list:
        table.add_row(str(c.id), c.fullname)

    console.print(table)


@app.command()
def resources(course_id: int = typer.Argument(help="Course ID")) -> None:
    """List sections and resources of a course."""
    client = _get_client()
    sections = client.get_course_contents(course_id)

    for section in sections:
        console.print(f"\n[bold magenta]{section.name}[/bold magenta]")
        if not section.resources:
            console.print("  (empty)", style="dim")
            continue

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Type", style="green")
        table.add_column("Name", style="white")

        for r in section.resources:
            table.add_row(str(r.id), r.type_label, r.name)

        console.print(table)


@app.command()
def download(
    course_id: int = typer.Argument(help="Course ID"),
    resource_id: int = typer.Argument(help="Resource ID (File or Folder)"),
    output: Path = typer.Option(
        None, "--output", "-o",
        help="Destination directory or file path",
    ),
    to: str = typer.Option(
        None, "--to",
        help="Convert to format after download (pdf, md, txt)",
    ),
    file: str = typer.Option(
        None, "--file", "-f",
        help="Download only files matching this substring (case-insensitive)",
    ),
    ocr: bool = typer.Option(
        False, "--ocr",
        help="Use a vision LLM for OCR conversion",
    ),
    ocr_provider: str = typer.Option(
        None, "--ocr-provider",
        help="OCR provider override (ollama, openrouter)",
    ),
    ocr_model: str = typer.Option(
        None, "--ocr-model",
        help="OCR model name override",
    ),
) -> None:
    """Download a resource (file or folder) from a course."""
    provider = model = ""
    provider_kwargs: dict = {}
    if ocr:
        if not to:
            to = "md"
        if to not in ("md", "txt"):
            console.print("OCR only supports --to md or --to txt.", style="red")
            raise typer.Exit(1)
        provider, model, provider_kwargs = _resolve_ocr_config(ocr_provider, ocr_model)

    dest_dir: Path
    dest_filename: str | None = None

    if output is not None:
        if output.is_dir() or not output.suffix:
            dest_dir = output
        else:
            dest_dir = output.parent
            dest_filename = output.name
    else:
        dest_dir = get_download_dir()

    client = _get_client()
    sections = client.get_course_contents(course_id)

    resource = None
    for section in sections:
        for r in section.resources:
            if r.id == resource_id:
                resource = r
                break

    if not resource:
        console.print(f"Resource {resource_id} not found in course {course_id}.", style="red")
        raise typer.Exit(1)

    if resource.module not in ("resource", "folder"):
        console.print(f"Resource type '{resource.type_label}' is not downloadable.", style="red")
        raise typer.Exit(1)

    file_urls = get_resource_files(client._http, resource.id, resource.module)
    if not file_urls:
        console.print("No downloadable files found.", style="red")
        raise typer.Exit(1)

    if file:
        pattern = file.lower()
        file_urls = [
            url for url in file_urls
            if pattern in filename_from_url(url).lower()
        ]
        if not file_urls:
            console.print(f"No files matching '{file}' in this resource.", style="red")
            raise typer.Exit(1)

    if dest_filename and len(file_urls) > 1:
        console.print(
            "Cannot use a file path as destination for a resource with multiple files. "
            "Use a directory instead.",
            style="red",
        )
        raise typer.Exit(1)

    console.print(f"Downloading {len(file_urls)} file(s)...", style="cyan")

    for url in file_urls:
        path = download_file(client._http, url, dest_dir, filename=dest_filename)
        console.print(f"  [green]✓[/green] {path.name}")

        if ocr and to:
            _ocr_convert_file(path, to, dest_dir, provider, model, provider_kwargs)
        elif to:
            _convert_file(path, to, dest_dir)


@app.command()
def download_all(
    course_id: int = typer.Argument(help="Course ID"),
    output: Path = typer.Option(None, "--output", "-o", help="Download directory"),
    to: str = typer.Option(
        None, "--to",
        help="Convert to format after download (pdf, md, txt)",
    ),
    ocr: bool = typer.Option(
        False, "--ocr",
        help="Use a vision LLM for OCR conversion",
    ),
    ocr_provider: str = typer.Option(
        None, "--ocr-provider",
        help="OCR provider override (ollama, openrouter)",
    ),
    ocr_model: str = typer.Option(
        None, "--ocr-model",
        help="OCR model name override",
    ),
) -> None:
    """Download all files and folders from a course."""
    provider = model = ""
    provider_kwargs: dict = {}
    if ocr:
        if not to:
            to = "md"
        if to not in ("md", "txt"):
            console.print("OCR only supports --to md or --to txt.", style="red")
            raise typer.Exit(1)
        provider, model, provider_kwargs = _resolve_ocr_config(ocr_provider, ocr_model)

    dest = output or get_download_dir()
    client = _get_client()
    sections = client.get_course_contents(course_id)

    downloadable = [
        r
        for section in sections
        for r in section.resources
        if r.module in ("resource", "folder")
    ]

    if not downloadable:
        console.print("No downloadable files in this course.", style="red")
        raise typer.Exit(1)

    console.print(f"Found {len(downloadable)} downloadable resources.", style="cyan")

    for resource in downloadable:
        file_urls = get_resource_files(client._http, resource.id, resource.module)
        for url in file_urls:
            path = download_file(client._http, url, dest)
            console.print(f"  [green]✓[/green] {path.name}")

            if ocr and to:
                _ocr_convert_file(path, to, dest, provider, model, provider_kwargs)
            elif to:
                _convert_file(path, to, dest)

    console.print("\n[bold green]Download complete.[/bold green]")


@app.command()
def events(
    course_id: int = typer.Argument(None, help="Course ID (optional, omit to show all)"),
) -> None:
    """Show upcoming events and pending assignments."""
    client = _get_client()
    event_list = client.get_upcoming_events(course_id)

    if not event_list:
        console.print("No upcoming events.", style="dim")
        raise typer.Exit()

    table = Table(title="Upcoming Events")
    table.add_column("Date", style="cyan")
    table.add_column("Course", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Name", style="white")
    table.add_column("Action", style="yellow")

    for e in event_list:
        table.add_row(e.date, e.course_name, e.module, e.name, e.action)

    console.print(table)


@app.command()
def forums(course_id: int = typer.Argument(help="Course ID")) -> None:
    """List forums in a course."""
    client = _get_client()
    forum_list = client.get_forums(course_id)

    if not forum_list:
        console.print("No forums in this course.", style="dim")
        raise typer.Exit()

    table = Table(title="Forums")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="white")

    for f in forum_list:
        table.add_row(str(f.id), f.name)

    console.print(table)


@app.command()
def discussions(
    forum_id: int = typer.Argument(help="Forum ID"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of discussions to show"),
) -> None:
    """List discussions in a forum."""
    client = _get_client()
    disc_list = client.get_forum_discussions(forum_id, limit)

    if not disc_list:
        console.print("No discussions in this forum.", style="dim")
        raise typer.Exit()

    table = Table(title="Discussions")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Title", style="white")

    for d in disc_list:
        table.add_row(str(d.id), d.title)

    console.print(table)


@app.command()
def posts(discussion_id: int = typer.Argument(help="Discussion ID")) -> None:
    """Show messages in a forum discussion."""
    client = _get_client()
    post_list = client.get_discussion_posts(discussion_id)

    if not post_list:
        console.print("No posts in this discussion.", style="dim")
        raise typer.Exit()

    for p in post_list:
        console.print(f"\n[bold cyan]{p.author}[/bold cyan] — [dim]{p.date}[/dim]")
        console.print(f"[bold]{p.subject}[/bold]")
        console.print(p.clean_message)
        console.print("─" * 60, style="dim")


@app.command()
def config(
    download_dir: Path = typer.Option(None, "--download-dir", "-d", help="Set default download directory"),
    ocr_provider: str = typer.Option(None, "--ocr-provider", help="Set OCR provider (ollama, openrouter)"),
    ocr_model: str = typer.Option(None, "--ocr-model", help="Set OCR model name"),
    openrouter_api_key: str = typer.Option(None, "--openrouter-api-key", help="Set OpenRouter API key"),
    ollama_base_url: str = typer.Option(None, "--ollama-base-url", help="Set Ollama base URL"),
) -> None:
    """View or update CLI configuration."""
    changed = False

    if download_dir is not None:
        set_download_dir(download_dir)
        console.print(f"Download directory set to: {download_dir.expanduser().resolve()}", style="green")
        changed = True

    if ocr_provider is not None:
        set_ocr_provider(ocr_provider)
        console.print(f"OCR provider set to: {ocr_provider}", style="green")
        changed = True

    if ocr_model is not None:
        set_ocr_model(ocr_model)
        console.print(f"OCR model set to: {ocr_model}", style="green")
        changed = True

    if openrouter_api_key is not None:
        set_ocr_provider_kwarg("openrouter", "api_key", openrouter_api_key)
        console.print("OpenRouter API key saved.", style="green")
        changed = True

    if ollama_base_url is not None:
        set_ocr_provider_kwarg("ollama", "base_url", ollama_base_url)
        console.print(f"Ollama base URL set to: {ollama_base_url}", style="green")
        changed = True

    if changed:
        return

    current = get_download_dir()
    console.print(f"Download directory: {current}", style="cyan")
    ocr_cfg = get_ocr_config()
    if ocr_cfg.get("provider") or ocr_cfg.get("model"):
        console.print(f"OCR provider: {ocr_cfg.get('provider', 'not set')}", style="cyan")
        console.print(f"OCR model: {ocr_cfg.get('model', 'not set')}", style="cyan")
        if ocr_cfg.get("openrouter", {}).get("api_key"):
            console.print("OpenRouter API key: [dim]****[/dim]", style="cyan")
    else:
        console.print("OCR: not configured", style="dim")
