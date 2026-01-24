from playwright.async_api import Page
from src.fillers.universal_filler import UniversalFiller
from src.core.job import Job
from src.core.application import Application
from src.utils.logger import logger
import asyncio

class WorkdayFiller(UniversalFiller):
    PLATFORM_NAME = "Workday"
    
    async def can_handle(self, page: Page) -> bool:
        url = page.url.lower()
        content = await page.content()
        return "myworkdayjobs.com" in url or "workday" in content.lower()

    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        """
        Workday specific flow:
        1. Find and click 'Apply' (handling various layouts)
        2. Handle 'Autofill with Resume', 'Apply Manually', or 'Use My Last Application'
        3. Fallback to Universal Filler logic for the actual form
        """
        application.start()
        logger.info("   🏢 Handling Workday application")

        try:
            await self.wait_for_page_load(page)
            
            # Step 1: Click Initial Apply Button
            # Workday often presents an "Apply" button, then a choice of how to apply
            if await self._handle_initial_navigation(page, application):
                 logger.info("   🖱️ Initial navigation pass complete")
            else:
                 logger.warning("   ⚠️ Could not navigate initial Workday screens - attempting form fill anyway")

            # Continue with universal logic which is good at finding inputs
            return await super().fill(page, job, application)

        except Exception as e:
            logger.error(f"   ❌ Workday filler error: {e}")
            application.fail(f"Workday filler error: {str(e)}")
            return False

    async def _handle_initial_navigation(self, page: Page, application: Application) -> bool:
        """
        Handles the "Apply" -> "Apply Manually" / "Autofill" sequence
        """
        # 1. Look for the main Apply button
        # Standard Workday uses data-automation-id="applyButton"
        apply_btn = page.locator('[data-automation-id="applyButton"]')
        
        if await apply_btn.count() > 0:
            logger.info("   🖱️ Clicking Workday Apply button")
            await apply_btn.first.click()
            await self.wait_for_page_load(page)
            await asyncio.sleep(2)
        else:
            # Maybe standard button
            logger.info("   ℹ️ Standard Workday apply button not found, searching variants...")
            # Try finding text "Apply"
            found = False
            for selector in ["a:has-text('Apply')", "button:has-text('Apply')"]:
                if await page.locator(selector).count() > 0:
                     await page.locator(selector).first.click()
                     found = True
                     await self.wait_for_page_load(page)
                     break
            if not found:
                logger.info("   ℹ️ No Apply button found (might be already on form)")

        # 2. Check for "Apply Manually" vs "Autofill with Resume" vs "Use Last Application"
        # We prefer "Apply Manually" to let our filler handle it, or "Autofill with Resume" if we had a resume uploader
        # Let's try "Apply Manually" first as it's most reliable for DOM analysis
        
        apply_manually = page.locator('[data-automation-id="applyManually"]')
        if await apply_manually.count() > 0:
            logger.info("   🖱️ Selecting 'Apply Manually'")
            await apply_manually.click()
            await self.wait_for_page_load(page)
            return True

        # "Use My Last Application" might appear for returning users
        use_last = page.locator('[data-automation-id="useMyLastApplication"]')
        if await use_last.count() > 0:
             logger.info("   🖱️ Selecting 'Use My Last Application'")
             await use_last.click()
             await self.wait_for_page_load(page)
             return True
             
        # Login Screen Detection
        # If we see username/password fields, we might be stuck unless we have creds
        # UniversalFiller will try to fill them if they exist
        
        return True
