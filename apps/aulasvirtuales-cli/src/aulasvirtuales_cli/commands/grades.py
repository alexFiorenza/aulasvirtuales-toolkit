import typer
from rich.table import Table

from aulasvirtuales_cli.app import app, console, get_client


@app.command()
def grades(
    course_id: int = typer.Argument(help="Course ID"),
    with_comments: bool = typer.Option(
        False, "--with-comments", help="Fetch deep inline submission comments for assignments (slower)"
    ),
    with_status: bool = typer.Option(
        False, "--with-status", help="Fetch submission status for assignments (slower)"
    ),
) -> None:
    """Show grades and feedback for a course."""
    client = get_client()

    spinner_msg = "Fetching grades..."
    if with_status:
        spinner_msg = "Fetching grades and submission status..."
    elif with_comments:
        spinner_msg = "Fetching grades and deep comments..."

    with console.status(spinner_msg, spinner="dots"):
        if with_status:
            grade_list = client.get_grades_with_status(course_id)
        else:
            grade_list = client.get_grades(course_id)

    if not grade_list:
        console.print("No grades or feedback found for this course.", style="dim")
        raise typer.Exit()

    assigns = []
    if with_comments:
        sections = client.get_course_contents(course_id)
        assigns = [r for s in sections for r in s.resources if r.module == 'assign']

    table = Table(title="Grades and Feedback")
    table.add_column("Item", style="cyan", overflow="fold")
    table.add_column("Grade", style="green", justify="center")
    table.add_column("Range", style="dim", justify="center")
    table.add_column("Percentage", style="yellow", justify="center")
    if with_status:
        table.add_column("Status", style="magenta", justify="center")
    table.add_column("Feedback", style="white", overflow="fold")

    for g in grade_list:
        final_grade = g.grade if g.grade else "-"
        combined_feedback = []
        if g.feedback and g.feedback not in ("&nbsp;", "-", ""):
            combined_feedback.append(f"[dim]General:[/dim] {g.feedback}")

        if with_comments and assigns:
            matched_assign = next((a for a in assigns if a.name in g.name), None)
            if matched_assign:
                try:
                    details = client.get_assignment_details(matched_assign.id)
                    if details.grade and details.grade not in ("-", "&nbsp;", ""):
                        final_grade = details.grade

                    if details.comments:
                        sub_text = "\n".join([f"[{c.author}]: {c.content}" for c in details.comments])
                        combined_feedback.append(f"[dim]Inline:[/dim]\n{sub_text}")
                except Exception:
                    pass

        feedback_str = "\n".join(combined_feedback) if combined_feedback else "-"
        if with_status:
            table.add_row(g.name, final_grade, g.range, g.percentage, g.status or "-", feedback_str)
        else:
            table.add_row(g.name, final_grade, g.range, g.percentage, feedback_str)

    console.print(table)
