from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Select

from aulasvirtuales.config import (
    get_download_dir,
    get_ocr_config,
    set_download_dir,
    set_ocr_model,
    set_ocr_provider,
    set_ocr_provider_kwarg,
)

PROVIDER_OPTIONS = [("Ollama (local)", "ollama"), ("OpenRouter (cloud)", "openrouter")]


class ConfigApp(App):
    """Textual form to edit persistent CLI configuration."""

    CSS = """
    Screen {
        align: center middle;
    }

    #form {
        width: 70;
        height: auto;
        padding: 1 2;
        border: round $accent;
    }

    .field-label {
        padding-top: 1;
        color: $text-muted;
    }

    #buttons {
        height: auto;
        align-horizontal: right;
        padding-top: 1;
    }

    Button {
        margin-left: 2;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        ocr_cfg = get_ocr_config()
        provider = ocr_cfg.get("provider") or ""
        model = ocr_cfg.get("model") or ""
        openrouter_key = ocr_cfg.get("openrouter", {}).get("api_key") or ""
        ollama_url = ocr_cfg.get("ollama", {}).get("base_url") or ""

        yield Header(show_clock=False)
        with Vertical(id="form"):
            yield Label("[b]aulasvirtuales config[/b]")

            yield Label("Download directory", classes="field-label")
            yield Input(value=str(get_download_dir()), id="download_dir")

            yield Label("OCR provider", classes="field-label")
            yield Select(
                PROVIDER_OPTIONS,
                value=provider if provider in ("ollama", "openrouter") else Select.BLANK,
                id="ocr_provider",
            )

            yield Label("OCR model", classes="field-label")
            yield Input(value=model, placeholder="e.g. google/gemini-flash-1.5", id="ocr_model")

            yield Label("OpenRouter API key", classes="field-label")
            yield Input(value=openrouter_key, password=True, id="openrouter_api_key")

            yield Label("Ollama base URL", classes="field-label")
            yield Input(value=ollama_url, placeholder="http://localhost:11434", id="ollama_base_url")

            with Horizontal(id="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", id="save", variant="primary")
        yield Footer()

    def action_cancel(self) -> None:
        self.exit(result=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.exit(result=False)
            return
        if event.button.id == "save":
            self._save()
            self.exit(result=True)

    def _save(self) -> None:
        download_dir = self.query_one("#download_dir", Input).value.strip()
        if download_dir:
            set_download_dir(Path(download_dir))

        provider_value = self.query_one("#ocr_provider", Select).value
        if provider_value and provider_value is not Select.BLANK:
            set_ocr_provider(provider_value)

        ocr_model = self.query_one("#ocr_model", Input).value.strip()
        if ocr_model:
            set_ocr_model(ocr_model)

        openrouter_key = self.query_one("#openrouter_api_key", Input).value.strip()
        if openrouter_key:
            set_ocr_provider_kwarg("openrouter", "api_key", openrouter_key)

        ollama_url = self.query_one("#ollama_base_url", Input).value.strip()
        if ollama_url:
            set_ocr_provider_kwarg("ollama", "base_url", ollama_url)
