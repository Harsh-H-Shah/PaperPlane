import httpx
import warnings
import re
from typing import Optional
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_string
from src.core.job import Job, JobSource
from src.utils.config import get_settings

# Suppress XML parsing warning for RSS feeds
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)



class BuiltInScraper(BaseScraper):
    SOURCE_NAME = "BuiltIn"
    SOURCE_TYPE = JobSource.BUILTIN
    
    # Targeting Entry Level Software Engineering in USA
    BASE_URL = "https://builtin.com/jobs/engineering/software-engineering/entry-level"
    INTERN_URL = "https://builtin.com/jobs/internships"
    
    def __init__(self):
        super().__init__()
        self._settings = get_settings()
    
    def _get_auth_cookies(self) -> dict:
        """Get BuiltIn session cookies from settings if available"""
        cookies = {}
        # Add SSESS session cookie
        if self._settings.builtin_session and self._settings.builtin_session_name:
            cookies[self._settings.builtin_session_name] = self._settings.builtin_session
        # Add BIX_AUTH cookies (required for full authentication)
        if self._settings.builtin_bix_auth:
            cookies["BIX_AUTH"] = self._settings.builtin_bix_auth
        if self._settings.builtin_bix_authc1:
            cookies["BIX_AUTHC1"] = self._settings.builtin_bix_authc1
        if self._settings.builtin_bix_authc2:
            cookies["BIX_AUTHC2"] = self._settings.builtin_bix_authc2
        return cookies
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or ["Software Engineer"]
        
        # Scrape both Entry Level and Internships
        urls = [
            f"{self.BASE_URL}?search=Software+Engineer&country=USA&allLocations=true",
            f"{self.INTERN_URL}?search=Software+Engineer&country=USA&allLocations=true"
        ]
        
        cookies = self._get_auth_cookies()
        is_authenticated = bool(cookies)
        
        if is_authenticated:
            print("   🔐 BuiltIn: Using authenticated session")
        else:
            print("   ⚠️ BuiltIn: No session cookies - apply URLs may not work. Set BUILTIN_SESSION in .env")
        
        async with httpx.AsyncClient(cookies=cookies) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://builtin.com/",
            }
            
            for url in urls:
                try:
                    if len(jobs) >= limit:
                        break
                        
                    response = await client.get(url, headers=headers, timeout=30, follow_redirects=True)
                    
                    if response.status_code == 200:
                        new_jobs = await self._parse_html_with_apply_urls(
                            client, headers, response.text, keywords, limit - len(jobs), is_authenticated
                        )
                        jobs.extend(new_jobs)
                except Exception as e:
                    print(f"Error fetching BuiltIn URL {url}: {e}")
        
        self.jobs_found = len(jobs)
        # Deduplicate by URL
        unique_jobs = {job.url: job for job in jobs}
        return list(unique_jobs.values())[:limit]
    
    async def _fetch_real_apply_url(self, client: httpx.AsyncClient, headers: dict, job_url: str) -> Optional[str]:
        """Fetch the job detail page and extract the real company apply URL"""
        try:
            response = await client.get(job_url, headers=headers, timeout=15, follow_redirects=True)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Look for the actual apply link - BuiltIn usually has "Apply on company site" button
            # Selectors for the external apply link
            apply_selectors = [
                'a[data-id="apply-button"]',
                'a[href*="redirect"]',  # BuiltIn redirect links
                'a.apply-button[target="_blank"]',
                'a[href*="greenhouse.io"]',
                'a[href*="lever.co"]',
                'a[href*="workday"]',
                'a[href*="jobs.ashbyhq.com"]',
                'a[href*="myworkdayjobs"]',
                'a:has-text("Apply on company site")',
            ]
            
            for selector in apply_selectors:
                try:
                    # BeautifulSoup CSS selector
                    element = soup.select_one(selector)
                    if element and element.get('href'):
                        href = element.get('href')
                        # Handle relative URLs
                        if href.startswith('/'):
                            href = f"https://builtin.com{href}"
                        # Skip builtin internal links unless they're redirects
                        if 'builtin.com' in href and '/redirect' not in href:
                            continue
                        return href
                except Exception:
                    continue
            
            # Also check for data attributes or onclick handlers that might have the URL
            scripts = soup.find_all('script', string=re.compile(r'apply.*url|external.*link', re.I))
            for script in scripts:
                # Try to extract URLs from script content
                urls = re.findall(r'https?://[^\s"\'<>]+(?:greenhouse|lever|workday|ashby)[^\s"\'<>]+', script.string or '')
                if urls:
                    return urls[0]
            
            return None
        except Exception as e:
            print(f"      Error fetching apply URL for {job_url}: {e}")
            return None
    
    async def _parse_html_with_apply_urls(
        self, client: httpx.AsyncClient, headers: dict, html: str, 
        keywords: list[str], limit: int, fetch_apply_urls: bool
    ) -> list[Job]:
    
        """Parse HTML and optionally fetch real apply URLs for each job"""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        # BuiltIn Job Cards
        job_cards = soup.select('div[data-id="job-card"], div.job-item, div.card-body')
        
        for card in job_cards:
            try:
                # Selectors based on recent analysis
                title_el = card.select_one('a[id^="job-card-alias-"], h2 a, a.card-alias-after-overlay')
                company_el = card.select_one('div[data-id="company-title"], a[href^="/company/"] span, .company-title')
                date_el = card.select_one('div.bounded-attribute-section span, span.job-date')
                
                if not title_el:
                    continue
                
                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown Company"
                
                # Link is usually on the title element
                url = title_el.get('href', '')
                if not url.startswith('http'):
                    url = f"https://builtin.com{url}"
                
                # Date parsing
                posted_date = None
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    # "Reposted 19 Hours Ago" -> "19 Hours Ago"
                    date_text = date_text.replace("Reposted", "").replace("Posted", "").strip()
                    posted_date = parse_date_string(date_text)
                
                # Try to get the real apply URL if authenticated
                apply_url = url  # Default to the listing page
                if fetch_apply_urls:
                    real_url = await self._fetch_real_apply_url(client, headers, url)
                    if real_url:
                        apply_url = real_url
                        print(f"      ✅ Got real apply URL for {company}: {real_url[:60]}...")
                
                job = Job(
                    title=title,
                    company=company,
                    location="United States", # Default as we filtered by USA
                    url=url,
                    apply_url=apply_url,
                    source=JobSource.BUILTIN,
                    posted_date=posted_date,
                    tags=["builtin", "entry-level" if "entry-level" in self.BASE_URL else "intern"],
                )
                
                if self.should_include_job(job):
                    jobs.append(job)
                    if len(jobs) >= limit:
                        break
            except Exception:
                # print(f"Error parsing BuiltIn card: {e}")
                continue
        
        return jobs



