import asyncio
import random
from datetime import datetime
from typing import Optional
from pathlib import Path

from src.core.job import Job, JobStatus, ApplicationType, JobSource
from src.core.applicant import Applicant
from src.core.application import Application, ApplicationStatus
from src.utils.config import get_settings
from src.utils.database import get_db
from src.utils.browser import BrowserManager, browser_session
from src.classifiers.detector import detect_application_type
from src.fillers.base_filler import BaseFiller
from src.fillers.greenhouse_filler import GreenhouseFiller
from src.fillers.lever_filler import LeverFiller
from src.fillers.workday_filler import WorkdayFiller
from src.fillers.ashby_filler import AshbyFiller
from src.llm.gemini import GeminiClient
from src.notifier.ntfy import NtfyNotifier
from src.scrapers.aggregator import JobAggregator
from src.fillers.universal_filler import UniversalFiller
from src.fillers.redirect_filler import RedirectFiller
from src.utils.logger import logger

class Orchestrator:
    def __init__(self, applicant: Applicant):
        self.settings = get_settings()
        self.db = get_db()
        self.applicant = applicant
        self.browser_manager: Optional[BrowserManager] = None
        self.llm_client: Optional[GeminiClient] = None
        self.notifier: Optional[NtfyNotifier] = None
        self.aggregator = JobAggregator()
        self.stats = {
            "jobs_processed": 0,
            "applications_submitted": 0,
            "applications_failed": 0,
            "needs_review": 0,
            "start_time": None,
        }
        self.fillers: dict[ApplicationType, type[BaseFiller]] = {
            ApplicationType.GREENHOUSE: GreenhouseFiller,
            ApplicationType.LEVER: LeverFiller,
            ApplicationType.WORKDAY: WorkdayFiller,
            ApplicationType.ASHBY: AshbyFiller,
            ApplicationType.BUILTIN: RedirectFiller,
            ApplicationType.REDIRECTOR: RedirectFiller,
        }
    
    async def setup(self) -> None:
        logger.info("🚀 Setting up AutoApplier...")
        
        if self.settings.gemini_api_key:
            try:
                self.llm_client = GeminiClient()
                logger.info("  ✅ LLM connected")
            except Exception as e:
                logger.warning(f"  ⚠️ LLM not available: {e}")
        
        try:
            self.notifier = NtfyNotifier()
            logger.info(f"  ✅ Notifications enabled ({self.notifier.topic})")
        except Exception as e:
            logger.warning(f"  ⚠️ Notifications not available: {e}")
        
        self.browser_manager = BrowserManager()
        logger.info("  ✅ Browser ready")
    
    async def teardown(self) -> None:
        if self.browser_manager:
            await self.browser_manager.stop()
    
    async def run(self, scrape_first: bool = True, max_applications: int = None, dry_run: bool = False, filter_type: Optional[ApplicationType] = None) -> dict:
        self.stats["start_time"] = datetime.now()
        max_applications = max_applications or self.settings.application.max_per_run
        
        await self.setup()
        
        try:
            if scrape_first:
                await self._scrape_jobs()
            
            pending_jobs = self.db.get_pending_jobs(max_applications * 5) # Get more candidates since we are filtering
            logger.info(f"\n📋 Found {len(pending_jobs)} pending jobs")
            
            if not pending_jobs:
                logger.info("No jobs to apply to!")
                return self.stats
            
            processed_count = 0
            for job in pending_jobs:
                if self.stats["applications_submitted"] >= max_applications:
                    logger.info(f"\n⏹️ Reached max applications ({max_applications})")
                    break
                
                # Pre-filter check if we already know the type
                if filter_type and job.application_type != ApplicationType.UNKNOWN and job.application_type != filter_type:
                     continue

                await self._process_job(job, dry_run, filter_type)
                
                if self.stats["jobs_processed"] > processed_count:
                    processed_count = self.stats["jobs_processed"]
                    await self._random_delay()
            
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
        logger.info("\n🔍 Scraping for new jobs...")
        try:
            result = await self.aggregator.scrape_all(limit_per_source=self.settings.application.max_per_run * 2)
            stats = result["stats"]
            logger.info(f"  Found {stats['total_found']} jobs, {stats['total_new']} new")
        except Exception as e:
            logger.error(f"  ⚠️ Scraping error: {e}")
    
    async def _process_job(self, job: Job, dry_run: bool, filter_type: Optional[ApplicationType] = None) -> None:
        logger.info(f"\n{'='*60}")
        logger.info(f"📝 Processing: {job.title} at {job.company}")
        logger.info(f"   URL: {job.url}")
        
        if job.application_type == ApplicationType.UNKNOWN:
            app_type, confidence = detect_application_type(job.url)
            job.application_type = app_type
            self.db.update_job_status(job.id, job.status)
            logger.info(f"   Platform: {app_type} (confidence: {confidence:.0%})")
        else:
            logger.info(f"   Platform: {job.application_type}")
            
        # Filter check post-detection
        if filter_type and job.application_type != filter_type:
            logger.info(f"   ⏭️ Skipping (Not {filter_type})")
            job.status = JobStatus.NEEDS_REVIEW
            self.db.update_job_status(job.id, JobStatus.NEEDS_REVIEW)
            self.stats["needs_review"] += 1
            return

        self.stats["jobs_processed"] += 1
        
        # Robust filler selection (handle string vs Enum)
        app_type = job.application_type
        if isinstance(app_type, str):
            try:
                app_type = ApplicationType(app_type)
            except:
                pass
                
        filler_class = self.fillers.get(app_type)
        
        if not filler_class:
            logger.info(f"   ⚠️ No specific filler for {app_type} - using UniversalFiller")
            filler_class = UniversalFiller
        else:
            logger.info(f"   🎯 Using specialized filler: {filler_class.__name__}")
        
        application = Application.from_job(job)
        self.db.add_application(application)
        
        if dry_run:
            logger.info("   🏃 [DRY RUN] Would apply here")
            return
        
        try:
            success = await self._fill_application(job, application, filler_class)
            
            if success:
                logger.info("   ✅ Application prepared successfully!")
                
                if self.settings.application.review_mode:
                    logger.info("   ⏸️ Review mode: pausing before submit")
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
                    job.status = JobStatus.APPLIED
                    job.applied_at = datetime.now()
                    self.db.update_job_status(job.id, JobStatus.APPLIED)
                    self.stats["applications_submitted"] += 1
                    logger.info("   🚀 Application Submitted!")
                    
                    if self.notifier:
                        await self.notifier.notify_completed(
                            job_title=job.title,
                            company=job.company,
                            url=job.url,
                        )
            else:
                logger.warning("   ❌ Application needs review")
                job.status = JobStatus.NEEDS_REVIEW
                self.db.update_job_status(job.id, JobStatus.NEEDS_REVIEW)
                self.stats["needs_review"] += 1
                
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            job.status = JobStatus.FAILED
            self.db.update_job_status(job.id, JobStatus.FAILED)
            self.stats["applications_failed"] += 1
            
            if self.notifier:
                await self.notifier.notify_failed(
                    job_title=job.title,
                    company=job.company,
                    error=str(e),
                )
    
    async def _fill_application(self, job: Job, application: Application, filler_class: type[BaseFiller]) -> bool:
        try:
            await self.browser_manager.start()
            
            # Add BuiltIn cookies if this is a BuiltIn job
            if job.source == JobSource.BUILTIN or "builtin.com" in (job.url or ""):
                await self.browser_manager.add_builtin_cookies()
            
            page = await self.browser_manager.new_page()

            logger.info(f"   🌐 Opening application page...")
            try:
                response = await page.goto(job.apply_url or job.url, wait_until="domcontentloaded", timeout=30000)
                if response and (response.status == 404 or response.status >= 500):
                    logger.error(f"   ❌ Page loaded with status {response.status}")
                    job.status = JobStatus.EXPIRED
                    self.db.update_job_status(job.id, JobStatus.EXPIRED)
                    return False
            except Exception as e:
                error_str = str(e).lower()
                if "err_name_not_resolved" in error_str or "err_connection_refused" in error_str or "timeout" in error_str:
                    logger.error(f"   ❌ Network/Page error: {e}")
                    job.status = JobStatus.EXPIRED
                    self.db.update_job_status(job.id, JobStatus.EXPIRED)
                    return False
                raise e
            
            # Wait a bit for redirects
            await page.wait_for_timeout(2000)
            
            # --- Landing Page / Redirect Loop ---
            # Some sites (BuiltIn, JobRight) require a click before reaching the form.
            # We allow up to 2 "hops" before giving up on specialized fillers.
            
            for hop in range(2):
                content = await page.content()
                current_url = page.url
                new_type, reliability = detect_application_type(current_url, content)
                
                # If we detected a REDIRECTOR (like BuiltIn), use RedirectFiller to click through
                if new_type in [ApplicationType.BUILTIN, ApplicationType.REDIRECTOR]:
                    logger.info(f"   ⚓ Landing page detected: {new_type}. Attempting redirect click... (Hop {hop+1})")
                    redirector = RedirectFiller(applicant=self.applicant, llm_client=self.llm_client)
                    
                    try:
                        # BuiltIn often opens in a new tab. We need to handle both cases.
                        async with page.context.expect_page(timeout=5000) as new_page_info:
                             if await redirector.fill(page, job, application):
                                  logger.info("   ✅ Redirect logic executed, waiting for new page...")
                        
                        # Await the coroutine to get the actual page
                        try:
                            new_p = await new_page_info.value
                            if new_p:
                                 logger.info("   📑 New tab detected! Switching focus to redirected form.")
                                 page = new_p
                                 await page.bring_to_front()
                                 await page.wait_for_load_state("networkidle", timeout=10000)
                            else:
                                 # Same tab navigation
                                 await page.wait_for_timeout(3000)
                                 await page.wait_for_load_state("networkidle", timeout=10000)
                        except Exception as e:
                             # No new page, maybe same tab?
                             await page.wait_for_timeout(3000)
                        
                        continue # Re-detect on the next hop (or final form)
                    except Exception as e:
                         # Fallback if no new page opens or click fails
                         logger.warning(f"   ℹ️ Redirect navigation check ended: {e}")
                         await page.wait_for_timeout(2000)
                         continue
                
                # If we've reached a terminal platform, break the loop
                if new_type != ApplicationType.BUILTIN and new_type != ApplicationType.REDIRECTOR:
                    if new_type != job.application_type and reliability > 0.6:
                         logger.info(f"   🔄 Platform refined: {job.application_type} -> {new_type} (reliability: {reliability:.0%})")
                         job.application_type = new_type
                    break
            
            # --- Final Filler Selection ---
            app_type = job.application_type
            if isinstance(app_type, str):
                try: app_type = ApplicationType(app_type)
                except: pass
                
            filler_class = self.fillers.get(app_type, UniversalFiller)
            
            if filler_class == RedirectFiller:
                 # If we are still on a redirector after 2 hops, fallback to universal
                 logger.info("   ⚠️ Still on landing page after hops, falling back to UniversalFiller")
                 filler_class = UniversalFiller
            
            logger.info(f"   🎯 Strategy selected: {filler_class.__name__}")
            filler = filler_class(applicant=self.applicant, llm_client=self.llm_client)
            
            if not await filler.can_handle(page):
                logger.warning(f"   ⚠️ Filler can't handle this page")
                return False
            
            logger.info(f"   ✏️ Filling form...")
            success = await filler.fill(page, job, application)
            
            screenshot_path = await self.browser_manager.take_screenshot(page, f"job_{job.id[:8]}_filled")
            application.screenshots.append(screenshot_path)
            
            self.db.update_application(application)
            return success
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"   ❌ Fill error: {e}")
            application.fail(str(e))
            self.db.update_application(application)
            return False
        
        finally:
            if 'page' in locals() and page:
                await page.close()
    
    async def _random_delay(self) -> None:
        min_delay = self.settings.application.delay.min
        max_delay = self.settings.application.delay.max
        delay = random.uniform(min_delay, max_delay)
        logger.info(f"\n⏳ Waiting {delay:.0f}s before next application...")
        await asyncio.sleep(delay)
    
    def _print_summary(self) -> None:
        duration = datetime.now() - self.stats["start_time"]
        logger.info("\n" + "="*60)
        logger.info("📊 SESSION SUMMARY")
        logger.info("="*60)
        logger.info(f"  Duration: {duration}")
        logger.info(f"  Jobs Processed: {self.stats['jobs_processed']}")
        logger.info(f"  Applications Submitted: {self.stats['applications_submitted']}")
        logger.info(f"  Needs Review: {self.stats['needs_review']}")
        logger.info(f"  Failed: {self.stats['applications_failed']}")
        logger.info("="*60)

async def run_auto_apply(max_applications: int = 5, scrape_first: bool = True, dry_run: bool = False, filter_type: Optional[ApplicationType] = None) -> dict:
    settings = get_settings()
    
    profile_path = Path("data/profile.json")
    
    # Try finding it in parent directories if not found in CWD
    if not profile_path.exists():
        # Check parent directories (up to 3 levels)
        current = Path.cwd()
        for _ in range(3):
            candidate = current / "data/profile.json"
            if candidate.exists():
                profile_path = candidate
                break
            current = current.parent

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found! CWD: {Path.cwd()}. Run 'python main.py init' and edit data/profile.json")
    
    applicant = Applicant.from_file(profile_path)
    logger.info(f"👤 Loaded profile: {applicant.full_name}")
    
    orchestrator = Orchestrator(applicant)
    return await orchestrator.run(
        scrape_first=scrape_first,
        max_applications=max_applications,
        dry_run=dry_run,
        filter_type=filter_type
    )
