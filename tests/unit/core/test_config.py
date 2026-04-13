"""Unit tests for aulasvirtuales.config — configuration management."""

import json
from pathlib import Path

import pytest

from aulasvirtuales.config import (
    get_download_dir,
    get_ocr_config,
    load_config,
    save_config,
    set_download_dir,
    set_ocr_model,
    set_ocr_provider,
    set_ocr_provider_kwarg,
)


@pytest.mark.unit
class TestLoadSaveConfig:
    def test_load_config_empty(self, tmp_config_dir):
        """Returns empty dict when no config file exists."""
        result = load_config()
        assert result == {}

    def test_save_and_load_config(self, tmp_config_dir):
        """Config is persisted and reloaded correctly."""
        config = {"key": "value", "nested": {"a": 1}}
        save_config(config)

        result = load_config()

        assert result == config
        assert (tmp_config_dir / "config.json").exists()


@pytest.mark.unit
class TestDownloadDir:
    def test_get_download_dir_default(self, tmp_config_dir, tmp_download_dir):
        """Returns default download directory when not configured."""
        result = get_download_dir()
        assert result == tmp_download_dir

    def test_set_download_dir(self, tmp_config_dir, tmp_path):
        """Download directory is updated in config."""
        custom_dir = tmp_path / "custom_downloads"

        set_download_dir(custom_dir)
        result = get_download_dir()

        assert result == custom_dir.resolve()


@pytest.mark.unit
class TestOcrConfig:
    def test_get_ocr_config_empty(self, tmp_config_dir):
        """Returns empty dict when no OCR config exists."""
        result = get_ocr_config()
        assert result == {}

    def test_set_ocr_provider(self, tmp_config_dir):
        """OCR provider is saved to config."""
        set_ocr_provider("ollama")

        result = get_ocr_config()
        assert result["provider"] == "ollama"

    def test_set_ocr_model(self, tmp_config_dir):
        """OCR model is saved to config."""
        set_ocr_model("llava")

        result = get_ocr_config()
        assert result["model"] == "llava"

    def test_set_ocr_provider_kwarg(self, tmp_config_dir):
        """Provider-specific kwargs are saved under the provider key."""
        set_ocr_provider_kwarg("openrouter", "api_key", "sk-test123")

        result = get_ocr_config()
        assert result["openrouter"]["api_key"] == "sk-test123"

    def test_multiple_ocr_settings(self, tmp_config_dir):
        """Multiple OCR settings are preserved together."""
        set_ocr_provider("openrouter")
        set_ocr_model("gemini-flash")
        set_ocr_provider_kwarg("openrouter", "api_key", "sk-test")

        result = get_ocr_config()
        assert result["provider"] == "openrouter"
        assert result["model"] == "gemini-flash"
        assert result["openrouter"]["api_key"] == "sk-test"
