# ADR 006: FastMCP as MCP Framework

## Status

Accepted

## Date

2024-12-01

## Context

The Model Context Protocol (MCP) allows AI agents to interact with external tools and data sources through a standardized protocol. We needed to expose Moodle functionality as MCP tools for AI assistants like Claude Desktop, Cursor, and Copilot.

We evaluated the following approaches:

1. **Official MCP Python SDK** (`mcp`) — The reference implementation maintained by Anthropic.
2. **FastMCP** — A higher-level framework built on top of the official SDK, inspired by FastAPI's decorator-based API design.
3. **Custom implementation** — Build a minimal MCP server directly on top of JSON-RPC.

## Decision

We chose **FastMCP** for its simplicity and developer experience.

Tools are defined with a simple decorator pattern:

```python
from fastmcp import FastMCP

mcp = FastMCP("AulasVirtuales")

@mcp.tool()
def get_courses():
    """List enrolled courses."""
    client = _get_client()
    return client.get_courses()
```

The server runs via stdio transport with `mcp.run()`.

## Consequences

### Positive

- **Minimal boilerplate**: Each tool is a decorated function with a docstring. No schema definitions, handler registrations, or protocol plumbing needed.
- **Automatic schema generation**: FastMCP generates JSON Schema for tool parameters from Python type hints and docstrings.
- **FastAPI-like DX**: Developers familiar with FastAPI feel immediately at home with the decorator pattern.
- **Built on official SDK**: FastMCP uses the official `mcp` SDK under the hood, so it's protocol-compliant and benefits from upstream fixes.
- **Image support**: FastMCP provides `Image` types for returning images in tool results (used in `read_downloaded_file`).

### Negative

- **Additional dependency**: Adds a layer on top of the official SDK, which increases the dependency surface.
- **Less control**: Advanced MCP features (custom transports, resource subscriptions, server-side prompts) may require dropping down to the official SDK.
- **Younger project**: FastMCP has less adoption and community support compared to the official SDK.

### Alternatives Considered

- **Official MCP SDK**: More verbose but provides full control over the protocol. Each tool requires manual schema definition and handler registration. Better for complex servers with custom transports.
- **Custom JSON-RPC**: Maximum flexibility but requires implementing the MCP protocol from scratch, including schema negotiation, capability advertisement, and transport handling.

### Neutral

- The stdio transport is the standard for local MCP servers and works out of the box with all major MCP clients.
- Migration from FastMCP to the official SDK would be straightforward since the tool logic (Moodle client calls) is independent of the framework.
