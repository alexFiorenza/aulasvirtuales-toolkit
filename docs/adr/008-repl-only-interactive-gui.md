# ADR 008: REPL-Only Interactive GUI Screens

## Status

Accepted

## Date

2026-04-16

## Context

ADR 007 introduced Textual as the framework for interactive screens (configuration form, folder file selector). A Textual app takes over the entire terminal: it repaints the screen, captures key strokes, and only returns to the caller when the user dismisses it.

This is incompatible with how AI agents use the CLI. The MCP server and tools like Claude Code invoke `aulasvirtuales` as a subprocess and parse stdout/stderr. They have a TTY but no way to send mouse or keyboard events to a full-screen application. If a Textual screen were to auto-launch on those invocations, the agent would hang forever.

At the same time, we want the interactive screens to appear **automatically** for human users — requiring an explicit `--ui` flag every time defeats the purpose of making configuration more ergonomic.

We evaluated the following approaches:

1. **Detect a TTY** — `sys.stdin.isatty() and sys.stdout.isatty()`. Straightforward, but many agent runners (including Claude Code) do allocate a TTY for the subprocess, so the check returns `True` and we hang anyway.
2. **Require an explicit `--ui` / `--select` flag** — Reliable, but loses the ergonomic win for humans who now have to remember two different invocations.
3. **Mark the REPL context explicitly** — The REPL (`start_repl`) is the one environment where we have a guaranteed human sitting at the keyboard. If we can detect "we are running inside the REPL loop", we can auto-launch Textual there and default to non-interactive behavior everywhere else.

## Decision

The REPL marks its context by setting an environment variable and unsetting it on exit:

```python
# repl.py
def start_repl(app):
    os.environ["AULASVIRTUALES_REPL"] = "1"
    try:
        ...  # prompt loop
    finally:
        os.environ.pop("AULASVIRTUALES_REPL", None)
```

Commands consult the helper `is_repl_context()` (in `app.py`) to decide whether to launch a Textual screen. Two override flags are available:

| Flag | Purpose |
|------|---------|
| `config --ui` | Force the config Textual screen outside the REPL (e.g., from a plain terminal). |
| `download --select` | Force the folder file selector outside the REPL. |
| `download --all` | Skip the folder file selector inside the REPL. |

### Decision matrix

| Context | Command | Behavior |
|---|---|---|
| REPL, no flags | `config` | Textual form |
| REPL, with a flag | `config --ocr-model foo` | Flag-driven, no GUI |
| Outside REPL, no flags | `aulasvirtuales config` | Print current values (agent-friendly) |
| Outside REPL, `--ui` | `aulasvirtuales config --ui` | Textual form |
| REPL, folder, no flags | `download 101 42` | File selector |
| REPL, folder, `--all` | `download 101 42 --all` | Download everything |
| Outside REPL, folder | `aulasvirtuales download 101 42` | Download everything (as today) |
| Outside REPL, folder, `--select` | `aulasvirtuales download 101 42 --select` | File selector |

## Consequences

### Positive

- **Agents are unaffected**: they do not enter the REPL, so the env var is never set, so Textual never launches automatically. The existing MCP server and any `aulasvirtuales <cmd>` invocation from a subprocess keep working exactly as before.
- **Humans get ergonomic defaults in the REPL**: typing `config` or `download <folder>` just does the right thing.
- **Opt-outs and opt-ins are symmetric**: `--all` and `--ui` / `--select` cover both directions cleanly.
- **Single-line signal**: the env var is trivial to set, trivial to check, and survives across the inner `click_app(args, standalone_mode=False)` invocations that the REPL uses for each command.

### Negative

- **Global state**: an environment variable is process-global. A spawned subprocess inherits it. If someone launches a second `aulasvirtuales` CLI invocation from inside the REPL (e.g. via `subprocess.run`), that child would also auto-launch Textual on a bare `config` call. We accept this edge case because (a) users rarely nest CLI invocations like that, and (b) the child command will still respect explicit flags.
- **Silent coupling**: the config and download commands implicitly depend on the REPL setting the env var. Misconfiguration would mean Textual never fires. Mitigated by end-to-end tests that exercise the REPL path.

### Alternatives Considered

- **TTY detection**: rejected because AI agent runners typically allocate a TTY.
- **Always require a flag**: rejected because it loses the primary UX motivation.
- **Click/Typer context propagation**: Typer creates a fresh context per invocation when the REPL dispatches with `click_app(args, standalone_mode=False)`, so `ctx.obj` does not persist across REPL commands. An env var is the simplest shared state.

### Neutral

- The env var name is namespaced (`AULASVIRTUALES_REPL`) to avoid collisions.
- If we ever need finer-grained signals (e.g. "called from the Homebrew helper"), we can layer more env vars with the same pattern.
