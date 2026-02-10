from playwright.async_api import Page
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller
from src.utils.logger import logger
from src.utils.config import get_settings

class RedirectFiller(BaseFiller):
    """
    Specialized filler for 'Landing Pages' (BuiltIn, JobRight, etc.)
    that only require clicking an 'Apply' button to redirect to the actual form.
    """
    PLATFORM_NAME = "Redirector"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._settings = get_settings()

    async def can_handle(self, page: Page) -> bool:
        # This is usually called explicitly by Orchestrator for known landing sites
        return True
    
    async def _check_builtin_login_required(self, page: Page) -> bool:
        """Check if BuiltIn is showing a login prompt"""
        content = await page.content()
        login_indicators = [
            "sign in to apply",
            "log in to apply", 
            "create an account",
            "sign up to apply",
            "/users/sign_in",
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in login_indicators)
    
    async def _add_builtin_cookies_if_available(self, page: Page) -> bool:
        """Add BuiltIn cookies to the browser context if configured"""
        cookies = []
        
        # Add SSESS session cookie
        if self._settings.builtin_session and self._settings.builtin_session_name:
            cookies.append({
                "name": self._settings.builtin_session_name,
                "value": self._settings.builtin_session,
                "domain": ".builtin.com",
                "path": "/",
            })
        
        # Add BIX_AUTH cookies
        if self._settings.builtin_bix_auth:
            cookies.append({
                "name": "BIX_AUTH",
                "value": self._settings.builtin_bix_auth,
                "domain": ".builtin.com",
                "path": "/",
            })
        
        if self._settings.builtin_bix_authc1:
            cookies.append({
                "name": "BIX_AUTHC1",
                "value": self._settings.builtin_bix_authc1,
                "domain": ".builtin.com",
                "path": "/",
            })
        
        if self._settings.builtin_bix_authc2:
            cookies.append({
                "name": "BIX_AUTHC2",
                "value": self._settings.builtin_bix_authc2,
                "domain": ".builtin.com",
                "path": "/",
            })
        
        if not cookies:
            return False
        
        try:
            await page.context.add_cookies(cookies)
            logger.info(f"   🍪 Added {len(cookies)} BuiltIn cookies")
            return True
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to add BuiltIn cookies: {e}")
            return False

    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        logger.info(f"   🔍 Handling landing page for {job.company}...")
        
        # Check if this is a BuiltIn page that needs authentication
        current_url = page.url
        is_builtin = "builtin.com" in current_url
        
        if is_builtin:
            # Check if we already have the real apply URL
            if job.apply_url and job.apply_url != job.url:
                if "builtin.com" not in job.apply_url:
                    logger.info(f"   🎯 Using pre-fetched apply URL: {job.apply_url[:60]}...")
                    # Navigate directly to the real apply URL
                    await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)
                    return True
            
            # Check if login is required
            if await self._check_builtin_login_required(page):
                logger.info("   🔐 BuiltIn requires login...")
                
                # Try to add cookies and reload
                if await self._add_builtin_cookies_if_available(page):
                    await page.reload(wait_until="domcontentloaded")
                    await page.wait_for_timeout(2000)
                    
                    # Check if we're now logged in
                    if await self._check_builtin_login_required(page):
                        logger.warning("   ❌ BuiltIn login failed - cookies may be expired. Update BUILTIN_SESSION in .env")
                        return False
                    logger.info("   ✅ BuiltIn login successful via cookies")
                else:
                    logger.warning("   ❌ BuiltIn requires login but no session cookies configured. Set BUILTIN_SESSION in .env")
                    return False
        
        # 1. Try to find the primary "Apply" button
        # Aggressive list of selectors for aggregator apply buttons
        selectors = [
            "a[data-id='apply-button']",  # BuiltIn specific
            "button[data-id='apply-button']",
            "a:has-text('Apply on company site')",
            "button:has-text('Apply on company site')",
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply')",
            "button:has-text('Apply')",
            "a[href*='/redirect']",  # BuiltIn redirect links
            "a[href*='apply']",
            "a[href*='application']",
            ".apply-button",
            "#apply-button"
        ]
        
        found_button = False
        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    logger.info(f"   🖱️ Found redirect button: '{selector}'")
                    try:
                        # BuiltIn often opens in new tab
                        await btn.click()
                        found_button = True
                        break
                    except Exception as e:
                        logger.warning(f"   ⚠️ Failed to click '{selector}': {e}")
            except Exception:
                continue

        if not found_button:
            # Fallback to general button heuristic
            logger.info("   ℹ️ No specific redirect button found, trying general heuristic...")
            found_button = await self._find_and_click_aggregator_button(page)

        if found_button:
            # Wait for navigation or popup
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # Timeout is OK, page might still be usable
            logger.info("   ✅ Redirect initiated")
            return True
        
        logger.warning("   ❌ Could not find redirect button on landing page")
        return False

    async def _find_and_click_aggregator_button(self, page: Page) -> bool:
        buttons = await page.locator("button, a.btn, .button, [role='button'], a[class*='apply']").all()
        
        candidate = None
        candidate_score = 0
        
        for btn in buttons:
            try:
                if not await btn.is_visible():
                    continue
                    
                text = (await btn.text_content() or await btn.get_attribute("value") or "").lower().strip()
                href = (await btn.get_attribute("href") or "").lower()
                
                score = 0
                if "apply on company" in text:
                    score = 100
                elif "apply now" in text:
                    score = 80
                elif "apply" in text and len(text) < 30:  # Avoid long strings that happen to contain "apply"
                    score = 50
                
                # BuiltIn specific
                if "on company site" in text:
                    score += 20
                    
                # Boost score for external links (likely the real apply URL)
                if href and ("greenhouse" in href or "lever" in href or "workday" in href or "ashby" in href):
                    score += 30

                if score > candidate_score:
                    candidate = btn
                    candidate_score = score
            except Exception:
                continue
        
        if candidate and candidate_score > 0:
            logger.info(f"   🎯 Highest scoring redirect button: '{await candidate.text_content()}' ({candidate_score})")
            await candidate.click()
            return True
            
        return False
