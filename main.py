#!/usr/bin/env python3
"""
AutoApplier - Automated Job Application System

A free tool that automates the job application process for tech positions.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.utils.config import get_settings, Settings
from src.utils.database import get_db
from src.core.applicant import Applicant
from src.core.job import JobStatus

# Initialize Typer app
app = typer.Typer(
    name="autoapplier",
    help="🚀 AutoApplier - Automated Job Application System",
    add_completion=False,
)

console = Console()


@app.command()
def init():
    """Initialize AutoApplier - create config files and directories."""
    console.print("\n🚀 [bold blue]Initializing AutoApplier...[/bold blue]\n")
    
    settings = get_settings()
    settings.ensure_directories()
    
    # Create profile if doesn't exist
    profile_path = Path("data/profile.json")
    example_path = Path("data/profile.example.json")
    
    if not profile_path.exists() and example_path.exists():
        import shutil
        shutil.copy(example_path, profile_path)
        console.print("✅ Created [cyan]data/profile.json[/cyan] - please edit with your information")
    
    # Create .env if doesn't exist
    env_path = Path(".env")
    env_example = Path(".env.example")
    
    if not env_path.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_path)
        console.print("✅ Created [cyan].env[/cyan] - please add your API keys")
    
    console.print("\n[bold green]✅ Initialization complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Edit [cyan]data/profile.json[/cyan] with your information")
    console.print("  2. Add your Gemini API key to [cyan].env[/cyan]")
    console.print("  3. Add your resume as [cyan]data/resume.pdf[/cyan]")
    console.print("  4. Run [cyan]autoapplier status[/cyan] to verify setup")


@app.command()
def status():
    """Show current status and configuration."""
    console.print("\n📊 [bold blue]AutoApplier Status[/bold blue]\n")
    
    settings = get_settings()
    db = get_db()
    
    # Check configuration
    config_table = Table(title="Configuration Status")
    config_table.add_column("Item", style="cyan")
    config_table.add_column("Status", style="green")
    
    # Profile
    profile_path = Path("data/profile.json")
    if profile_path.exists():
        try:
            applicant = Applicant.from_file(profile_path)
            config_table.add_row("Profile", f"✅ Loaded ({applicant.full_name})")
        except Exception as e:
            config_table.add_row("Profile", f"⚠️ Error: {e}")
    else:
        config_table.add_row("Profile", "❌ Not found (run `init` first)")
    
    # Resume
    resume_path = Path("data/resume.pdf")
    config_table.add_row(
        "Resume", 
        "✅ Found" if resume_path.exists() else "❌ Not found"
    )
    
    # API Key
    config_table.add_row(
        "Gemini API Key",
        "✅ Configured" if settings.gemini_api_key else "❌ Not set"
    )
    
    # Notifications
    notif_status = []
    if settings.discord_webhook_url:
        notif_status.append("Discord")
    if settings.telegram_bot_token:
        notif_status.append("Telegram")
    if settings.ntfy_topic:
        notif_status.append("ntfy")
    
    config_table.add_row(
        "Notifications",
        f"✅ {', '.join(notif_status)}" if notif_status else "❌ None configured"
    )
    
    console.print(config_table)
    
    # Job statistics
    stats = db.get_job_stats()
    
    stats_table = Table(title="\nJob Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Count", style="yellow")
    
    stats_table.add_row("Total Jobs", str(stats["total"]))
    stats_table.add_row("Applied", str(stats["applied"]))
    stats_table.add_row("Pending", str(stats["pending"]))
    stats_table.add_row("Failed", str(stats["failed"]))
    
    console.print(stats_table)
    console.print()


@app.command()
def scrape(
    source: Optional[str] = typer.Option(
        None, "--source", "-s",
        help="Specific source to scrape (linkedin, jobright, simplify, cvrve, all)"
    ),
    limit: int = typer.Option(
        50, "--limit", "-l",
        help="Maximum number of jobs to scrape"
    ),
):
    """Scrape jobs from configured sources."""
    console.print("\n🔍 [bold blue]Scraping Jobs...[/bold blue]\n")
    
    # TODO: Implement scrapers in Phase 2
    console.print("[yellow]⚠️ Scrapers not implemented yet (Phase 2)[/yellow]")
    console.print("For now, use [cyan]autoapplier add-job[/cyan] to add jobs manually")


@app.command()
def add_job(
    url: str = typer.Argument(..., help="URL of the job posting"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Job title"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Company name"),
):
    """Add a job manually by URL."""
    console.print(f"\n➕ Adding job: {url}\n")
    
    from src.core.job import Job
    
    job = Job(
        url=url,
        title=title or "Unknown Title",
        company=company or "Unknown Company",
    )
    
    db = get_db()
    job_id = db.add_job(job)
    
    console.print(f"[green]✅ Job added with ID: {job_id}[/green]")


@app.command()
def apply(
    job_id: Optional[str] = typer.Argument(
        None, 
        help="Specific job ID to apply to (optional)"
    ),
    limit: int = typer.Option(
        5, "--limit", "-l",
        help="Maximum number of applications"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d",
        help="Run without actually submitting"
    ),
):
    """Apply to jobs in the queue."""
    mode = "[DRY RUN] " if dry_run else ""
    console.print(f"\n📝 {mode}[bold blue]Applying to Jobs...[/bold blue]\n")
    
    # TODO: Implement auto-apply in Phase 4
    console.print("[yellow]⚠️ Auto-apply not implemented yet (Phase 4)[/yellow]")
    console.print("Form fillers are required for autonomous application")


@app.command()
def jobs(
    status: Optional[str] = typer.Option(
        None, "--status", "-s",
        help="Filter by status (new, applied, failed, needs_review)"
    ),
    limit: int = typer.Option(
        20, "--limit", "-l",
        help="Maximum number of jobs to show"
    ),
):
    """List jobs in the database."""
    db = get_db()
    
    console.print("\n📋 [bold blue]Jobs[/bold blue]\n")
    
    if status:
        try:
            job_status = JobStatus(status)
            jobs_list = db.get_jobs_by_status(job_status, limit)
        except ValueError:
            console.print(f"[red]Invalid status: {status}[/red]")
            return
    else:
        jobs_list = db.get_pending_jobs(limit)
    
    if not jobs_list:
        console.print("[yellow]No jobs found[/yellow]")
        return
    
    table = Table()
    table.add_column("ID", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Company", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Type", style="magenta")
    
    for job in jobs_list:
        table.add_row(
            job.id[:8] if job.id else "N/A",
            job.title[:40],
            job.company[:20],
            job.status,
            job.application_type,
        )
    
    console.print(table)


@app.command()
def config():
    """Show current configuration."""
    settings = get_settings()
    
    console.print("\n⚙️ [bold blue]Configuration[/bold blue]\n")
    
    # Search settings
    console.print(Panel.fit(
        f"[cyan]Job Titles:[/cyan] {', '.join(settings.search.titles)}\n"
        f"[cyan]Locations:[/cyan] {', '.join(settings.search.locations)}\n"
        f"[cyan]Experience:[/cyan] {', '.join(settings.search.experience_levels)}\n"
        f"[cyan]Max Days Old:[/cyan] {settings.search.max_days_old}",
        title="Search Preferences"
    ))
    
    # Application settings
    console.print(Panel.fit(
        f"[cyan]Review Mode:[/cyan] {settings.application.review_mode}\n"
        f"[cyan]Max Per Run:[/cyan] {settings.application.max_per_run}\n"
        f"[cyan]Auto Submit:[/cyan] {settings.auto_submit}",
        title="Application Settings"
    ))


@app.command()
def version():
    """Show version information."""
    from src import __version__
    console.print(f"\n🚀 AutoApplier v{__version__}\n")


@app.command(name="llm-usage")
def llm_usage():
    """Show LLM API usage statistics (to stay within free tier)."""
    console.print("\n📊 [bold blue]LLM Usage Statistics[/bold blue]\n")
    
    settings = get_settings()
    
    if not settings.gemini_api_key:
        console.print("[red]❌ Gemini API key not configured[/red]")
        console.print("Add GEMINI_API_KEY to .env file")
        return
    
    try:
        from src.llm.gemini import GeminiClient
        client = GeminiClient()
        stats = client.get_usage_stats()
        
        table = Table(title="Gemini Free Tier Usage")
        table.add_column("Metric", style="cyan")
        table.add_column("Used", style="yellow")
        table.add_column("Limit", style="green")
        table.add_column("Remaining", style="magenta")
        
        table.add_row(
            "Daily Requests",
            str(stats["daily_requests"]),
            str(stats["daily_limit"]),
            str(stats["daily_remaining"])
        )
        table.add_row(
            "Monthly Tokens",
            f"{stats['monthly_tokens']:,}",
            f"{stats['monthly_limit']:,}",
            f"{stats['monthly_remaining']:,}"
        )
        
        console.print(table)
        
        # Warning if approaching limits
        daily_pct = stats["daily_requests"] / stats["daily_limit"] * 100
        monthly_pct = stats["monthly_tokens"] / stats["monthly_limit"] * 100
        
        if daily_pct > 80 or monthly_pct > 80:
            console.print("\n[yellow]⚠️ Approaching usage limits! Consider waiting before more requests.[/yellow]")
        else:
            console.print(f"\n[green]✅ Usage OK ({daily_pct:.1f}% daily, {monthly_pct:.1f}% monthly)[/green]")
            
    except Exception as e:
        console.print(f"[red]Error checking usage: {e}[/red]")


@app.command(name="test-llm")
def test_llm():
    """Test LLM connection with a simple query (uses 1 API call)."""
    console.print("\n🧪 [bold blue]Testing LLM Connection...[/bold blue]\n")
    
    settings = get_settings()
    
    if not settings.gemini_api_key:
        console.print("[red]❌ Gemini API key not configured[/red]")
        return
    
    try:
        from src.llm.gemini import GeminiClient
        client = GeminiClient()
        
        console.print("Sending test query...")
        response = client.generate(
            "Reply with exactly: 'AutoApplier LLM connection successful!'",
            max_tokens=50,
            temperature=0.0
        )
        
        if response:
            console.print(f"[green]✅ Response: {response}[/green]")
        else:
            console.print("[yellow]⚠️ No response received (might be rate limited)[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")

@app.command()
def dashboard(
    port: int = typer.Option(8080, "--port", "-p", help="Port to run dashboard on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
):
    """Launch the web dashboard to view and manage applications."""
    console.print("\n🚀 [bold blue]Starting AutoApplier Dashboard...[/bold blue]\n")
    console.print(f"📊 Open in browser: [cyan]http://{host}:{port}[/cyan]\n")
    
    try:
        from src.dashboard.app import run_dashboard
        run_dashboard(host=host, port=port)
    except ImportError as e:
        console.print("[red]Dashboard dependencies not installed.[/red]")
        console.print("Run: [cyan]pip install fastapi uvicorn jinja2[/cyan]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()
