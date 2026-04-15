import typer
from rich.table import Table

from aulasvirtuales_cli.app import app, console, get_client


@app.command()
def forums(course_id: int = typer.Argument(help="Course ID")) -> None:
    """List forums in a course."""
    client = get_client()
    forum_list = client.get_forums(course_id)

    if not forum_list:
        console.print("No forums in this course.", style="dim")
        raise typer.Exit()

    table = Table(title="Forums")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="white")

    for f in forum_list:
        table.add_row(str(f.id), f.name)

    console.print(table)


@app.command()
def discussions(
    forum_id: int = typer.Argument(help="Forum ID"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of discussions to show"),
) -> None:
    """List discussions in a forum."""
    client = get_client()
    disc_list = client.get_forum_discussions(forum_id, limit)

    if not disc_list:
        console.print("No discussions in this forum.", style="dim")
        raise typer.Exit()

    table = Table(title="Discussions")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Title", style="white")

    for d in disc_list:
        table.add_row(str(d.id), d.title)

    console.print(table)


@app.command()
def posts(discussion_id: int = typer.Argument(help="Discussion ID")) -> None:
    """Show messages in a forum discussion."""
    client = get_client()
    post_list = client.get_discussion_posts(discussion_id)

    if not post_list:
        console.print("No posts in this discussion.", style="dim")
        raise typer.Exit()

    for p in post_list:
        console.print(f"\n[bold cyan]{p.author}[/bold cyan] — [dim]{p.date}[/dim]")
        console.print(f"[bold]{p.subject}[/bold]")
        console.print(p.clean_message)
        console.print("─" * 60, style="dim")
