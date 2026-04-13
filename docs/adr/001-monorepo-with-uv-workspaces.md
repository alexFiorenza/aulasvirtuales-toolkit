# ADR 001: Monorepo with uv Workspaces

## Status

Accepted

## Date

2024-12-01

## Context

The aulasvirtuales-toolkit consists of three distinct packages:

1. **aulasvirtuales-core** — Shared library with Moodle client, auth, config, conversion, downloading, and OCR logic.
2. **aulasvirtuales-cli** — CLI application built with Typer.
3. **aulasvirtuales-mcp** — MCP server built with FastMCP.

Both applications depend on the core library. We needed to decide between:

- **Separate repositories** for each package.
- **Monorepo** with all packages in a single repository.

## Decision

We chose a **monorepo structure** using **uv workspaces** with the following layout:

```
packages/core/         → aulasvirtuales-core
apps/aulasvirtuales-cli/  → aulasvirtuales-cli
apps/aulasvirtuales-mcp/  → aulasvirtuales-mcp
```

The root `pyproject.toml` defines workspace members:

```toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]
```

## Consequences

### Positive

- **Atomic changes**: Changes to the core library and its consumers can be made in a single commit and PR.
- **Shared dev environment**: One `uv sync` installs all dependencies for all packages.
- **Consistent versioning**: Release-please manages changelogs and versions across all packages from one config.
- **Simplified CI**: A single GitHub Actions workflow can test all packages.
- **No publishing overhead**: No need to publish internal packages to PyPI for inter-package dependencies.

### Negative

- **Coupled releases**: A change to only the CLI still touches the same repo as the MCP server.
- **Larger clone size**: Contributors who only care about one package still clone everything.
- **uv-specific**: The workspace feature ties us to `uv` as the package manager (though the individual packages remain pip-compatible).

### Neutral

- Each package maintains its own `pyproject.toml` with independent versions and dependencies.
- The `packages/` vs `apps/` convention clearly separates libraries from applications.
