import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from src.utils.config import get_settings


class BrowserManager:
    def __init__(self):
        self.settings = get_settings()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        
        browser_config = self.settings.browser
        user_data_dir = Path("data/browser_context")
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # In Playwright, launch_persistent_context handles both launch and context creation
        launch_args = {
            "user_data_dir": str(user_data_dir),
            "headless": browser_config.headless,
            "slow_mo": browser_config.slow_mo,
            "viewport": browser_config.viewport,
            "user_agent": browser_config.user_agent or self._get_default_user_agent(),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
            "permissions": ["geolocation"],
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        }
        
        if browser_config.type == "firefox":
            self.context = await self.playwright.firefox.launch_persistent_context(**launch_args)
        elif browser_config.type == "webkit":
            self.context = await self.playwright.webkit.launch_persistent_context(**launch_args)
        else:
            self.context = await self.playwright.chromium.launch_persistent_context(**launch_args)
        
        await self.context.add_init_script(self._get_stealth_script())
        # With persistent context, we don't need a separate browser object for closing/management
        # as the context itself represents the browser session.
        self.browser = None 
    
    
    def _get_default_user_agent(self) -> str:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    def _get_stealth_script(self) -> str:
        return """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [{ 0: {type: "application/x-google-chrome-pdf"}, description: "PDF", filename: "internal-pdf-viewer", length: 1, name: "Chrome PDF Plugin" }],
        });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        window.chrome = { runtime: {} };
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : originalQuery(parameters)
        );
        """
    
    async def new_page(self) -> Page:
        if not self.context:
            await self.start()
        return await self.context.new_page()
    
    async def stop(self) -> None:
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
        screenshots_dir = Path(self.settings.application.screenshots_dir)
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        path = screenshots_dir / f"{name}.png"
        await page.screenshot(path=path, full_page=True)
        return str(path)
    
    async def add_linkedin_cookies(self, page: Page) -> None:
        li_at = self.settings.linkedin_li_at
        jsessionid = self.settings.linkedin_jsessionid
        
        if li_at and jsessionid:
            await self.context.add_cookies([
                {"name": "li_at", "value": li_at, "domain": ".linkedin.com", "path": "/"},
                {"name": "JSESSIONID", "value": jsessionid, "domain": ".linkedin.com", "path": "/"}
            ])
    
    async def add_builtin_cookies(self) -> None:
        """Add BuiltIn session cookies if configured in .env"""
        if not self.context:
            return  # Context not initialized yet
        
        cookies = []
        
        # Add SSESS session cookie
        if self.settings.builtin_session and self.settings.builtin_session_name:
            cookies.append({
                "name": self.settings.builtin_session_name,
                "value": self.settings.builtin_session,
                "domain": ".builtin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            })
        
        # Add BIX_AUTH cookies (required for full authentication)
        if self.settings.builtin_bix_auth:
            cookies.append({
                "name": "BIX_AUTH",
                "value": self.settings.builtin_bix_auth,
                "domain": ".builtin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            })
        
        if self.settings.builtin_bix_authc1:
            cookies.append({
                "name": "BIX_AUTHC1",
                "value": self.settings.builtin_bix_authc1,
                "domain": ".builtin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            })
        
        if self.settings.builtin_bix_authc2:
            cookies.append({
                "name": "BIX_AUTHC2",
                "value": self.settings.builtin_bix_authc2,
                "domain": ".builtin.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            })
        
        if cookies:
            await self.context.add_cookies(cookies)
            print(f"   🍪 BuiltIn cookies added ({len(cookies)} cookies)")
    
    async def ensure_builtin_authenticated(self, page: Page) -> bool:
        """Check if BuiltIn is authenticated, add cookies if not"""
        if not self.settings.builtin_session:
            return False
        
        # Add cookies before navigating
        await self.add_builtin_cookies()
        return True


_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


@asynccontextmanager
async def browser_session():
    manager = get_browser_manager()
    try:
        await manager.start()
        page = await manager.new_page()
        yield manager, page
    finally:
        await manager.stop()


async def human_like_delay(min_ms: int = 500, max_ms: int = 2000) -> None:
    import random
    delay = random.uniform(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)


async def human_like_type(page: Page, selector: str, text: str) -> None:
    import random
    element = page.locator(selector)
    await element.click()
    for char in text:
        await element.press(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def wait_for_navigation_or_timeout(page: Page, timeout: int = 30000, wait_until: str = "networkidle") -> bool:
    try:
        await page.wait_for_load_state(wait_until, timeout=timeout)
        return True
    except Exception:
        return False
