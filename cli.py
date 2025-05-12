import argparse
import asyncio
import logging
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.markdown import Markdown

# Import core components - adjust paths
from github_processor_node.core import node
from github_processor_node import index_db
from github_processor_node.utils import owner_repo_to_repo_rid, repo_rid_to_owner_repo

logger = logging.getLogger(__name__)

# CLI command implementations
async def list_repos_cmd():
    """List all tracked repositories."""
    repos = index_db.get_repositories(node.config.index_db_path)
    if not repos:
        print("No repositories are currently being tracked.")
        return

    console = Console()
    table = Table(title="Tracked GitHub Repositories")
    table.add_column("Repository RID", style="cyan", no_wrap=True)
    table.add_column("Owner/Repo", style="green")
    table.add_column("First Indexed", style="yellow")
    table.add_column("Last Updated", style="yellow")
    table.add_column("Events", style="magenta")

    for repo in repos:
        events_count = len(
            index_db.get_events_for_repo(
                node.config.index_db_path,
                repo["repo_rid"],
                limit=1000
            )
        )
        owner, repo_name = repo_rid_to_owner_repo(repo["repo_rid"])
        owner_repo = f"{owner}/{repo_name}"
        table.add_row(
            repo["repo_rid"],
            owner_repo,
            repo.get("first_indexed", "N/A"),
            repo.get("last_updated", "N/A"),
            str(events_count)
        )

    console.print(table)

async def show_events_cmd(repo_arg: str, limit: int = 50):
    """Show events for a repository."""
    if "/" in repo_arg and not repo_arg.startswith("orn:"):
        owner, repo = repo_arg.split("/", 1)
        repo_rid = owner_repo_to_repo_rid(owner, repo)
    else:
        repo_rid = repo_arg

    events = index_db.get_events_for_repo(node.config.index_db_path, repo_rid, limit=limit)
    if not events:
        print(f"No events found for repository: {repo_arg}")
        return

    console = Console()
    table = Table(title=f"Events for {repo_arg}")
    table.add_column("Type", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("Commit SHA", style="yellow", no_wrap=True)
    table.add_column("Summary", style="white")
    table.add_column("Event RID", style="dim")

    for event in events:
        timestamp = event.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        commit_sha = event.get("commit_sha", "") or ""
        if commit_sha:
            commit_sha = commit_sha[:8]

        table.add_row(
            event.get("event_type", "unknown"),
            timestamp,
            commit_sha,
            event.get("summary", ""),
            event.get("event_rid", "")
        )

    console.print(table)

async def show_event_details_cmd(event_rid: str):
    """Show detailed information about a specific event."""
    import sqlite3
    conn = sqlite3.connect(node.config.index_db_path)
    conn.row_factory = lambda c, r: dict(
        (col[0], r[idx]) for idx, col in enumerate(c.description)
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE event_rid = ?", (event_rid,))
    event = cursor.fetchone()
    if not event:
        print(f"Event not found: {event_rid}")
        conn.close()
        return

    cursor.execute(
        "SELECT * FROM repositories WHERE repo_rid = ?",
        (event.get("repo_rid", ""),)
    )
    repo = cursor.fetchone() or {}
    conn.close()

    console = Console()
    layout = Layout()
    layout.split(Layout(name="header", size=3), Layout(name="main"))

    event_type = event.get("event_type", "unknown").upper()
    layout["header"].update(
        Panel(
            Text(f"Event Details: {event_type}", style="bold white on blue"),
            style="bold white on blue"
        )
    )

    details = [
        f"## {event_type} Event\n",
        f"**RID:** {event.get('event_rid', 'N/A')}\n",
        f"**Repository:** {event.get('repo_rid', 'N/A')}\n",
        f"**Repository URL:** {repo.get('repo_url', 'N/A')}\n",
        f"**Timestamp:** {event.get('timestamp', 'N/A')}\n",
    ]
    if event.get("commit_sha"):
        details.append(f"**Commit SHA:** {event.get('commit_sha', 'N/A')}\n")
    details.append(f"**Summary:** {event.get('summary', 'N/A')}\n")
    if event.get("bundle_rid"):
        details.append(f"**Bundle RID:** {event.get('bundle_rid', 'N/A')}\n")

    layout["main"].update(Panel(Markdown("\n".join(details))))
    console.print(layout)

async def add_repo_cmd(repo_arg: str):
    """Manually add a repository to the database."""
    if "/" in repo_arg and not repo_arg.startswith("orn:"):
        owner, repo = repo_arg.split("/", 1)
        repo_rid = owner_repo_to_repo_rid(owner, repo)
    else:
        repo_rid = repo_arg

    try:
        owner, repo = repo_rid_to_owner_repo(repo_rid)
        repo_url = f"https://github.com/{owner}/{repo}"
        console = Console()
        console.print(f"Adding repository [cyan]{owner}/{repo}[/cyan] to database...")
        index_db.add_repository(node.config.index_db_path, repo_rid, repo_url)
        console.print(f"[green]Repository added successfully:[/green] {repo_rid}")
    except Exception as e:
        Console().print(f"[red]Error adding repository:[/red] {e}")

async def summarize_events_cmd():
    """Show a summary of all events in the database."""
    import sqlite3
    conn = sqlite3.connect(node.config.index_db_path)
    conn.row_factory = lambda c, r: dict(
        (col[0], r[idx]) for idx, col in enumerate(c.description)
    )
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT event_type, COUNT(*) as count FROM events GROUP BY event_type ORDER BY count DESC"
        )
        event_types = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as count FROM events")
        total_events = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM repositories")
        repo_count = cursor.fetchone()["count"]
        cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 1")
        latest_event = cursor.fetchone()
    except Exception as e:
        Console().print(f"[red]Error querying database:[/red] {e}")
        return
    finally:
        conn.close()

    console = Console()
    console.print(Panel(Text("GitHub Events Summary", style="bold white"), style="bold blue"))
    console.print(f"Total Repositories: [cyan]{repo_count}[/cyan]")
    console.print(f"Total Events: [cyan]{total_events}[/cyan]")
    if latest_event and latest_event.get("timestamp"):
        console.print(
            f"Latest Event: [yellow]{latest_event.get('timestamp')}[/yellow] "
            f"({latest_event.get('event_type')})"
        )

    table = Table(title="Events by Type")
    table.add_column("Event Type", style="cyan")
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Percentage", style="green", justify="right")

    for et in event_types:
        pct = (et["count"] / total_events) * 100 if total_events else 0
        table.add_row(et["event_type"], str(et["count"]), f"{pct:.1f}%")

    console.print(table)

def get_db_connection(db_path):
    """Helper function to get a database connection with dict factory."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    parser = argparse.ArgumentParser(
        description="KOI-net GitHub Events Explorer CLI"
    )
    subs = parser.add_subparsers(dest="command", help="Available commands")

    subs.add_parser("list-repos", help="List all tracked repositories")
    subs.add_parser("summary", help="Show summary of all events in the database")

    show_ev = subs.add_parser("show-events", help="Show events for a repository")
    show_ev.add_argument("repo", help="Repository identifier (owner/repo or RID)")
    show_ev.add_argument(
        "--limit", type=int, default=50, help="Maximum number of events to show"
    )

    det = subs.add_parser("event-details", help="Show details for a specific event")
    det.add_argument("event_rid", help="Event RID")

    add = subs.add_parser("add-repo", help="Manually add a repository")
    add.add_argument("repo", help="Repository identifier (owner/repo or RID)")

    args = parser.parse_args()
    if args.command == "list-repos":
        asyncio.run(list_repos_cmd())
    elif args.command == "show-events":
        asyncio.run(show_events_cmd(args.repo, args.limit))
    elif args.command == "event-details":
        asyncio.run(show_event_details_cmd(args.event_rid))
    elif args.command == "add-repo":
        asyncio.run(add_repo_cmd(args.repo))
    elif args.command == "summary":
        asyncio.run(summarize_events_cmd())
    else:
        console = Console()
        if args.command is None:
            console.print(
                Panel(
                    Markdown("# GitHub Events Explorer\n\n"
                             "This CLI tool allows you to explore GitHub events stored in the database."),
                    title="Welcome",
                    border_style="green"
                )
            )
            print("\nAvailable commands:")
        else:
            print(f"Unknown command: {args.command}")
        parser.print_help()

if __name__ == "__main__":
    main()
