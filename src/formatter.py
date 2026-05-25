from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from datetime import datetime

console = Console()


def format_recommendations(recommendations: list, comparison_table: str) -> None:
    """Format and display project recommendations."""

    # Header
    console.print()
    console.print(Panel(
        "[bold green]Top {} Recommendations[/bold green]".format(len(recommendations)),
        border_style="green",
        padding=(1, 2)
    ))
    console.print()

    # Display each recommendation
    for rec in recommendations:
        # Create recommendation panel
        content = Text()
        content.append(f"{rec.summary_zh}\n\n", style="white")
        content.append("Pros:\n", style="bold green")
        for pro in rec.pros:
            content.append(f"  + {pro}\n", style="green")
        content.append("\nCons:\n", style="bold red")
        for con in rec.cons:
            content.append(f"  - {con}\n", style="red")
        content.append(f"\n{rec.verdict}", style="bold yellow")

        # Stars and last update
        stars_str = f"Stars: {rec.stars:,}"
        try:
            update_date = datetime.fromisoformat(rec.last_update.replace("Z", "+00:00"))
            update_str = f"Updated: {update_date.strftime('%Y-%m-%d')}"
        except Exception:
            update_str = f"Updated: {rec.last_update}"

        title = f"#{rec.rank} {rec.name} | {stars_str} | {update_str}"

        panel = Panel(
            content,
            title=f"[bold blue]{title}[/bold blue]",
            subtitle=f"[link={rec.url}]{rec.url}[/link]",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()

    # Display comparison table
    if comparison_table:
        console.print(Panel(
            "[bold]Comparison Table[/bold]",
            border_style="cyan"
        ))
        console.print()
        console.print(Markdown(comparison_table))
        console.print()


def format_search_progress(query: str) -> None:
    """Display search progress."""
    console.print(Panel(
        f"[bold blue]Search Query:[/bold blue] {query}",
        title="HubSeek",
        border_style="blue"
    ))


def format_strategy(strategy) -> None:
    """Display generated search strategy."""
    console.print()
    console.print("[bold]Search Strategy:[/bold]")
    console.print(f"  Keywords: {', '.join(strategy.keywords)}")
    if strategy.topics:
        console.print(f"  Topics: {', '.join(strategy.topics)}")
    if strategy.language:
        console.print(f"  Language: {strategy.language}")
    if strategy.min_stars > 0:
        console.print(f"  Min Stars: {strategy.min_stars}")
    console.print()


def format_searching() -> None:
    """Display searching status."""
    console.print("[bold]Searching GitHub for candidates...[/bold]")


def format_fetching() -> None:
    """Display fetching status."""
    console.print("[bold]Fetching repo details concurrently...[/bold]")


def format_analyzing() -> None:
    """Display analyzing status."""
    console.print("[bold]AI Analyzing...[/bold]")


def format_error(message: str) -> None:
    """Display error message."""
    console.print(f"[red]Error: {message}[/red]")


def format_cache_stats(stats: dict) -> None:
    """Display cache statistics."""
    console.print()
    console.print("[bold]Cache Statistics:[/bold]")
    console.print(f"  Entries: {stats['size']}")
    console.print(f"  Directory: {stats['directory']}")
    console.print()
