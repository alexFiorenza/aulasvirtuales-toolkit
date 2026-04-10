import asyncio
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from aulasvirtuales.auth import get_credentials, login, get_token, save_token, is_session_valid
from aulasvirtuales.client import MoodleClient
from aulasvirtuales.downloader import download_file, get_resource_files, filename_from_url
from aulasvirtuales.config import get_download_dir, get_ocr_config

mcp = FastMCP("AulasVirtuales")


# ---------------------------------------------------------------------------
# OCR job registry
# ---------------------------------------------------------------------------

@dataclass
class OcrJob:
    id: str
    filename: str
    current_page: int = 0
    total_pages: int = 0
    status: str = "pending"  # pending | processing | completed | failed
    result_path: str | None = None
    error: str | None = None

_ocr_jobs: dict[str, OcrJob] = {}


# ---------------------------------------------------------------------------
# Conversion tables
# ---------------------------------------------------------------------------
SUPPORTED_CONVERSIONS: dict[tuple[str, str], str] = {
    (".docx", "pdf"): "docx2pdf",
    (".docx", "md"): "docx2pdf + pymupdf4llm",
    (".pdf", "md"): "pymupdf4llm",
    (".pptx", "pdf"): "libreoffice",
    (".pptx", "md"): "libreoffice + pymupdf4llm",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client() -> MoodleClient:
    username = os.environ.get("MOODLE_USERNAME")
    password = os.environ.get("MOODLE_PASSWORD")

    token = get_token()
    if token and is_session_valid(token):
        return MoodleClient(token)

    if username and password:
        token = login(username, password)
        save_token(token)
        return MoodleClient(token)

    creds = get_credentials()
    if creds:
        token = login(creds[0], creds[1])
        save_token(token)
        return MoodleClient(token)

    raise RuntimeError(
        "No Moodle credentials found. Please set MOODLE_USERNAME and "
        "MOODLE_PASSWORD environment variables, or run 'aulasvirtuales login' locally via CLI."
    )


def _find_resource(client: MoodleClient, course_id: int, resource_id: int):
    """Locate a resource inside course sections."""
    sections = client.get_course_contents(course_id)
    for section in sections:
        for r in section.resources:
            if r.id == resource_id:
                return r, sections
    return None, sections


def _convert_file(path: Path, to_format: str, output_dir: Path) -> Path:
    """Convert a downloaded file to the requested format (native, no OCR)."""
    suffix = path.suffix.lower()
    if suffix == f".{to_format}":
        return path

    key = (suffix, to_format)
    if key not in SUPPORTED_CONVERSIONS:
        raise ValueError(f"Conversion from {suffix} to {to_format} is not supported.")

    # .pptx -> pdf (or chained to md)
    if suffix == ".pptx" and to_format in ("pdf", "md"):
        from aulasvirtuales.converter import pptx_to_pdf
        pdf_path = pptx_to_pdf(path, output_dir)
        if to_format == "pdf":
            return pdf_path
        path = pdf_path
        suffix = ".pdf"

    # .docx -> pdf (or chained to md)
    if suffix == ".docx" and to_format in ("pdf", "md"):
        from aulasvirtuales.converter import docx_to_pdf
        pdf_path = docx_to_pdf(path, output_dir)
        if to_format == "pdf":
            return pdf_path
        path = pdf_path
        suffix = ".pdf"

    # .pdf -> md
    if suffix == ".pdf" and to_format == "md":
        from aulasvirtuales.converter import convert_and_save
        return convert_and_save(path, output_dir)

    return path


def _resolve_ocr_config(
    ocr_provider: str | None,
    ocr_model: str | None,
) -> tuple[str, str, dict]:
    """Resolve OCR provider, model, and provider kwargs from args and config."""
    ocr_cfg = get_ocr_config()
    provider = ocr_provider or ocr_cfg.get("provider")
    model = ocr_model or ocr_cfg.get("model")
    if not provider or not model:
        raise ValueError(
            "OCR provider and model required. Set them via CLI with:\n"
            "  aulasvirtuales config --ocr-provider <provider> --ocr-model <model>\n"
            "Or pass ocr_provider and ocr_model parameters directly."
        )
    provider_kwargs = ocr_cfg.get(provider, {})
    return provider, model, provider_kwargs


def _ocr_convert_file(
    path: Path,
    output_format: str,
    output_dir: Path,
    provider: str,
    model: str,
    provider_kwargs: dict,
    on_page: Callable[[int, int], None] | None = None,
) -> Path:
    """Convert a file using OCR via a vision LLM."""
    from aulasvirtuales.ocr import OCR_SUPPORTED_EXTENSIONS, ocr_and_save

    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return path
    if suffix not in OCR_SUPPORTED_EXTENSIONS:
        raise ValueError(f"OCR not supported for {suffix} files.")

    return ocr_and_save(
        path, provider, model,
        provider_config=provider_kwargs,
        output_format=output_format,
        output_dir=output_dir,
        on_page=on_page,
    )


async def _run_ocr_job(
    job: OcrJob,
    path: Path,
    output_format: str,
    output_dir: Path,
    provider: str,
    model: str,
    provider_kwargs: dict,
) -> None:
    """Run OCR in a background thread and update the job registry."""
    job.status = "processing"

    def _on_page(current: int, total: int) -> None:
        job.current_page = current
        job.total_pages = total

    try:
        converted = await asyncio.to_thread(
            _ocr_convert_file, path, output_format, output_dir,
            provider, model, provider_kwargs, _on_page,
        )
        job.result_path = str(converted)
        job.status = "completed"
    except Exception as exc:
        job.error = str(exc)
        job.status = "failed"


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_courses():
    """List enrolled courses."""
    client = _get_client()
    return client.get_courses()

@mcp.tool()
def get_course_resources(course_id: int | str):
    """List sections and resources of a course."""
    client = _get_client()
    return client.get_course_contents(int(course_id))

@mcp.tool()
def get_upcoming_events(course_id: int | str | None = None):
    """Show upcoming events for a specific course or across all courses."""
    client = _get_client()
    return client.get_upcoming_events(int(course_id) if course_id is not None else None)

@mcp.tool()
def get_grades(course_id: int | str):
    """Show grades and feedback for a course."""
    client = _get_client()
    return client.get_grades(int(course_id))

@mcp.tool()
def get_forums(course_id: int | str):
    """List forums in a course."""
    client = _get_client()
    return client.get_forums(int(course_id))

@mcp.tool()
def get_forum_discussions(forum_id: int | str, limit: int | str = 10):
    """List discussions in a forum."""
    client = _get_client()
    return client.get_forum_discussions(int(forum_id), int(limit))

@mcp.tool()
def get_discussion_posts(discussion_id: int | str):
    """Show messages in a forum discussion."""
    client = _get_client()
    return client.get_discussion_posts(int(discussion_id))



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
            doc = fitz.open(str(file_path))
            pages = [page.get_text() for page in doc]
            doc.close()
            return [f"--- File: {file_path.name} ---\n" + "\n".join(pages)]
        else:
            return [f"--- File: {file_path.name} ---\n" + file_path.read_text(encoding="utf-8", errors="ignore")]
    except Exception as e:
        return [f"[Failed to read {file_path.name}: {e}]"]




@mcp.tool()
async def download(
    course_id: int | str,
    resource_id: int | str,
    output: str | None = None,
    to: str | None = None,
    file: str | None = None,
    ocr: bool | str = False,
    ocr_provider: str | None = None,
    ocr_model: str | None = None,
) -> str:
    """Download a resource (file or folder) from a course with optional conversion and OCR.

    This is the full-featured download tool, equivalent to the CLI's `aulasvirtuales download` command.

    Args:
        course_id: The Moodle course ID.
        resource_id: The resource ID (must be a File or Folder type).
        output: Destination directory or file path. Defaults to the configured download directory (~\/aulasvirtuales).
        to: Convert after download. Supported conversions: .docx->pdf, .docx->md, .pdf->md, .pptx->pdf, .pptx->md. Use "md" or "txt" with OCR.
        file: Download only files whose name contains this substring (case-insensitive). Useful for folders with many files.
        ocr: If true, use a vision LLM for OCR-based conversion instead of native parsing. Requires ocr_provider and ocr_model to be set (via params or CLI config). Defaults the output format to "md" if `to` is not specified.
        ocr_provider: OCR provider override (e.g. "ollama", "openrouter"). Falls back to CLI-configured value.
        ocr_model: OCR model name override (e.g. "llava", "google/gemini-2.0-flash-001"). Falls back to CLI-configured value.

    Returns:
        A summary of downloaded (and optionally converted) file paths.
        When OCR is requested, the conversion runs in the background and the tool
        returns immediately with a job ID. Use `ocr_status` to check progress.
    """
    course_id, resource_id = int(course_id), int(resource_id)
    ocr = ocr if isinstance(ocr, bool) else str(ocr).lower() in ("true", "1", "yes")

    # --- Validate OCR args early ---
    provider = model = ""
    provider_kwargs: dict = {}
    if ocr:
        if not to:
            to = "md"
        if to not in ("md", "txt"):
            raise ValueError("OCR only supports 'md' or 'txt' as output format.")
        provider, model, provider_kwargs = _resolve_ocr_config(ocr_provider, ocr_model)

    # --- Resolve destination ---
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

    # --- Find resource ---
    client = _get_client()
    resource, _ = _find_resource(client, course_id, resource_id)

    if not resource:
        raise ValueError(f"Resource {resource_id} not found in course {course_id}.")

    if resource.module not in ("resource", "folder"):
        raise ValueError(f"Resource type '{resource.module}' is not downloadable.")

    file_urls = get_resource_files(client._http, resource.id, resource.module)
    if not file_urls:
        raise ValueError("No downloadable files found.")

    # --- Filter by filename substring ---
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

    # --- Download & convert ---
    results: list[str] = []

    for url in file_urls:
        path = download_file(client._http, url, dest_dir, filename=dest_filename)
        results.append(f"✓ Downloaded: {path}")

        if ocr and to:
            job = OcrJob(id=uuid.uuid4().hex[:8], filename=path.name)
            _ocr_jobs[job.id] = job

            asyncio.create_task(
                _run_ocr_job(job, path, to, dest_dir, provider, model, provider_kwargs)
            )

            results.append(
                f"  ⏳ OCR started in background (job_id: {job.id}). "
                f"Use ocr_status(job_id=\"{job.id}\") to check progress."
            )
        elif to:
            converted = _convert_file(path, to, dest_dir)
            results.append(f"  ✓ Converted: {converted}")

    return "\n".join(results)


@mcp.tool()
def ocr_status(job_id: str | None = None) -> str:
    """Check the status of a background OCR job.

    Call without arguments to list all jobs, or pass a specific job_id
    returned by the download tool.

    Args:
        job_id: The OCR job ID to check. If omitted, lists all jobs.

    Returns:
        Current status of the OCR job(s): processing page X/Y, completed
        with the output file path, or error details.
    """
    if job_id is None:
        if not _ocr_jobs:
            return "No OCR jobs found."
        lines = []
        for job in _ocr_jobs.values():
            lines.append(_format_job_status(job))
        return "\n".join(lines)

    job = _ocr_jobs.get(job_id)
    if not job:
        return f"OCR job '{job_id}' not found."
    return _format_job_status(job)


def _format_job_status(job: OcrJob) -> str:
    """Format a single OCR job status as a human-readable string."""
    if job.status == "pending":
        return f"[{job.id}] {job.filename}: pending"
    if job.status == "processing":
        if job.total_pages > 0:
            return f"[{job.id}] {job.filename}: processing page {job.current_page}/{job.total_pages}"
        return f"[{job.id}] {job.filename}: processing..."
    if job.status == "completed":
        return f"[{job.id}] {job.filename}: ✓ completed → {job.result_path}"
    if job.status == "failed":
        return f"[{job.id}] {job.filename}: ✗ failed — {job.error}"
    return f"[{job.id}] {job.filename}: {job.status}"


@mcp.tool()
def clear_downloads(force: bool | str = False) -> str:
    """Clear all downloaded files from the configured download directory.

    Use this after completing download tasks to free disk space.

    Args:
        force: If true, skip confirmation and delete immediately. Default is false.

    Returns:
        A message indicating success or that the directory was already empty.
    """
    import shutil

    force = force if isinstance(force, bool) else str(force).lower() in ("true", "1", "yes")

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

def main():
    mcp.run()

if __name__ == "__main__":
    main()
