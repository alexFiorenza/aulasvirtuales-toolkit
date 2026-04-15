from pathlib import Path

import typer
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from aulasvirtuales.config import get_download_dir
from aulasvirtuales.downloader import download_file, filename_from_url, get_resource_files
from aulasvirtuales_cli.app import app, console, convert_file, get_client, ocr_convert_file, resolve_ocr_config


@app.command()
def courses() -> None:
    """List enrolled courses."""
    with console.status("[cyan]📚 Fetching courses...[/cyan]", spinner="dots"):
        client = get_client()
        course_list = client.get_courses()

    table = Table(title="📚 My Courses")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="white")

    for c in course_list:
        table.add_row(str(c.id), c.fullname)

    console.print(table)


@app.command()
def resources(course_id: int = typer.Argument(help="Course ID")) -> None:
    """List sections and resources of a course."""
    with console.status("[cyan]📂 Fetching course resources...[/cyan]", spinner="dots"):
        client = get_client()
        sections = client.get_course_contents(course_id)

    for section in sections:
        console.print(f"\n[bold magenta]📁 {section.name}[/bold magenta]")
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
        provider, model, provider_kwargs = resolve_ocr_config(ocr_provider, ocr_model)

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

    client = get_client()
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

    console.print(f"[cyan]📥 Downloading {len(file_urls)} file(s)...[/cyan]")

    for url in file_urls:
        name = filename_from_url(url) if dest_filename is None else dest_filename
        with console.status(f"[cyan]  ↓ {name}[/cyan]", spinner="dots"):
            path = download_file(client._http, url, dest_dir, filename=dest_filename)
        console.print(f"  [green]✓[/green] {path.name}")

        if ocr and to:
            ocr_convert_file(path, to, dest_dir, provider, model, provider_kwargs)
        elif to:
            convert_file(path, to, dest_dir)


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
        provider, model, provider_kwargs = resolve_ocr_config(ocr_provider, ocr_model)

    dest = output or get_download_dir()

    with console.status("[cyan]📂 Fetching course contents...[/cyan]", spinner="dots"):
        client = get_client()
        sections = client.get_course_contents(course_id)

    downloadable = [
        r
        for section in sections
        for r in section.resources
        if r.module in ("resource", "folder")
    ]

    if not downloadable:
        console.print("❌ No downloadable files in this course.", style="red")
        raise typer.Exit(1)

    console.print(f"[cyan]📦 Found {len(downloadable)} downloadable resources.[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        resource_task = progress.add_task("📥 Resources", total=len(downloadable))

        for resource in downloadable:
            file_urls = get_resource_files(client._http, resource.id, resource.module)
            for url in file_urls:
                name = filename_from_url(url)
                progress.update(resource_task, description=f"📥 {name}")
                path = download_file(client._http, url, dest)

                if ocr and to:
                    # OCR mostrará su propia barra; pausamos la de arriba para no pisar
                    progress.stop()
                    console.print(f"  [green]✓[/green] {path.name}")
                    ocr_convert_file(path, to, dest, provider, model, provider_kwargs)
                    progress.start()
                elif to:
                    convert_file(path, to, dest)

            progress.advance(resource_task)

        progress.update(resource_task, description="📥 Resources")

    console.print("\n[bold green]✅ Download complete.[/bold green]")


@app.command(name="clear-downloads")
def clear_downloads(
    force: bool = typer.Option(False, "--force", "-y", help="Skip confirmation prompt"),
) -> None:
    """Clear all downloaded files from the configured download directory."""
    import shutil

    d_dir = get_download_dir()

    if not d_dir.exists() or not any(d_dir.iterdir()):
        console.print(f"ℹ️  Directory [cyan]{d_dir}[/cyan] is already empty.", style="dim")
        raise typer.Exit()

    if not force:
        confirm = typer.confirm(f"⚠️  Are you sure you want to delete ALL files in {d_dir}?")
        if not confirm:
            console.print("Cancelled.")
            raise typer.Exit()

    try:
        with console.status(f"[yellow]🗑️  Clearing {d_dir}...[/yellow]", spinner="dots"):
            shutil.rmtree(d_dir)
            d_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"  [green]✓[/green] Successfully cleared {d_dir}")
    except Exception as e:
        console.print(f"❌ Failed to clear downloads directory: {e}", style="red")
