from pathlib import Path

import typer

from aulasvirtuales.config import (
    get_download_dir,
    get_ocr_config,
    set_download_dir,
    set_ocr_model,
    set_ocr_provider,
    set_ocr_provider_kwarg,
)
from aulasvirtuales_cli.app import app, console, is_repl_context


@app.command()
def config(
    download_dir: Path = typer.Option(None, "--download-dir", "-d", help="Set default download directory"),
    ocr_provider: str = typer.Option(None, "--ocr-provider", help="Set OCR provider (ollama, openrouter)"),
    ocr_model: str = typer.Option(None, "--ocr-model", help="Set OCR model name"),
    openrouter_api_key: str = typer.Option(None, "--openrouter-api-key", help="Set OpenRouter API key"),
    ollama_base_url: str = typer.Option(None, "--ollama-base-url", help="Set Ollama base URL"),
    ui: bool = typer.Option(False, "--ui", help="Launch the interactive Textual configuration screen"),
) -> None:
    """View or update CLI configuration."""
    no_flags = all(
        v is None
        for v in (download_dir, ocr_provider, ocr_model, openrouter_api_key, ollama_base_url)
    )

    if ui or (is_repl_context() and no_flags):
        from aulasvirtuales_cli.tui.config_screen import ConfigApp

        ConfigApp().run()
        return

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
