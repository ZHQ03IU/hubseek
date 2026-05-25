import sys
import asyncio
import webbrowser
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .config import load_config, validate_config, create_default_config
from .github import GitHubClient
from .ai_analyzer import AIAnalyzer
from .cache import CacheManager
from .formatter import (
    format_recommendations,
    format_search_progress,
    format_strategy,
    format_searching,
    format_fetching,
    format_analyzing,
    format_error,
    format_cache_stats
)

console = Console()


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.run(coro)


def _handle_error(e: Exception) -> None:
    """Display friendly error messages based on exception type."""
    err_str = str(e).lower()
    err_type = type(e).__name__

    # Network errors
    if "connect" in err_str or "timeout" in err_str or "network" in err_str:
        console.print(Panel(
            "[bold red]Network connection failed[/bold red]\n\n"
            "Cannot reach remote server, please check:\n"
            "  1. Is your network working?\n"
            "  2. Do you need a proxy?\n"
            "  3. Is a firewall blocking the connection?",
            title="[red]Error[/red]",
            border_style="red"
        ))
        return

    # GitHub rate limit (403)
    if "403" in err_str or "rate limit" in err_str:
        console.print(Panel(
            "[bold red]GitHub API rate limit exceeded[/bold red]\n\n"
            "Your GitHub Token has hit the rate limit:\n"
            "  1. Wait a while and try again\n"
            "  2. Check if your Token is valid\n"
            "  3. Run [cyan]hubseek config:show[/cyan] to view current config",
            title="[red]Rate Limited[/red]",
            border_style="red"
        ))
        return

    # 429 -- rate limit from either GitHub or LLM API
    if "429" in err_str:
        is_llm = "openai" in err_str or "api" in err_str or "model" in err_str
        if is_llm:
            console.print(Panel(
                "[bold red]AI API rate limit exceeded[/bold red]\n\n"
                "Please wait a moment and try again, or check your API quota.",
                title="[red]Rate Limited[/red]",
                border_style="red"
            ))
        else:
            console.print(Panel(
                "[bold red]API rate limit exceeded[/bold red]\n\n"
                "Please wait a moment and try again.",
                title="[red]Rate Limited[/red]",
                border_style="red"
            ))
        return

    # JSON parse error from AI response
    if "json" in err_str or err_type == "JSONDecodeError":
        console.print(Panel(
            "[bold red]AI returned invalid format[/bold red]\n\n"
            "AI did not return valid JSON. Please try again.\n"
            "If this keeps happening, check if your model config is correct.",
            title="[red]Parse Error[/red]",
            border_style="red"
        ))
        return

    # 401 -- distinguish LLM API key vs GitHub token
    if "401" in err_str:
        # LLM API key issues typically mention openai/api/key/model in the error
        is_llm_auth = any(kw in err_str for kw in ("openai", "api_key", "api key", "model", "chat/completions"))
        if is_llm_auth:
            console.print(Panel(
                "[bold red]AI API Key is invalid[/bold red]\n\n"
                "Please check openai_api_key in your config:\n"
                "  1. Is the key correct?\n"
                "  2. Do you have sufficient balance?\n"
                "  3. Run [cyan]hubseek config:show[/cyan] to view current config",
                title="[red]API Error[/red]",
                border_style="red"
            ))
        else:
            console.print(Panel(
                "[bold red]GitHub Token is invalid[/bold red]\n\n"
                "Please check github_token in your config:\n"
                "  1. Has the token expired?\n"
                "  2. Run [cyan]hubseek config:show[/cyan] to view current config\n"
                "  3. Regenerate at https://github.com/settings/tokens",
                title="[red]Auth Error[/red]",
                border_style="red"
            ))
        return

    # Generic fallback
    console.print(Panel(
        f"[bold red]An unknown error occurred[/bold red]\n\n"
        f"Type: [cyan]{err_type}[/cyan]\n"
        f"Detail: {e}\n\n"
        f"Run [cyan]hubseek --help[/cyan] for usage info.",
        title="[red]Error[/red]",
        border_style="red"
    ))


async def search_async(query: str, cfg: dict) -> list:
    """Async search implementation. Returns list of recommendations."""

    # Initialize components
    github_client = GitHubClient(token=cfg["github_token"])
    ai_analyzer = AIAnalyzer(
        api_key=cfg["openai_api_key"],
        base_url=cfg["openai_base_url"],
        model=cfg["model"]
    )
    cache = CacheManager(ttl_hours=cfg["cache_ttl_hours"])

    # Step 1: Generate search strategy using AI
    format_search_progress(query)
    console.print("[bold]AI Generating search strategy...[/bold]")

    strategy = await ai_analyzer.generate_search_strategy(query)
    format_strategy(strategy)

    # Step 2: Search GitHub (Combined: Repos + Code)
    cache_key = "+".join(sorted(strategy.keywords))
    cached_results = cache.get_search_results(cache_key, cfg["max_results"])

    if cached_results:
        console.print("[green]Using cached results[/green]")
        search_results = cached_results
        search_source = "Cache"
    else:
        format_searching()
        search_results, search_source = await github_client.search_combined(
            keywords=strategy.keywords,
            topics=strategy.topics,
            language=strategy.language,
            min_stars=strategy.min_stars,
            exclude_keywords=strategy.exclude_keywords,
            max_results=cfg["max_results"],
            min_repo_results=5
        )
        # Cache search results
        cache.set_search_results(cache_key, cfg["max_results"], search_results)

    console.print(f"[dim]Source: {search_source}[/dim]")

    if not search_results:
        console.print("[yellow]No matching projects found[/yellow]")
        return []

    # Step 3: Fetch repo details concurrently
    format_fetching()

    # Check cache for each repo
    repos_to_fetch = []
    cached_repos = []
    project_names = []

    for repo in search_results:
        full_name = repo["full_name"]
        project_names.append(full_name)
        cached = cache.get_repo_details(full_name, cfg["readme_max_chars"])
        if cached:
            cached_repos.append(cached)
        else:
            repos_to_fetch.append(repo)

    # Fetch uncached repos
    if repos_to_fetch:
        fetched_repos = await github_client.get_multiple_repo_details(
            repos=repos_to_fetch,
            readme_max_chars=cfg["readme_max_chars"]
        )
        # Cache fetched repos
        for repo in fetched_repos:
            if not isinstance(repo, Exception):
                cache.set_repo_details(
                    repo.full_name,
                    cfg["readme_max_chars"],
                    repo.__dict__
                )
                cached_repos.append(repo.__dict__)

    console.print(f"[green]Fetched {len(cached_repos)} project details[/green]")

    # Step 4: AI Analysis
    format_analyzing()

    # Check cache for analysis
    cached_analysis = cache.get_analysis(query, project_names)
    if cached_analysis:
        console.print("[green]Using cached analysis[/green]")
        analysis_result = cached_analysis
    else:
        analysis = await ai_analyzer.analyze_projects(
            user_query=query,
            projects=cached_repos
        )
        analysis_result = {
            "recommendations": [r.__dict__ for r in analysis.recommendations],
            "comparison_table": analysis.comparison_table
        }
        # Cache analysis
        cache.set_analysis(query, project_names, analysis_result)

    # Step 5: Display results
    from .ai_analyzer import ProjectRecommendation

    recommendations = [
        ProjectRecommendation(**rec) for rec in analysis_result["recommendations"]
    ]
    format_recommendations(recommendations, analysis_result["comparison_table"])

    return recommendations


def _interactive_open_browser(recommendations: list) -> None:
    """Interactive prompt to open recommended projects in browser."""
    if not recommendations:
        return

    console.print()
    while True:
        choice = Prompt.ask(
            "[bold cyan]Open in browser? Enter number (1-{}) or 0 to exit[/bold cyan]".format(
                len(recommendations)
            ),
            default="0"
        )

        if choice == "0":
            console.print("[dim]Bye![/dim]")
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(recommendations):
                url = recommendations[idx].url
                console.print(f"[green]Opening {url}...[/green]")
                webbrowser.open(url)
            else:
                console.print(f"[yellow]Please enter a number between 1 and {len(recommendations)}[/yellow]")
        except ValueError:
            console.print("[yellow]Invalid input, please enter a number[/yellow]")


@click.group()
@click.version_option(version="2.0.0", prog_name="hubseek")
def cli():
    """HubSeek - Natural language GitHub project finder powered by AI

    Use natural language to search and discover GitHub projects.
    Results are analyzed by AI with Chinese summaries and pros/cons.
    """
    pass


@cli.command()
@click.argument("query")
@click.option("--config", "-c", default=None, help="Config file path")
@click.option("--results", "-n", default=None, type=int, help="Number of recommendations")
def search(query: str, config: str, results: int):
    """Search GitHub projects with natural language

    Examples:

        hubseek search "markdown to resume converter"

        hubseek search "Python Web framework" --results 3

        hubseek search "React state management" -n 5
    """
    # Load config
    cfg = load_config(config)

    # Override results count if specified
    if results:
        cfg["final_recommendations"] = results

    # Validate config
    errors = validate_config(cfg)
    if errors:
        console.print("[red]Config errors:[/red]")
        for error in errors:
            console.print(f"  * {error}")
        console.print("\n[yellow]Hint:[/yellow] Run [cyan]hubseek config:init[/cyan] to create config file")
        sys.exit(1)

    # Run async search
    try:
        recommendations = run_async(search_async(query, cfg))
        _interactive_open_browser(recommendations)
    except KeyboardInterrupt:
        console.print("\n[yellow]Search cancelled[/yellow]")
    except Exception as e:
        _handle_error(e)
        sys.exit(1)


@cli.command("config:init")
@click.option("--config", "-c", default=None, help="Config file path")
def config_init(config: str):
    """Initialize config file"""
    path = create_default_config(config)
    console.print(f"[green][OK][/green] Config file created: {path}")
    console.print("\n[yellow]Please edit the config file and fill in:[/yellow]")
    console.print("  - openai_api_key: Your OpenAI-compatible API key")
    console.print("  - github_token: Your GitHub personal access token")
    console.print("  - openai_base_url: API base URL (optional, default: OpenAI)")
    console.print("  - model: Model to use (optional, default: gpt-4o-mini)")


@cli.command("config:show")
@click.option("--config", "-c", default=None, help="Config file path")
def config_show(config: str):
    """Show current config"""
    cfg = load_config(config)

    # Mask sensitive values
    masked_config = cfg.copy()
    if masked_config.get("openai_api_key"):
        key = masked_config["openai_api_key"]
        masked_config["openai_api_key"] = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
    if masked_config.get("github_token"):
        token = masked_config["github_token"]
        masked_config["github_token"] = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"

    console.print(Panel(
        "\n".join(f"  {k}: {v}" for k, v in masked_config.items()),
        title="Current Config",
        border_style="green"
    ))


@cli.command("cache:clear")
def cache_clear():
    """Clear all cache"""
    cache = CacheManager()
    cache.clear()
    console.print("[green][OK][/green] Cache cleared")


@cli.command("cache:stats")
def cache_stats():
    """Show cache statistics"""
    cache = CacheManager()
    format_cache_stats(cache.stats())


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
