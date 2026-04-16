import asyncio
import base64
import importlib
from collections.abc import Awaitable, Callable
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"}

OCR_SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf", ".docx", ".pptx"}

PROVIDERS: dict[str, tuple[str, str]] = {
    "ollama": ("langchain_ollama", "ChatOllama"),
    "openrouter": ("langchain_openrouter", "ChatOpenRouter"),
}

_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".webp": "image/webp",
}

_PROMPT_MD = (
    "You are an OCR assistant. Extract ALL text from this image and format it "
    "as clean Markdown. Preserve headings, lists, tables, and emphasis. "
    "Output ONLY the extracted content, no commentary."
)

_PROMPT_TXT = (
    "You are an OCR assistant. Extract ALL text from this image as plain text. "
    "Preserve paragraph breaks and structure. "
    "Output ONLY the extracted content, no commentary."
)


def _get_llm(provider: str, model: str, **kwargs) -> BaseChatModel:
    """Instantiate a LangChain chat model for the given provider."""
    if provider not in PROVIDERS:
        available = ", ".join(PROVIDERS)
        raise ValueError(f"Unknown provider: {provider}. Available: {available}")
    module_name, class_name = PROVIDERS[provider]
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls(model=model, **kwargs)


def _ocr_image(image_bytes: bytes, llm: BaseChatModel, mime_type: str, prompt: str) -> str:
    """Send a single image to the vision model and return extracted text."""
    b64 = base64.b64encode(image_bytes).decode()
    message = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
    ])
    return llm.invoke([message]).content


def _pdf_to_images(pdf_path: Path) -> list[bytes]:
    """Render each page of a PDF as a PNG image."""
    import fitz

    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(str(pdf_path))
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def _render_pdf_pages(pdf_path: Path, pages_1indexed: list[int]) -> dict[int, bytes]:
    """Render a specific subset of 1-indexed PDF pages as PNG images."""
    import fitz

    fitz.TOOLS.mupdf_display_errors(False)
    doc = fitz.open(str(pdf_path))
    out: dict[int, bytes] = {}
    try:
        for p in pages_1indexed:
            pix = doc[p - 1].get_pixmap(dpi=150)
            out[p] = pix.tobytes("png")
    finally:
        doc.close()
    return out


class OcrGateRefusalError(RuntimeError):
    """Raised when the classifier gate refuses an OCR run on a text-based PDF."""

    def __init__(self, pdf_path: Path, confidence: float | None = None):
        self.pdf_path = pdf_path
        self.confidence = confidence
        msg = (
            f"'{pdf_path.name}' is a text-based PDF — native conversion (--to md) is faster and "
            "produces equivalent markdown. Pass --force-ocr (CLI) or force_ocr=true (MCP) to "
            "override."
        )
        super().__init__(msg)


def _ensure_pdf(file_path: Path) -> tuple[Path, bool]:
    """Convert to PDF if needed. Returns (pdf_path, needs_cleanup)."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return file_path, False
    if suffix == ".docx":
        from aulasvirtuales.converter import docx_to_pdf

        return docx_to_pdf(file_path), True
    if suffix == ".pptx":
        from aulasvirtuales.converter import pptx_to_pdf

        return pptx_to_pdf(file_path), True
    raise ValueError(f"OCR not supported for {suffix} files.")


async def ocr_and_save(
    file_path: Path,
    provider: str,
    model: str,
    provider_config: dict | None = None,
    output_format: str = "md",
    output_dir: Path | None = None,
    on_page: Callable[[int, int], Awaitable[None]] | None = None,
    on_status: Callable[[str], Awaitable[None]] | None = None,
    force: bool = False,
) -> Path:
    """Convert a file to markdown or plain text using OCR via a vision LLM.

    On PDFs, runs the pdf-inspector classifier gate first:
    - text_based  → raises OcrGateRefusalError unless force=True
    - mixed       → hybrid: native extraction for clean pages, vision OCR for pages_needing_ocr
    - scanned/image_based/unknown → full vision pipeline (render every page to image)
    - gate unavailable (pdf-inspector not installed) → full vision pipeline with a warning status
    """
    llm = _get_llm(provider, model, **(provider_config or {}))
    prompt = _PROMPT_MD if output_format == "md" else _PROMPT_TXT
    suffix = file_path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        mime = _MIME_TYPES.get(suffix, "image/png")
        if on_page:
            await on_page(1, 1)
        content = await asyncio.to_thread(
            _ocr_image, file_path.read_bytes(), llm, mime, prompt
        )
    else:
        if on_status and suffix != ".pdf":
            await on_status(f"Converting {file_path.name} to PDF")
        pdf_path, cleanup = _ensure_pdf(file_path)

        try:
            from aulasvirtuales.converter import classify_pdf

            verdict = classify_pdf(pdf_path)
        except Exception:
            verdict = None

        pdf_type = getattr(verdict, "pdf_type", None) if verdict else None

        if pdf_type == "text_based" and not force:
            if cleanup:
                pdf_path.unlink(missing_ok=True)
            raise OcrGateRefusalError(file_path, getattr(verdict, "confidence", None))

        if verdict is None and on_status:
            await on_status(
                "Classifier gate unavailable (pdf-inspector not installed) — running full vision pipeline"
            )

        if pdf_type == "mixed" and not force:
            content = await _ocr_hybrid(
                pdf_path,
                file_path.name,
                verdict,
                llm,
                prompt,
                on_page,
                on_status,
            )
        else:
            if on_status:
                await on_status(f"Rendering {file_path.name} pages")
            images = _pdf_to_images(pdf_path)
            parts = []
            for i, img in enumerate(images):
                page_num = i + 1
                total = len(images)
                if on_page:
                    await on_page(page_num, total)
                if on_status:
                    await on_status(f"OCR {file_path.name} — page {page_num}/{total}")
                try:
                    parts.append(
                        await asyncio.to_thread(_ocr_image, img, llm, "image/png", prompt)
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"OCR failed on page {page_num}/{total}: {exc}"
                    ) from exc
            content = "\n\n---\n\n".join(parts)

        if cleanup:
            pdf_path.unlink(missing_ok=True)

    out_dir = output_dir or file_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = ".md" if output_format == "md" else ".txt"
    out_path = out_dir / f"{file_path.stem}{ext}"
    out_path.write_text(content, encoding="utf-8")
    return out_path


async def _ocr_hybrid(
    pdf_path: Path,
    display_name: str,
    verdict,
    llm: BaseChatModel,
    prompt: str,
    on_page: Callable[[int, int], Awaitable[None]] | None,
    on_status: Callable[[str], Awaitable[None]] | None,
) -> str:
    """Hybrid pipeline for mixed PDFs — native extraction for text pages, vision OCR for scanned pages.

    Page indices are assumed 1-based.
    """
    import pdf_inspector

    page_count = int(getattr(verdict, "page_count", 0) or 0)
    pages_needing_ocr = list(getattr(verdict, "pages_needing_ocr", []) or [])
    ocr_set = set(pages_needing_ocr)

    if page_count <= 0:
        # Fall back to full vision if we can't plan
        images = _pdf_to_images(pdf_path)
        parts = []
        for i, img in enumerate(images):
            parts.append(await asyncio.to_thread(_ocr_image, img, llm, "image/png", prompt))
        return "\n\n---\n\n".join(parts)

    if on_status:
        await on_status(
            f"Hybrid OCR {display_name} — {len(ocr_set)}/{page_count} pages need vision"
        )

    rendered = await asyncio.to_thread(_render_pdf_pages, pdf_path, sorted(ocr_set))

    parts: list[str] = []
    for page in range(1, page_count + 1):
        if on_page:
            await on_page(page, page_count)
        if page in ocr_set:
            if on_status:
                await on_status(f"OCR {display_name} — page {page}/{page_count} (vision)")
            try:
                parts.append(
                    await asyncio.to_thread(
                        _ocr_image, rendered[page], llm, "image/png", prompt
                    )
                )
            except Exception as exc:
                raise RuntimeError(f"OCR failed on page {page}/{page_count}: {exc}") from exc
        else:
            if on_status:
                await on_status(f"Native {display_name} — page {page}/{page_count}")
            def _extract_page(path=str(pdf_path), p=page):
                return pdf_inspector.process_pdf(path, pages=[p])

            result = await asyncio.to_thread(_extract_page)
            parts.append(getattr(result, "markdown", "") or "")

    return "\n\n---\n\n".join(parts)
