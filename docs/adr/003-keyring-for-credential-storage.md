# ADR 003: Keyring for Credential Storage

## Status

Accepted

## Date

2024-12-01

## Context

The toolkit needs to persist user credentials (username, password) and session tokens (MoodleSession cookie) between invocations. We evaluated the following storage mechanisms:

1. **Environment variables only** — `MOODLE_USERNAME` and `MOODLE_PASSWORD` as env vars.
2. **Plaintext config file** — Store credentials in `~/.config/aulasvirtuales/config.json`.
3. **`.env` file** — Store credentials in a `.env` file.
4. **OS keychain** — Use the operating system's secure credential storage via the `keyring` library.

## Decision

We chose the **OS keychain** via the `keyring` Python library, which integrates with:

- **macOS**: Keychain Access
- **Linux**: GNOME Keyring / KDE Wallet / SecretService
- **Windows**: Windows Credential Locker

Credentials are stored with service name `aulasvirtuales-cli` and keys `username`, `password`, and `token`.

Environment variables (`MOODLE_USERNAME`, `MOODLE_PASSWORD`) are supported as an override, primarily for the MCP server where env vars are the standard configuration mechanism.

## Consequences

### Positive

- **Secure by default**: Credentials are encrypted at rest by the OS. No plaintext files on disk.
- **Standard practice**: Users expect CLI tools to use the system keychain (similar to `gh`, `aws-cli`, `docker`).
- **Cross-platform**: The `keyring` library abstracts away OS-specific APIs.
- **No accidental commits**: Credentials can't end up in version control (unlike `.env` files).
- **Multiple access methods**: Both CLI (`keyring`) and MCP (`env vars`) can provide credentials.

### Negative

- **Headless environments**: Some CI/server environments don't have a keyring backend available (requires `keyrings.alt` or env var fallback).
- **First-time setup**: Users must explicitly run `aulasvirtuales login` to store credentials, rather than just setting env vars.
- **Debug difficulty**: It's harder to inspect stored credentials compared to a config file.

### Neutral

- The `keyring` library is a well-maintained, widely-used package with no heavy dependencies.
- Session tokens are also stored in the keychain, providing consistent secure storage for all sensitive data.
