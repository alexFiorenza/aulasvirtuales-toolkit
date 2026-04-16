import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastmcp import FastMCP

from aulasvirtuales.auth import get_credentials, get_token, is_session_valid, login, save_token
from aulasvirtuales.client import MoodleClient
from aulasvirtuales.config import get_ocr_config

mcp = FastMCP("AulasVirtuales")


SUPPORTED_CONVERSIONS: dict[tuple[str, str], str] = {
    (".docx", "pdf"): "libreoffice",
    (".docx", "md"): "mammoth",
    (".pdf", "md"): "pdf-inspector",
    (".pptx", "pdf"): "libreoffice",
    (".pptx", "md"): "libreoffice + pdf-inspector",
}


def get_client() -> MoodleClient:
    """Return an authenticated MoodleClient, refreshing the token if needed."""
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


def convert_file(path: Path, to_format: str, output_dir: Path) -> Path:
    """Convert a downloaded file to the requested format (native, no OCR)."""
    suffix = path.suffix.lower()
    if suffix == f".{to_format}":
        return path

    key = (suffix, to_format)
    if key not in SUPPORTED_CONVERSIONS:
        raise ValueError(f"Conversion from {suffix} to {to_format} is not supported.")

    from aulasvirtuales.converter import convert
    return convert(path, to_format, output_dir)


def resolve_ocr_config(
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


async def ocr_convert_file(
    path: Path,
    output_format: str,
    output_dir: Path,
    provider: str,
    model: str,
    provider_kwargs: dict,
    on_page: Callable[[int, int], Awaitable[None]] | None = None,
    force: bool = False,
) -> Path:
    """Convert a file using OCR via a vision LLM."""
    from aulasvirtuales.ocr import OCR_SUPPORTED_EXTENSIONS, ocr_and_save

    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return path
    if suffix not in OCR_SUPPORTED_EXTENSIONS:
        raise ValueError(f"OCR not supported for {suffix} files.")

    return await ocr_and_save(
        path, provider, model,
        provider_config=provider_kwargs,
        output_format=output_format,
        output_dir=output_dir,
        on_page=on_page,
        force=force,
    )


def main() -> None:
    mcp.run()


# Register tool modules — each module adds its @mcp.tool() on import
import aulasvirtuales_mcp.tools.courses  # noqa: F401, E402
import aulasvirtuales_mcp.tools.events  # noqa: F401, E402
import aulasvirtuales_mcp.tools.grades  # noqa: F401, E402
import aulasvirtuales_mcp.tools.forums  # noqa: F401, E402
import aulasvirtuales_mcp.tools.downloads  # noqa: F401, E402
