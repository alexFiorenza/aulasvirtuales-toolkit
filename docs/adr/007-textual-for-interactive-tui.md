# ADR 007: Textual for Interactive TUI Screens

## Status

Accepted

## Date

2026-04-16

## Context

The CLI had been flag-only for configuration (`aulasvirtuales config --ocr-model …`) and "all or nothing" for folder downloads (a folder resource downloaded every file inside). Both UX decisions work well for automation and AI agents, but make direct human use in the REPL verbose and inflexible.

We wanted two interactive screens, available only to human users:

1. **Configuration screen** — edit download directory, OCR provider, OCR model, OpenRouter API key, and Ollama base URL through a form.
2. **Folder file selector** — pick which files to download from a Moodle folder resource using checkboxes.

We evaluated the following approaches:

1. **`questionary`** — Simple line-based prompts built on `prompt-toolkit`. Minimal API (`questionary.checkbox(...)`, `questionary.text(...)`).
2. **`prompt-toolkit` full-screen application** — We already depend on `prompt-toolkit` for the REPL. Its full-screen API can build arbitrary TUIs but requires manual layout, key bindings, and buffer management.
3. **`Textual`** — Full TUI framework from the Textualize team, built on top of `rich` (which we already use). Ships with widgets like `Input`, `Select`, `SelectionList`, and `Button`.

## Decision

We chose **Textual** as the TUI framework for `aulasvirtuales-cli`.

Textual is added only to `apps/aulasvirtuales-cli/pyproject.toml`. The core library (`packages/core`) and the MCP server (`apps/aulasvirtuales-mcp`) remain UI-agnostic — they depend only on `rich` and `httpx` respectively.

Textual applications live under `apps/aulasvirtuales-cli/src/aulasvirtuales_cli/tui/`:

```python
# tui/config_screen.py
from textual.app import App
from textual.widgets import Input, Select, Button

class ConfigApp(App):
    def compose(self): ...  # pre-populated form widgets
    def on_button_pressed(self, event): ...  # Save -> config setters
```

Each Textual app is launched synchronously with `App().run()`, which takes over the terminal, and returns cleanly so the REPL prompt (`prompt-toolkit`) can resume.

## Consequences

### Positive

- **Rich widget set out of the box**: `Input(password=True)`, `Select`, `SelectionList` (checkboxes), and `Button` cover every interaction we need without custom rendering.
- **Clean integration with the REPL**: `App.run()` is blocking and returns after the user dismisses the screen, so the `prompt-toolkit` session picks up on the next iteration without artifacts.
- **Consistent with `rich`**: Textual shares styling primitives with `rich`, which we already use throughout the CLI, so the visual language stays coherent.
- **Good separation of concerns**: Business logic lives in `packages/core` (config setters, downloader); Textual screens are thin wrappers that call those setters on Save.

### Negative

- **Heavy transitive dependencies**: Textual brings in a sizeable dependency tree (~15 MB resolved). It is justified for interactive users but irrelevant for the MCP server, which is why we kept Textual out of `packages/core` and `apps/aulasvirtuales-mcp`.
- **Terminal takeover**: While a Textual app is running, the REPL's prompt is gone. We mitigate this by scoping Textual strictly to REPL invocations (see ADR 008).
- **New paradigm**: Developers working on CLI screens need to learn Textual's reactive/compose model, which differs from `rich`'s imperative API.

### Alternatives Considered

- **`questionary`**: Simpler and lighter, but its line-based prompts do not provide the form-like experience we wanted for configuration. It would also require adding yet another `prompt-toolkit`-derived library rather than a self-contained framework.
- **`prompt-toolkit` full-screen**: Zero new dependencies, but the amount of boilerplate for a small form (layouts, key bindings, buffer routing) was high enough to offset the "same library" benefit. Textual essentially is the library we would otherwise have written.

### Neutral

- Textual is only loaded lazily (inside the command handler that needs it), so users running one-shot commands do not pay the import cost.
- If Textual ever becomes a problem (breaking changes, maintenance), replacing both screens with `questionary` or hand-rolled `prompt-toolkit` apps is localized to `tui/config_screen.py` and `tui/file_selector.py`.
