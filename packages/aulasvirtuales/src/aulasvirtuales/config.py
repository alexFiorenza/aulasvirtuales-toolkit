import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "aulasvirtuales"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_DOWNLOAD_DIR = Path.home() / "aulasvirtuales"


def load_config() -> dict:
    """Load configuration from disk, returning defaults if none exists."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config(config: dict) -> None:
    """Persist configuration to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_download_dir() -> Path:
    """Return the configured download directory, falling back to the default."""
    config = load_config()
    return Path(config.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)))


def set_download_dir(path: Path) -> None:
    """Update the configured download directory."""
    config = load_config()
    config["download_dir"] = str(path.expanduser().resolve())
    save_config(config)


def get_ocr_config() -> dict:
    """Return OCR configuration (provider, model, and per-provider kwargs)."""
    config = load_config()
    return config.get("ocr", {})


def set_ocr_provider(provider: str) -> None:
    """Set the OCR provider name."""
    config = load_config()
    ocr = config.setdefault("ocr", {})
    ocr["provider"] = provider
    save_config(config)


def set_ocr_model(model: str) -> None:
    """Set the OCR model name."""
    config = load_config()
    ocr = config.setdefault("ocr", {})
    ocr["model"] = model
    save_config(config)


def set_ocr_provider_kwarg(provider: str, key: str, value: str) -> None:
    """Set a configuration kwarg for a specific OCR provider."""
    config = load_config()
    ocr = config.setdefault("ocr", {})
    provider_cfg = ocr.setdefault(provider, {})
    provider_cfg[key] = value
    save_config(config)
