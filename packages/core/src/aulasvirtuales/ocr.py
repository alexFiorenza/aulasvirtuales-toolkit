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
) -> Path:
    """Convert a file to markdown or plain text using OCR via a vision LLM."""
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
        pdf_path, cleanup = _ensure_pdf(file_path)
        images = _pdf_to_images(pdf_path)
        if cleanup:
            pdf_path.unlink(missing_ok=True)

        parts = []
        for i, img in enumerate(images):
            if on_page:
                await on_page(i + 1, len(images))
            parts.append(
                await asyncio.to_thread(_ocr_image, img, llm, "image/png", prompt)
            )
        content = "\n\n---\n\n".join(parts)

    out_dir = output_dir or file_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = ".md" if output_format == "md" else ".txt"
    out_path = out_dir / f"{file_path.stem}{ext}"
    out_path.write_text(content, encoding="utf-8")
    return out_path
