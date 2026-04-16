from pathlib import Path

from fastmcp import Context
from fastmcp.utilities.types import Image

from aulasvirtuales.config import get_download_dir
from aulasvirtuales.downloader import download_file, filename_from_url, get_resource_files
from aulasvirtuales_mcp.server import get_client, mcp, convert_file, ocr_convert_file, resolve_ocr_config


def _find_resource(client, course_id: int, resource_id: int):
    """Locate a resource inside course sections."""
    sections = client.get_course_contents(course_id)
    for section in sections:
        for r in section.resources:
            if r.id == resource_id:
                return r, sections
    return None, sections


@mcp.tool()
async def download(
    course_id: int | str,
    resource_id: int | str,
    ctx: Context,
    output: str | None = None,
    to: str | None = None,
    file: str | None = None,
    ocr: bool = False,
    force_ocr: bool = False,
    ocr_provider: str | None = None,
    ocr_model: str | None = None,
) -> str:
    """Download a resource (file or folder) from a course with optional conversion and OCR.

    This is the full-featured download tool, equivalent to the CLI's `aulasvirtuales download` command.

    Args:
        course_id: The Moodle course ID.
        resource_id: The resource ID (must be a File or Folder type).
        output: Destination directory or file path. Defaults to the configured download directory (~/aulasvirtuales).
        to: Convert after download. Supported conversions: .docx->pdf, .docx->md, .pdf->md, .pptx->pdf, .pptx->md. Use "md" or "txt" with OCR.
        file: Download only files whose name contains this substring (case-insensitive). Useful for folders with many files.
        ocr: If true, use a vision LLM for OCR-based conversion instead of native parsing. Requires ocr_provider and ocr_model to be set (via params or CLI config). Defaults the output format to "md" if `to` is not specified. On PDFs, runs the pdf-inspector classifier gate first: text-based PDFs are refused (use `to="md"` instead), mixed PDFs use a hybrid pipeline (native text + vision OCR on scanned pages only).
        force_ocr: If true, bypass the classifier gate and run vision OCR even on text-based PDFs. Only pass true when the user has explicitly asked for OCR despite the warning. Ignored when `ocr=false`.
        ocr_provider: OCR provider override (e.g. "ollama", "openrouter"). Falls back to CLI-configured value.
        ocr_model: OCR model name override (e.g. "llava", "google/gemini-2.0-flash-001"). Falls back to CLI-configured value.

    Returns:
        A summary of downloaded (and optionally converted) file paths. OCR progress
        is streamed via MCP progress notifications while the conversion runs.
    """
    course_id, resource_id = int(course_id), int(resource_id)

    provider = model = ""
    provider_kwargs: dict = {}
    if ocr:
        if not to:
            to = "md"
        if to not in ("md", "txt"):
            raise ValueError("OCR only supports 'md' or 'txt' as output format.")
        provider, model, provider_kwargs = resolve_ocr_config(ocr_provider, ocr_model)

    dest_dir: Path
    dest_filename: str | None = None

    if output is not None:
        out_path = Path(output).expanduser()
        if out_path.is_dir() or not out_path.suffix:
            dest_dir = out_path
        else:
            dest_dir = out_path.parent
            dest_filename = out_path.name
    else:
        dest_dir = get_download_dir()

    dest_dir.mkdir(parents=True, exist_ok=True)

    client = get_client()
    resource, _ = _find_resource(client, course_id, resource_id)

    if not resource:
        raise ValueError(f"Resource {resource_id} not found in course {course_id}.")

    if resource.module not in ("resource", "folder"):
        raise ValueError(f"Resource type '{resource.module}' is not downloadable.")

    file_urls = get_resource_files(client._http, resource.id, resource.module)
    if not file_urls:
        raise ValueError("No downloadable files found.")

    if file:
        pattern = file.lower()
        file_urls = [
            url for url in file_urls
            if pattern in filename_from_url(url).lower()
        ]
        if not file_urls:
            raise ValueError(f"No files matching '{file}' in this resource.")

    if dest_filename and len(file_urls) > 1:
        raise ValueError(
            "Cannot use a file path as destination for a resource with multiple files. "
            "Use a directory instead."
        )

    results: list[str] = []

    async def on_page(current: int, total: int) -> None:
        await ctx.report_progress(current, total, f"OCR page {current}/{total}")

    for url in file_urls:
        path = download_file(client._http, url, dest_dir, filename=dest_filename)
        results.append(f"✓ Downloaded: {path}")

        if ocr and to:
            from aulasvirtuales.ocr import OcrGateRefusalError

            try:
                converted = await ocr_convert_file(
                    path, to, dest_dir, provider, model, provider_kwargs, on_page, force=force_ocr
                )
                results.append(f"  ✓ OCR converted: {converted}")
            except OcrGateRefusalError as exc:
                results.append(f"  ⚠ OCR skipped: {exc}")
        elif to:
            converted = convert_file(path, to, dest_dir)
            results.append(f"  ✓ Converted: {converted}")

    return "\n".join(results)


@mcp.tool()
def read_downloaded_file(filename: str | None = None) -> list[str | Image]:
    """Read a file from the local downloads directory.

    If no filename is provided, lists all available files in the downloads directory.
    If a filename is provided, reads and returns its content.

    This is useful after calling `download` to read the converted file and pass its
    content to other tools or MCP servers (e.g. saving to Obsidian as a note).

    Supported content types:
    - Text files (.txt, .md, .csv, .json, .xml, .html): returned as text.
    - PDF files: basic text extraction.
    - Images (.png, .jpg, .jpeg, .gif, .bmp, .tiff, .webp): returned as image content.
    - Other files: attempted raw text read.

    Args:
        filename: Name of the file to read (e.g. "apunte.md"). If omitted, lists all files in the downloads directory.

    Returns:
        The file content, or a listing of available files.
    """
    downloads_dir = get_download_dir()

    if not downloads_dir.exists():
        return ["Downloads directory is empty. Use the `download` tool first to download files."]

    if filename is None:
        files = sorted(f.name for f in downloads_dir.iterdir() if f.is_file())
        if not files:
            return ["Downloads directory is empty. Use the `download` tool first to download files."]
        listing = f"Files in {downloads_dir}:\n" + "\n".join(f"  - {f}" for f in files)
        return [listing]

    file_path = downloads_dir / filename
    if not file_path.exists():
        available = sorted(f.name for f in downloads_dir.iterdir() if f.is_file())
        return [
            f"File '{filename}' not found in {downloads_dir}.\n"
            f"Available files:\n" + "\n".join(f"  - {f}" for f in available)
        ]

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"}
    suffix = file_path.suffix.lower()

    try:
        if suffix in IMAGE_EXTENSIONS:
            return [f"--- Image: {file_path.name} ---", Image(path=file_path)]
        elif suffix == ".pdf":
            import fitz
            fitz.TOOLS.mupdf_display_errors(False)
            doc = fitz.open(str(file_path))
            pages = [page.get_text() for page in doc]
            doc.close()
            return [f"--- File: {file_path.name} ---\n" + "\n".join(pages)]
        else:
            return [f"--- File: {file_path.name} ---\n" + file_path.read_text(encoding="utf-8", errors="ignore")]
    except Exception as e:
        return [f"[Failed to read {file_path.name}: {e}]"]


@mcp.tool()
def clear_downloads(force: bool = False) -> str:
    """Clear all downloaded files from the configured download directory.

    Use this after completing download tasks to free disk space.

    Args:
        force: If true, skip confirmation and delete immediately. Default is false.

    Returns:
        A message indicating success or that the directory was already empty.
    """
    import shutil

    d_dir = get_download_dir()

    if not d_dir.exists() or not any(d_dir.iterdir()):
        return f"Directory {d_dir} is already empty."

    if not force:
        return (
            f"Download directory {d_dir} contains files. "
            f"Call clear_downloads(force=true) to confirm deletion."
        )

    try:
        shutil.rmtree(d_dir)
        d_dir.mkdir(parents=True, exist_ok=True)
        return f"✓ Successfully cleared {d_dir}"
    except Exception as e:
        raise ValueError(f"Failed to clear downloads directory: {e}")
