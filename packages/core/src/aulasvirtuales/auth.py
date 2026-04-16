import httpx
import keyring
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://aulasvirtuales.frba.utn.edu.ar"
LOGIN_URL = f"{BASE_URL}/login/index.php"
SERVICE_NAME = "aulasvirtuales-cli"

KEYCLOAK_ERROR_SELECTORS = (
    "#input-error",
    ".alert-error",
    "span.kc-feedback-text",
)


class AuthenticationError(Exception):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


def save_credentials(username: str, password: str) -> None:
    """Store university credentials in the OS keychain."""
    keyring.set_password(SERVICE_NAME, "username", username)
    keyring.set_password(SERVICE_NAME, "password", password)


def get_credentials() -> tuple[str, str] | None:
    """Retrieve stored credentials from the OS keychain."""
    username = keyring.get_password(SERVICE_NAME, "username")
    password = keyring.get_password(SERVICE_NAME, "password")
    if not username or not password:
        return None
    return username, password


def delete_credentials() -> None:
    """Remove stored credentials from the OS keychain."""
    for key in ("username", "password"):
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except keyring.errors.PasswordDeleteError:
            pass


def login(username: str, password: str, headless: bool = True) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(LOGIN_URL)
            page.click("a.btn.btn-primary.btn-lg[href*='oauth2']")

            try:
                page.wait_for_selector("#username", timeout=15000)
            except PlaywrightTimeoutError:
                raise AuthenticationError(
                    "El portal SSO de UTN no respondió. Verificá tu conexión "
                    "o que aulasvirtuales.frba.utn.edu.ar esté operativo."
                )

            page.fill("#username", username)
            page.fill("#outlined-adornment-password", password)
            page.click("button:has-text('Iniciar sesión')")

            try:
                page.wait_for_url(f"{BASE_URL}/**", timeout=15000)
            except PlaywrightTimeoutError:
                if _has_keycloak_error(page):
                    raise InvalidCredentialsError(
                        "Usuario o contraseña incorrectos"
                    )
                raise AuthenticationError(
                    f"Login no completó (URL actual: {page.url})"
                )

            cookies = context.cookies(BASE_URL)
            session_cookie = next(
                (c["value"] for c in cookies if c["name"] == "MoodleSession"),
                None,
            )
        finally:
            browser.close()

    if not session_cookie:
        raise AuthenticationError("No MoodleSession cookie found after login")

    return session_cookie


def _has_keycloak_error(page) -> bool:
    for selector in KEYCLOAK_ERROR_SELECTORS:
        if page.query_selector(selector):
            return True
    return False


def save_token(token: str) -> None:
    keyring.set_password(SERVICE_NAME, "token", token)


def get_token() -> str | None:
    return keyring.get_password(SERVICE_NAME, "token")


def delete_token() -> None:
    try:
        keyring.delete_password(SERVICE_NAME, "token")
    except keyring.errors.PasswordDeleteError:
        pass


def is_session_valid(session_cookie: str) -> bool:
    response = httpx.get(
        f"{BASE_URL}/my/",
        cookies={"MoodleSession": session_cookie},
        follow_redirects=False,
    )
    return response.status_code == 200
