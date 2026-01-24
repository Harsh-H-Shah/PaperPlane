from playwright.async_api import Page
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller
from src.utils.logger import logger

class RedirectFiller(BaseFiller):
    """
    Specialized filler for 'Landing Pages' (BuiltIn, JobRight, etc.)
    that only require clicking an 'Apply' button to redirect to the actual form.
    """
    PLATFORM_NAME = "Redirector"

    async def can_handle(self, page: Page) -> bool:
        # This is usually called explicitly by Orchestrator for known landing sites
        return True

    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        logger.info(f"   🔍 Handling landing page for {job.company}...")
        
        # 1. Try to find the primary "Apply" button
        # Aggressive list of selectors for aggregator apply buttons
        selectors = [
            "button:has-text('Apply on company site')",
            "a:has-text('Apply on company site')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply Now')",
            "button:has-text('Apply')",
            "a[href*='apply']",
            "a[href*='application']",
            ".apply-button",
            "#apply-button"
        ]
        
        found_button = False
        for selector in selectors:
            btn = page.locator(selector).first
            if await btn.count() > 0 and await btn.is_visible():
                logger.info(f"   🖱️ Found redirect button: '{selector}'")
                try:
                    # BuiltIn often opens in new tab, but Playwright follows redirects well
                    # We might need to handle popup if it opens new window
                    await btn.click()
                    found_button = True
                    break
                except Exception as e:
                    logger.warning(f"   ⚠️ Failed to click '{selector}': {e}")

        if not found_button:
            # Fallback to general button heuristic
            logger.info("   ℹ️ No specific redirect button found, trying general heuristic...")
            found_button = await self._find_and_click_aggregator_button(page)

        if found_button:
            # Wait for navigation or popup
            await page.wait_for_load_state("networkidle", timeout=5000)
            logger.info("   ✅ Redirect initiated")
            return True
        
        logger.warning("   ❌ Could not find redirect button on landing page")
        return False

    async def _find_and_click_aggregator_button(self, page: Page) -> bool:
        buttons = await page.locator("button, a.btn, .button, [role='button']").all()
        
        candidate = None
        candidate_score = 0
        
        for btn in buttons:
            try:
                if not await btn.is_visible():
                    continue
                    
                text = (await btn.text_content() or await btn.get_attribute("value") or "").lower().strip()
                
                score = 0
                if "apply on company" in text:
                    score = 100
                elif "apply now" in text:
                    score = 80
                elif "apply" in text:
                    score = 50
                
                # BuiltIn specific
                if "on company site" in text:
                    score += 20

                if score > candidate_score:
                    candidate = btn
                    candidate_score = score
            except: continue
        
        if candidate and candidate_score > 0:
            logger.info(f"   🎯 Highest scoring redirect button: '{await candidate.text_content()}' ({candidate_score})")
            await candidate.click()
            return True
            
        return False
