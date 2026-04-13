# ADR 002: Playwright for SSO Authentication

## Status

Accepted

## Date

2024-12-01

## Context

UTN FRBA's Moodle instance uses **Keycloak SSO** with OAuth2 for authentication. To interact with Moodle programmatically, we need a valid `MoodleSession` cookie.

We evaluated the following approaches:

1. **Moodle Web Services API tokens** — Moodle has a built-in API token system (`/login/token.php`), but UTN FRBA's instance does not expose this endpoint for students.
2. **Direct HTTP form submission** — Submit credentials via `requests`/`httpx` by replicating the SSO flow. This requires handling OAuth2 redirects, CSRF tokens, and dynamic form parameters from Keycloak.
3. **Headless browser automation** — Use a browser automation tool (Playwright, Selenium) to drive the real login flow.

## Decision

We chose **Playwright** with **headless Chromium** to automate the SSO login flow.

The login process:
1. Navigate to Moodle's login page.
2. Click the OAuth2 SSO button.
3. Fill username and password on the Keycloak form.
4. Wait for redirect back to Moodle.
5. Extract the `MoodleSession` cookie from the browser context.

## Consequences

### Positive

- **Resilient to SSO changes**: The browser handles all redirects, CSRF tokens, and dynamic form elements automatically. If Keycloak adds new fields or changes redirect URLs, the flow still works as long as the basic form structure remains.
- **No reverse engineering**: We don't need to understand or replicate the internal OAuth2 flow, which could change without notice.
- **Battle-tested**: Playwright is maintained by Microsoft and handles edge cases (timeouts, network errors, JavaScript-heavy pages) well.

### Negative

- **Heavy dependency**: Playwright requires downloading Chromium (~150MB), which is significant for a CLI tool.
- **Slower**: A headless browser login takes 3–5 seconds vs. sub-second for direct HTTP requests.
- **Installation complexity**: Users must run `playwright install chromium` separately after installing the Python package.
- **Not CI-friendly**: Running Playwright in CI requires additional setup (system dependencies, Xvfb for headed mode).

### Neutral

- The session cookie is cached in the OS keychain, so the Playwright login only runs once per session (or when the session expires). This mitigates the performance cost.
- The Homebrew formula handles Playwright installation automatically, hiding the complexity from end users.
