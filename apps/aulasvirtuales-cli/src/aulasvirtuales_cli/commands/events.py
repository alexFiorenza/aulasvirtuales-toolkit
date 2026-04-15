import typer
from rich.table import Table

from aulasvirtuales_cli.app import app, console, get_client


@app.command()
def events(
    course_id: int = typer.Argument(None, help="Course ID (optional, omit to show all)"),
) -> None:
    """Show upcoming events and pending assignments."""
    client = get_client()
    event_list = client.get_upcoming_events(course_id)

    if not event_list:
        console.print("No upcoming events.", style="dim")
        raise typer.Exit()

    table = Table(title="Upcoming Events")
    table.add_column("Date", style="cyan")
    table.add_column("Course", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Name", style="white")
    table.add_column("Action", style="yellow")

    for e in event_list:
        table.add_row(e.date, e.course_name, e.module, e.name, e.action)

    console.print(table)
