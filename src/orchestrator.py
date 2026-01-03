"""
Orchestrator - The main automation engine for AutoApplier

This ties everything together:
1. Scrapes jobs from configured sources
2. Classifies application types
3. Fills out forms automatically
4. Uses LLM for complex questions
5. Notifies you when input is needed
6. Tracks all applications
"""

import asyncio
import random
from datetime import datetime
from typing import Optional
from pathlib import Path

from src.core.job import Job, JobStatus, ApplicationType
from src.core.applicant import Applicant
from src.core.application import Application, ApplicationStatus
from src.utils.config import get_settings
from src.utils.database import get_db
from src.utils.browser import BrowserManager, browser_session
from src.classifiers.detector import detect_application_type
from src.fillers.base_filler import BaseFiller
from src.fillers.greenhouse_filler import GreenhouseFiller
from src.fillers.lever_filler import LeverFiller
from src.llm.gemini import GeminiClient
from src.notifier.ntfy import NtfyNotifier
from src.scrapers.aggregator import JobAggregator


class Orchestrator:
    """
    Main orchestrator that runs the job application automation.
    """
    
    def __init__(self, applicant: Applicant):
        self.settings = get_settings()
        self.db = get_db()
        self.applicant = applicant
        
        # Initialize components
        self.browser_manager: Optional[BrowserManager] = None
        self.llm_client: Optional[GeminiClient] = None
        self.notifier: Optional[NtfyNotifier] = None
        self.aggregator = JobAggregator()
        
        # Stats
        self.stats = {
            "jobs_processed": 0,
            "applications_submitted": 0,
            "applications_failed": 0,
            "needs_review": 0,
            "start_time": None,
        }
        
        # Filler registry
        self.fillers: dict[ApplicationType, type[BaseFiller]] = {
            ApplicationType.GREENHOUSE: GreenhouseFiller,
            ApplicationType.LEVER: LeverFiller,
            # Add more fillers as they're implemented
        }
    
    async def setup(self) -> None:
        """Initialize all components"""
        print("🚀 Setting up AutoApplier...")
        
        # Setup LLM
        if self.settings.gemini_api_key:
            try:
                self.llm_client = GeminiClient()
                print("  ✅ LLM connected")
            except Exception as e:
                print(f"  ⚠️ LLM not available: {e}")
        
        # Setup notifier
        try:
            self.notifier = NtfyNotifier()
            print(f"  ✅ Notifications enabled ({self.notifier.topic})")
        except Exception as e:
            print(f"  ⚠️ Notifications not available: {e}")
        
        # Setup browser
        self.browser_manager = BrowserManager()
        print("  ✅ Browser ready")
    
    async def teardown(self) -> None:
        """Cleanup resources"""
        if self.browser_manager:
            await self.browser_manager.stop()
    
    async def run(
        self,
        scrape_first: bool = True,
        max_applications: int = None,
        dry_run: bool = False,
    ) -> dict:
        """
        Run the main automation loop.
        
        Args:
            scrape_first: Whether to scrape for new jobs first
            max_applications: Max applications to submit
            dry_run: If True, don't actually submit
        
        Returns:
            Stats dictionary
        """
        self.stats["start_time"] = datetime.now()
        max_applications = max_applications or self.settings.application.max_per_run
        
        await self.setup()
        
        try:
            # Step 1: Scrape new jobs
            if scrape_first:
                await self._scrape_jobs()
            
            # Step 2: Get pending jobs
            pending_jobs = self.db.get_pending_jobs(max_applications * 2)
            print(f"\n📋 Found {len(pending_jobs)} pending jobs")
            
            if not pending_jobs:
                print("No jobs to apply to!")
                return self.stats
            
            # Step 3: Process each job
            for job in pending_jobs:
                if self.stats["applications_submitted"] >= max_applications:
                    print(f"\n⏹️ Reached max applications ({max_applications})")
                    break
                
                await self._process_job(job, dry_run)
                
                # Random delay between applications
                await self._random_delay()
            
            # Step 4: Send summary notification
            if self.notifier:
                await self.notifier.notify_daily_summary(
                    applied=self.stats["applications_submitted"],
                    pending=len(pending_jobs) - self.stats["jobs_processed"],
                    failed=self.stats["applications_failed"],
                    needs_review=self.stats["needs_review"],
                )
            
        finally:
            await self.teardown()
        
        self._print_summary()
        return self.stats
    
    async def _scrape_jobs(self) -> None:
        """Scrape new jobs from all sources"""
        print("\n🔍 Scraping for new jobs...")
        
        try:
            result = await self.aggregator.scrape_all(
                limit_per_source=self.settings.application.max_per_run * 2
            )
            stats = result["stats"]
            print(f"  Found {stats['total_found']} jobs, {stats['total_new']} new")
        except Exception as e:
            print(f"  ⚠️ Scraping error: {e}")
    
    async def _process_job(self, job: Job, dry_run: bool) -> None:
        """Process a single job application"""
        print(f"\n{'='*60}")
        print(f"📝 Processing: {job.title} at {job.company}")
        print(f"   URL: {job.url}")
        
        self.stats["jobs_processed"] += 1
        
        # Detect application type if not set
        if job.application_type == ApplicationType.UNKNOWN:
            app_type, confidence = detect_application_type(job.url)
            job.application_type = app_type
            self.db.update_job_status(job.id, job.status)
            print(f"   Platform: {app_type} (confidence: {confidence:.0%})")
        else:
            print(f"   Platform: {job.application_type}")
        
        # Check if we have a filler for this type
        filler_class = self.fillers.get(job.application_type)
        
        if not filler_class:
            print(f"   ⚠️ No filler for {job.application_type} - needs manual application")
            job.status = JobStatus.NEEDS_REVIEW
            self.db.update_job_status(job.id, JobStatus.NEEDS_REVIEW)
            self.stats["needs_review"] += 1
            
            if self.notifier:
                await self.notifier.notify_needs_review(
                    job_title=job.title,
                    company=job.company,
                    reason=f"No auto-filler for {job.application_type}",
                    url=job.url,
                )
            return
        
        # Create application record
        application = Application.from_job(job)
        self.db.add_application(application)
        
        if dry_run:
            print("   🏃 [DRY RUN] Would apply here")
            return
        
        # Try to fill the application
        try:
            success = await self._fill_application(job, application, filler_class)
            
            if success:
                print("   ✅ Application prepared successfully!")
                
                # Check if review mode
                if self.settings.application.review_mode:
                    print("   ⏸️ Review mode: pausing before submit")
                    job.status = JobStatus.NEEDS_REVIEW
                    self.db.update_job_status(job.id, JobStatus.NEEDS_REVIEW)
                    self.stats["needs_review"] += 1
                    
                    if self.notifier:
                        await self.notifier.notify_needs_review(
                            job_title=job.title,
                            company=job.company,
                            reason="Review mode - check before submitting",
                            url=job.url,
                        )
                else:
                    # Auto-submit if enabled
                    job.status = JobStatus.APPLIED
                    job.applied_at = datetime.now()
                    self.db.update_job_status(job.id, JobStatus.APPLIED)
                    self.stats["applications_submitted"] += 1
                    
                    if self.notifier:
                        await self.notifier.notify_completed(
                            job_title=job.title,
                            company=job.company,
                            url=job.url,
                        )
            else:
                print("   ❌ Application needs review")
                job.status = JobStatus.NEEDS_REVIEW
                self.db.update_job_status(job.id, JobStatus.NEEDS_REVIEW)
                self.stats["needs_review"] += 1
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            job.status = JobStatus.FAILED
            self.db.update_job_status(job.id, JobStatus.FAILED)
            self.stats["applications_failed"] += 1
            
            if self.notifier:
                await self.notifier.notify_failed(
                    job_title=job.title,
                    company=job.company,
                    error=str(e),
                )
    
    async def _fill_application(
        self,
        job: Job,
        application: Application,
        filler_class: type[BaseFiller],
    ) -> bool:
        """Fill out an application form"""
        # Start browser
        await self.browser_manager.start()
        page = await self.browser_manager.new_page()
        
        try:
            # Navigate to job page
            print(f"   🌐 Opening application page...")
            await page.goto(job.apply_url or job.url, wait_until="networkidle")
            
            # Take screenshot
            screenshot_path = await self.browser_manager.take_screenshot(
                page, f"job_{job.id[:8]}_start"
            )
            application.screenshots.append(screenshot_path)
            
            # Initialize filler
            filler = filler_class(
                applicant=self.applicant,
                llm_client=self.llm_client,
            )
            
            # Check if filler can handle this page
            if not await filler.can_handle(page):
                print(f"   ⚠️ Filler can't handle this page")
                return False
            
            # Fill the form
            print(f"   ✏️ Filling form...")
            success = await filler.fill(page, job, application)
            
            # Take final screenshot
            screenshot_path = await self.browser_manager.take_screenshot(
                page, f"job_{job.id[:8]}_filled"
            )
            application.screenshots.append(screenshot_path)
            
            # Update application in DB
            self.db.update_application(application)
            
            return success
            
        except Exception as e:
            print(f"   ❌ Fill error: {e}")
            application.fail(str(e))
            self.db.update_application(application)
            return False
        
        finally:
            await page.close()
    
    async def _random_delay(self) -> None:
        """Add a random delay between applications"""
        min_delay = self.settings.application.delay.min
        max_delay = self.settings.application.delay.max
        
        delay = random.uniform(min_delay, max_delay)
        print(f"\n⏳ Waiting {delay:.0f}s before next application...")
        await asyncio.sleep(delay)
    
    def _print_summary(self) -> None:
        """Print final summary"""
        duration = datetime.now() - self.stats["start_time"]
        
        print("\n" + "="*60)
        print("📊 SESSION SUMMARY")
        print("="*60)
        print(f"  Duration: {duration}")
        print(f"  Jobs Processed: {self.stats['jobs_processed']}")
        print(f"  Applications Submitted: {self.stats['applications_submitted']}")
        print(f"  Needs Review: {self.stats['needs_review']}")
        print(f"  Failed: {self.stats['applications_failed']}")
        print("="*60)


async def run_auto_apply(
    max_applications: int = 5,
    scrape_first: bool = True,
    dry_run: bool = False,
) -> dict:
    """
    Convenience function to run auto-apply.
    
    Args:
        max_applications: Max number of applications to submit
        scrape_first: Whether to scrape for new jobs first
        dry_run: If True, don't actually submit
    
    Returns:
        Session stats
    """
    settings = get_settings()
    
    # Load applicant profile
    profile_path = Path("data/profile.json")
    if not profile_path.exists():
        raise FileNotFoundError(
            "Profile not found! Run 'python main.py init' and edit data/profile.json"
        )
    
    applicant = Applicant.from_file(profile_path)
    print(f"👤 Loaded profile: {applicant.full_name}")
    
    # Create and run orchestrator
    orchestrator = Orchestrator(applicant)
    return await orchestrator.run(
        scrape_first=scrape_first,
        max_applications=max_applications,
        dry_run=dry_run,
    )
