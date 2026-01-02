"""
Browser utilities - Playwright browser automation with stealth mode
"""

import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from src.utils.config import get_settings


class BrowserManager:
    """
    Manages Playwright browser instances with stealth configuration.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    async def start(self) -> None:
        """Start the browser"""
        self.playwright = await async_playwright().start()
        
        browser_config = self.settings.browser
        
        # Launch browser based on type
        if browser_config.type == "firefox":
            self.browser = await self.playwright.firefox.launch(
                headless=browser_config.headless,
                slow_mo=browser_config.slow_mo,
            )
        elif browser_config.type == "webkit":
            self.browser = await self.playwright.webkit.launch(
                headless=browser_config.headless,
                slow_mo=browser_config.slow_mo,
            )
        else:
            self.browser = await self.playwright.chromium.launch(
                headless=browser_config.headless,
                slow_mo=browser_config.slow_mo,
            )
        
        # Create context with stealth settings
        self.context = await self._create_stealth_context()
    
    async def _create_stealth_context(self) -> BrowserContext:
        """Create a browser context with anti-detection measures"""
        settings = self.settings.browser
        
        context = await self.browser.new_context(
            viewport=settings.viewport,
            user_agent=settings.user_agent or self._get_default_user_agent(),
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
            # Extra HTTP headers to appear more human
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )
        
        # Add stealth scripts
        await context.add_init_script(self._get_stealth_script())
        
        return context
    
    def _get_default_user_agent(self) -> str:
        """Get a realistic user agent string"""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    def _get_stealth_script(self) -> str:
        """JavaScript to make browser harder to detect as automated"""
        return """
        // Override webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }
            ],
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Override platform
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
        });
        
        // Override hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
        });
        
        // Remove automation indicators
        window.chrome = { runtime: {} };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """
    
    async def new_page(self) -> Page:
        """Create a new page"""
        if not self.context:
            await self.start()
        return await self.context.new_page()
    
    async def stop(self) -> None:
        """Stop the browser and cleanup"""
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def take_screenshot(self, page: Page, name: str) -> str:
        """Take a screenshot and save it"""
        screenshots_dir = Path(self.settings.application.screenshots_dir)
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        path = screenshots_dir / f"{name}.png"
        await page.screenshot(path=path, full_page=True)
        return str(path)
    
    async def add_linkedin_cookies(self, page: Page) -> None:
        """Add LinkedIn session cookies if available"""
        li_at = self.settings.linkedin_li_at
        jsessionid = self.settings.linkedin_jsessionid
        
        if li_at and jsessionid:
            await self.context.add_cookies([
                {
                    "name": "li_at",
                    "value": li_at,
                    "domain": ".linkedin.com",
                    "path": "/",
                },
                {
                    "name": "JSESSIONID",
                    "value": jsessionid,
                    "domain": ".linkedin.com",
                    "path": "/",
                }
            ])


# Global browser manager
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Get the global browser manager instance"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


@asynccontextmanager
async def browser_session():
    """
    Context manager for browser sessions.
    
    Usage:
        async with browser_session() as (browser, page):
            await page.goto("https://example.com")
    """
    manager = get_browser_manager()
    try:
        await manager.start()
        page = await manager.new_page()
        yield manager, page
    finally:
        await manager.stop()


async def human_like_delay(min_ms: int = 500, max_ms: int = 2000) -> None:
    """Add a random human-like delay"""
    import random
    delay = random.uniform(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)


async def human_like_type(page: Page, selector: str, text: str) -> None:
    """Type text with human-like delays between keystrokes"""
    import random
    
    element = page.locator(selector)
    await element.click()
    
    for char in text:
        await element.press(char)
        # Random delay between keystrokes (50-150ms)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def wait_for_navigation_or_timeout(
    page: Page, 
    timeout: int = 30000,
    wait_until: str = "networkidle"
) -> bool:
    """Wait for navigation with a timeout, return True if successful"""
    try:
        await page.wait_for_load_state(wait_until, timeout=timeout)
        return True
    except Exception:
        return False
