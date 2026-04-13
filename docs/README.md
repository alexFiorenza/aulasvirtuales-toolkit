# aulasvirtuales-toolkit Documentation

Welcome to the documentation for **aulasvirtuales-toolkit** — a toolkit to interact with [UTN FRBA's Moodle virtual classrooms](https://aulasvirtuales.frba.utn.edu.ar).

## Contents

### Product

- [Product Requirements Document (PRD)](prd/product_requirements.md) — Vision, goals, features, and roadmap.

### Architecture

- [Technical Blueprint](architecture/technical_blueprint.md) — System architecture, data flows, and technical decisions.
- [Class Diagram](architecture/class_diagram.mmd) — Class hierarchy and relationships (Mermaid).
- [Package Diagram](architecture/package_diagram.mmd) — Package dependencies and module organization (Mermaid).

### Architecture Decision Records (ADRs)

| # | Decision | Status |
|---|---|---|
| [001](adr/001-monorepo-with-uv-workspaces.md) | Monorepo with uv workspaces | Accepted |
| [002](adr/002-playwright-for-sso-auth.md) | Playwright for SSO authentication | Accepted |
| [003](adr/003-keyring-for-credential-storage.md) | Keyring for credential storage | Accepted |
| [004](adr/004-html-scraping-vs-moodle-api.md) | HTML scraping vs Moodle Web Services API | Accepted |
| [005](adr/005-langchain-for-ocr-pipeline.md) | LangChain for the OCR pipeline | Accepted |
| [006](adr/006-fastmcp-as-mcp-framework.md) | FastMCP as MCP framework | Accepted |
