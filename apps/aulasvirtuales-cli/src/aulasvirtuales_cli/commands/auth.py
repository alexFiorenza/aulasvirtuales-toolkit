import typer

from aulasvirtuales.auth import (
    delete_credentials,
    delete_token,
    get_credentials,
    get_token,
    is_session_valid,
    login,
    save_credentials,
    save_token,
)
from aulasvirtuales_cli.app import app, console


@app.command(name="login")
def login_cmd() -> None:
    """Authenticate and store credentials securely in the OS keychain."""
    import getpass

    username = console.input("[cyan]Username:[/cyan] ")
    password = getpass.getpass("Password: ")

    console.print("Authenticating...", style="yellow")
    token = login(username, password)
    save_credentials(username, password)
    save_token(token)
    console.print("Logged in successfully. Credentials stored in keychain.", style="green")


@app.command(name="logout")
def logout_cmd() -> None:
    """Remove stored credentials and session from the OS keychain."""
    delete_credentials()
    delete_token()
    console.print("Credentials and session removed from keychain.", style="green")


@app.command()
def status() -> None:
    """Check authentication status."""
    creds = get_credentials()
    if not creds:
        console.print("Not logged in. Run [bold]aulasvirtuales login[/bold].", style="red")
        return

    username, _ = creds
    token = get_token()
    if token and is_session_valid(token):
        console.print(f"Logged in as [bold]{username}[/bold] (session active).", style="green")
    else:
        console.print(f"Logged in as [bold]{username}[/bold] (session expired, will re-auth on next command).", style="yellow")
