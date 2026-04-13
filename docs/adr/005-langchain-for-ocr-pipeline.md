# ADR 005: LangChain for the OCR Pipeline

## Status

Accepted

## Date

2024-12-01

## Context

The OCR feature converts documents (PDF, DOCX, PPTX, images) to markdown or plain text using vision LLMs. We need to support multiple LLM providers:

- **Ollama** — Local inference (e.g., LLaVA model).
- **OpenRouter** — Cloud inference with access to many models (e.g., Gemini Flash).

We evaluated the following approaches:

1. **Direct API calls** — Use `httpx` to call each provider's API directly (Ollama REST API, OpenRouter REST API).
2. **LangChain** — Use LangChain's chat model abstractions (`BaseChatModel`) with provider-specific packages.
3. **LiteLLM** — A unified API wrapper for 100+ LLM providers.

## Decision

We chose **LangChain** with provider-specific packages:

- `langchain-core` — Base `BaseChatModel` interface and `HumanMessage` types.
- `langchain-ollama` — `ChatOllama` implementation.
- `langchain-openrouter` — `ChatOpenRouter` implementation.

The OCR module (`ocr.py`) uses dynamic imports to load the appropriate provider class at runtime:

```python
PROVIDERS = {
    "ollama": ("langchain_ollama", "ChatOllama"),
    "openrouter": ("langchain_openrouter", "ChatOpenRouter"),
}
```

## Consequences

### Positive

- **Uniform interface**: Both providers are used through the same `BaseChatModel.invoke()` API. Adding a new provider requires only one entry in the `PROVIDERS` dict.
- **Multimodal support**: LangChain's `HumanMessage` with `image_url` content type provides a standard way to send images to vision models across providers.
- **Dynamic loading**: Provider packages are only imported when the OCR feature is actually used, making them optional dependencies.
- **Community maintained**: Each `langchain-*` package is maintained by the provider or the LangChain community, so API changes are handled upstream.

### Negative

- **Heavy dependency chain**: LangChain packages pull in many transitive dependencies (Pydantic, tenacity, etc.), making the OCR extra significantly heavier than the base install.
- **Abstraction overhead**: For our use case (single image → text), the LangChain abstraction adds complexity without leveraging features like chains, memory, or agents.
- **Version churn**: LangChain has a history of rapid breaking changes between versions.

### Alternatives Considered

- **Direct API calls**: Simpler and lighter, but requires maintaining HTTP client code for each provider's different API format, authentication, and error handling. Would need to be updated when providers change their API.
- **LiteLLM**: Similar abstraction layer but focused on text completion rather than multimodal. Less mature support for image inputs at the time of implementation.

### Mitigations

- OCR dependencies are isolated in the `[ocr]` optional extra, so users who don't need OCR don't pay the dependency cost.
- The `PROVIDERS` registry pattern makes it easy to swap LangChain for direct API calls per-provider without changing the rest of the pipeline.
