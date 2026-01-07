#!/usr/bin/env python3

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

app = typer.Typer(name="autoapplier", add_completion=False)
console = Console()


@app.command()
def init():
    console.print("\n🚀 [bold blue]Initializing AutoApplier...[/bold blue]\n")
    
    settings = get_settings()
    settings.ensure_directories()
    
    profile_path = Path("data/profile.json")
    example_path = Path("data/profile.example.json")
    
    if not profile_path.exists() and example_path.exists():
        import shutil
        shutil.copy(example_path, profile_path)
        console.print("✅ Created [cyan]data/profile.json[/cyan]")
    
    env_path = Path(".env")
    env_example = Path(".env.example")
    
    if not env_path.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_path)
        console.print("✅ Created [cyan].env[/cyan]")
    
    console.print("\n[bold green]✅ Initialization complete![/bold green]")


@app.command()
def status():
    console.print("\n📊 [bold blue]AutoApplier Status[/bold blue]\n")
    
    settings = get_settings()
    db = get_db()
    
    config_table = Table(title="Configuration Status")
    config_table.add_column("Item", style="cyan")
    config_table.add_column("Status", style="green")
    
    profile_path = Path("data/profile.json")
    if profile_path.exists():
        try:
            applicant = Applicant.from_file(profile_path)
            config_table.add_row("Profile", f"✅ Loaded ({applicant.full_name})")
        except Exception as e:
            config_table.add_row("Profile", f"⚠️ Error: {e}")
    else:
        config_table.add_row("Profile", "❌ Not found")
    
    resume_path = Path("data/resume.pdf")
    config_table.add_row("Resume", "✅ Found" if resume_path.exists() else "❌ Not found")
    config_table.add_row("Gemini API Key", "✅ Configured" if settings.gemini_api_key else "❌ Not set")
    
    notif_status = []
    if settings.discord_webhook_url:
        notif_status.append("Discord")
    if settings.telegram_bot_token:
        notif_status.append("Telegram")
    if settings.ntfy_topic:
        notif_status.append("ntfy")
    
    config_table.add_row("Notifications", f"✅ {', '.join(notif_status)}" if notif_status else "❌ None")
    console.print(config_table)
    
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
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    limit: int = typer.Option(50, "--limit", "-l"),
):
    console.print("\n🔍 [bold blue]Scraping Jobs...[/bold blue]\n")
    
    async def run_scrape():
        from src.scrapers.aggregator import JobAggregator
        
        aggregator = JobAggregator()
        
        if source and source.lower() != "all":
            console.print(f"Scraping from [cyan]{source}[/cyan]...")
            try:
                jobs = await aggregator.scrape_source(source, limit=limit)
                console.print(f"[green]✅ Found {len(jobs)} jobs from {source}[/green]")
                return {"jobs": jobs}
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                return None
        else:
            console.print("Scraping from all sources...")
            result = await aggregator.scrape_all(limit_per_source=limit)
            
            stats = result["stats"]
            console.print(f"\n[bold]Results:[/bold]")
            for src in stats["sources"]:
                if src.get("error"):
                    console.print(f"  ❌ {src['name']}: Error - {src['error']}")
                else:
                    console.print(f"  ✅ {src['name']}: {src['found']} jobs found")
            
            console.print(f"\n[green]Total: {stats['total_found']} found, {stats['total_new']} new[/green]")
            if stats["duplicates_removed"] > 0:
                console.print(f"[dim]Removed {stats['duplicates_removed']} duplicates[/dim]")
            
            return result
    
    try:
        asyncio.run(run_scrape())
    except Exception as e:
        console.print(f"[red]Scraping error: {e}[/red]")


@app.command()
def add_job(
    url: str = typer.Argument(...),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    company: Optional[str] = typer.Option(None, "--company", "-c"),
):
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
    job_id: Optional[str] = typer.Argument(None),
    limit: int = typer.Option(5, "--limit", "-l"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d"),
    no_scrape: bool = typer.Option(False, "--no-scrape"),
):
    mode = "[DRY RUN] " if dry_run else ""
    console.print(f"\n📝 {mode}[bold blue]AutoApplier Starting...[/bold blue]\n")
    
    if not Path("data/profile.json").exists():
        console.print("[red]❌ Profile not found! Run init first.[/red]")
        return
    
    async def run_apply():
        from src.orchestrator import run_auto_apply
        
        try:
            stats = await run_auto_apply(
                max_applications=limit,
                scrape_first=not no_scrape,
                dry_run=dry_run,
            )
            return stats
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            return None
    
    try:
        asyncio.run(run_apply())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user[/yellow]")


@app.command(name="apply-url")
def apply_url(
    url: str = typer.Argument(..., help="Direct URL to apply to"),
    visible: bool = typer.Option(True, "--visible/--headless", "-v/-h", help="Show browser window"),
):
    console.print(f"\n🚀 [bold blue]Apply-URL Mode[/bold blue]")
    console.print(f"Target: [cyan]{url}[/cyan]")
    console.print(f"Browser: {'Visible' if visible else 'Headless'}\n")
    
    settings = get_settings()
    settings.browser.headless = not visible
    
    async def run_single_application():
        import uuid
        from src.orchestrator import Orchestrator
        from src.core.job import Job, JobSource, JobStatus, ApplicationType
        from src.core.application import Application
        from src.classifiers.detector import detect_application_type
        
        profile_path = Path("data/profile.json")
        if not profile_path.exists():
            console.print("[red]❌ Profile not found![/red]")
            return

        applicant = Applicant.from_file(profile_path)
        orchestrator = Orchestrator(applicant)
        
        await orchestrator.setup()
        
        # Detect type
        app_type, confidence = detect_application_type(url)
        console.print(f"Detected Platform: [green]{app_type}[/green] ({confidence:.0%})")
        
        if app_type == ApplicationType.UNKNOWN:
            # Fallback check if it is greenhouse
            if "greenhouse.io" in url:
                app_type = ApplicationType.GREENHOUSE
            
        print(f"Using Filler: {app_type}")

        # Create transient job/app
        job = Job(
            id=str(uuid.uuid4()),
            url=url,
            title="Manual Application",
            company="Unknown",
            source=JobSource.OTHER,
            application_type=app_type,
            status=JobStatus.IN_PROGRESS
        )
        application = Application.from_job(job)
        
        filler_class = orchestrator.fillers.get(app_type)
        if not filler_class:
            console.print(f"[red]❌ No filler supported for {app_type}[/red]")
            await orchestrator.teardown()
            return

        success = await orchestrator._fill_application(job, application, filler_class)
        
        if success:
             console.print("[green]✅ AUTO-FILL SUCCESSFUL![/green]")
        else:
             console.print("[red]❌ Auto-fill failed/incomplete.[/red]")
        
        # Keep open if visible for a moment
        if visible:
            console.print("[yellow]Keeping browser open for 15s...[/yellow]")
            await asyncio.sleep(15)
            
        await orchestrator.teardown()

    try:
        asyncio.run(run_single_application())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user[/yellow]")


@app.command()
def jobs(
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    limit: int = typer.Option(20, "--limit", "-l"),
):
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
    settings = get_settings()
    console.print("\n⚙️ [bold blue]Configuration[/bold blue]\n")
    
    console.print(Panel.fit(
        f"[cyan]Job Titles:[/cyan] {', '.join(settings.search.titles)}\n"
        f"[cyan]Locations:[/cyan] {', '.join(settings.search.locations)}\n"
        f"[cyan]Experience:[/cyan] {', '.join(settings.search.experience_levels)}\n"
        f"[cyan]Max Days Old:[/cyan] {settings.search.max_days_old}",
        title="Search Preferences"
    ))
    
    console.print(Panel.fit(
        f"[cyan]Review Mode:[/cyan] {settings.application.review_mode}\n"
        f"[cyan]Max Per Run:[/cyan] {settings.application.max_per_run}\n"
        f"[cyan]Auto Submit:[/cyan] {settings.auto_submit}",
        title="Application Settings"
    ))


@app.command()
def version():
    from src import __version__
    console.print(f"\n🚀 AutoApplier v{__version__}\n")


@app.command(name="llm-usage")
def llm_usage():
    console.print("\n📊 [bold blue]LLM Usage Statistics[/bold blue]\n")
    
    settings = get_settings()
    
    if not settings.gemini_api_key:
        console.print("[red]❌ Gemini API key not configured[/red]")
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
        
        table.add_row("Daily Requests", str(stats["daily_requests"]), str(stats["daily_limit"]), str(stats["daily_remaining"]))
        table.add_row("Monthly Tokens", f"{stats['monthly_tokens']:,}", f"{stats['monthly_limit']:,}", f"{stats['monthly_remaining']:,}")
        
        console.print(table)
        
        daily_pct = stats["daily_requests"] / stats["daily_limit"] * 100
        monthly_pct = stats["monthly_tokens"] / stats["monthly_limit"] * 100
        
        if daily_pct > 80 or monthly_pct > 80:
            console.print("\n[yellow]⚠️ Approaching usage limits![/yellow]")
        else:
            console.print(f"\n[green]✅ Usage OK ({daily_pct:.1f}% daily, {monthly_pct:.1f}% monthly)[/green]")
            
    except Exception as e:
        console.print(f"[red]Error checking usage: {e}[/red]")


@app.command(name="test-llm")
def test_llm():
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
            console.print("[yellow]⚠️ No response received[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@app.command()
def dashboard(
    port: int = typer.Option(8080, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host"),
):
    console.print(f"\n🚀 [bold blue]Starting Dashboard...[/bold blue]\n")
    console.print(f"📊 Open: [cyan]http://{host}:{port}[/cyan]\n")
    
    try:
        from src.dashboard.app import run_dashboard
        run_dashboard(host=host, port=port)
    except ImportError:
        console.print("[red]Dashboard dependencies not installed.[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def scheduler(
    action: str = typer.Argument(...),
    interval: float = typer.Option(3.0, "--interval", "-i"),
):
    if action == "start":
        console.print(f"\n🚀 [bold blue]Starting Job Scheduler (every {interval}h)...[/bold blue]\n")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        async def run():
            from src.scheduler.scheduler import start_scheduler
            await start_scheduler(interval_hours=interval)
        
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            console.print("\n[yellow]Scheduler stopped[/yellow]")
    
    elif action == "run":
        console.print(f"\n🔍 [bold blue]Running single scrape...[/bold blue]\n")
        
        async def run_once():
            from src.scheduler.scheduler import run_scrape_once
            result = await run_scrape_once()
            return result
        
        try:
            asyncio.run(run_once())
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    elif action == "status":
        console.print(f"\n📊 [bold blue]Scheduler Status[/bold blue]\n")
        
        from src.scheduler.scheduler import get_scheduler
        sched = get_scheduler()
        stats = sched.get_stats()
        
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Running", "✅ Yes" if stats["running"] else "❌ No")
        table.add_row("Interval", f"{stats['interval_hours']}h")
        table.add_row("Total Runs", str(stats["run_count"]))
        table.add_row("Last Run", stats["last_run"] or "Never")
        table.add_row("Total Jobs Found", str(stats["total_jobs_found"]))
        table.add_row("Total New Jobs", str(stats["total_jobs_new"]))
        
        console.print(table)
    
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available: start, run, status")


@app.command(name="job-stats")
def job_stats():
    console.print("\n📊 [bold blue]Job Statistics[/bold blue]\n")
    
    db = get_db()
    stats = db.get_job_stats()
    
    table = Table(title="Database Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="yellow")
    
    table.add_row("Total Jobs", str(stats["total"]))
    table.add_row("Applied", str(stats["applied"]))
    table.add_row("Pending", str(stats["pending"]))
    table.add_row("Failed", str(stats["failed"]))
    
    console.print(table)
    
    from src.utils.database import JobModel
    from sqlalchemy import func
    
    with db.session() as session:
        by_source = session.query(
            JobModel.source, func.count(JobModel.id)
        ).group_by(JobModel.source).all()
        
        if by_source:
            source_table = Table(title="\nJobs by Source")
            source_table.add_column("Source", style="cyan")
            source_table.add_column("Count", style="yellow")
            
            for source, count in by_source:
                source_table.add_row(source or "Unknown", str(count))
            
            console.print(source_table)


@app.command()
def resume(
    variant: Optional[str] = typer.Option(None, "--variant", "-v", help="Resume variant from profile"),
    job_description: Optional[str] = typer.Option(None, "--jd", help="Job description text"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Job URL to fetch description"),
):
    console.print(f"\n📄 [bold blue]Generating Resume...[/bold blue]\n")
    
    from src.resume.generator import ResumeGenerator
    
    try:
        generator = ResumeGenerator()
        
        jd_text = job_description
        # TODO: If URL provided, fetch content (omitted for now to keep simple)
        
        pdf_path = generator.generate(variant=variant, job_description=jd_text)
        console.print(f"[green]✅ Resume generated: [bold]{pdf_path}[/bold][/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if "pdflatex" in str(e):
            console.print("[yellow]Tip: Install LaTeX with 'sudo apt install texlive-latex-base'[/yellow]")


@app.command(name="h1b-sponsors")
def h1b_sponsors(
    limit: int = typer.Option(50, "--limit", "-l"),
    tech_only: bool = typer.Option(True, "--tech-only", "-t"),
):
    console.print("\n🏢 [bold blue]H1B Sponsor Companies[/bold blue]\n")
    
    async def fetch():
        from src.scrapers.h1b_sponsors import get_h1b_scraper
        
        scraper = get_h1b_scraper()
        sponsors = await scraper.fetch_sponsors(limit=limit * 2)
        
        if tech_only:
            sponsors = scraper.get_tech_companies(min_filings=50)
        
        return sponsors[:limit]
    
    try:
        sponsors = asyncio.run(fetch())
        
        if not sponsors:
            console.print("[yellow]No sponsors found[/yellow]")
            return
        
        table = Table(title=f"Top {len(sponsors)} H1B Sponsors")
        table.add_column("#", style="dim")
        table.add_column("Company", style="cyan")
        table.add_column("H1B Filings", style="yellow")
        table.add_column("Avg Salary", style="green")
        table.add_column("Careers URL", style="blue")
        
        for i, sponsor in enumerate(sponsors, 1):
            salary = f"${sponsor.avg_salary:,}" if sponsor.avg_salary else "-"
            careers = "✅" if sponsor.careers_url else "-"
            table.add_row(str(i), sponsor.name, str(sponsor.h1b_filings), salary, careers)
        
        console.print(table)
        
        with_urls = [s for s in sponsors if s.careers_url]
        console.print(f"\n[green]✅ {len(with_urls)}/{len(sponsors)} companies have careers URLs mapped[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def main():
    app()


if __name__ == "__main__":
    main()
