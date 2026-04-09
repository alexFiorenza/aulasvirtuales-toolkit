# Contributing

Thanks for your interest in contributing to **aulasvirtuales-cli**!

## Getting started

1. Fork and clone the repository
2. Create a virtual environment and install dependencies:

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras
playwright install chromium
```

3. Install pre-commit hooks:

```bash
pre-commit install
```

## Development workflow

1. Create a branch from `master` for your changes
2. Make your changes following the conventions below
3. Run tests before committing:

```bash
pytest
```

4. Commit using [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat(scope): add new feature
fix(scope): fix something broken
docs: update documentation
```

5. Open a pull request against `master`

## Code conventions

- **Python 3.11+**
- `snake_case` for functions and variables, `PascalCase` for classes
- Type hints on all function signatures
- Google-style docstrings where needed
- Imports organized with `isort` (stdlib, third-party, local)
- Tests with `pytest` in the `tests/` directory

## Reporting issues

Open an issue describing the bug or feature request. Include steps to reproduce for bugs.
