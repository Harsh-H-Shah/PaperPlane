"""
Google Jobs Scraper - Enhanced version for maximum job discovery
Scrapes job listings from Google's job search using multiple strategies.
"""
import re
import json
from typing import Optional
from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_string
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type


class GoogleJobsScraper(BaseScraper):
    SOURCE_NAME = "GoogleJobs"
    SOURCE_TYPE = JobSource.GOOGLE_JOBS
    
    SEARCH_URL = "https://www.google.com/search"
    
    # Search variations to maximize results
    SEARCH_TEMPLATES = [
        "{keyword} jobs",
        "{keyword} new grad jobs",
        "{keyword} entry level jobs",
        "{keyword} remote jobs",
        "{keyword} jobs usa",
    ]
    
    def __init__(self):
        super().__init__()
        # Very conservative rate limiting for Google
        self.rate_limiter.rpm = 8
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        from src.utils.browser import browser_session
        
        jobs = []
        queries = keywords or self.get_search_keywords()
        location = location or "United States"
        
        print("   🔄 GoogleJobs: Switch to Playwright (Browser) scraping...")
        
        try:
            async with browser_session() as (manager, page):
                for query in queries[:1]: # Fail fast on first query
                    if len(jobs) >= limit:
                        break
                    
                    # Google Jobs URL with 'ibp=htl;jobs'
                    encoded_query = query.replace(" ", "+")
                    url = f"https://www.google.com/search?q={encoded_query}&ibp=htl;jobs&hl=en&gl=us"
                    
                    print(f"      Google: Navigating to {url}...")
                    
                    try:
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(5000) # Wait longer
                        
                        # Debug: Take screenshot
                        await manager.take_screenshot(page, "debug_google_jobs")
                        print("      📸 Debug screenshot saved to data/screenshots/debug_google_jobs.png")
                        
                        # Debug: Save HTML
                        html = await page.content()
                        debug_html_path = "data/debug_google_jobs.html"
                        with open(debug_html_path, "w") as f:
                            f.write(html)
                        print(f"      📄 Debug HTML saved to {debug_html_path}")
                        
                        page_jobs = self._parse_response(html)
                        
                        print(f"      Google: Found {len(page_jobs)} jobs for '{query}'")
                        
                        for job in page_jobs:
                            if self.should_include_job(job):
                                jobs.append(job)
                    
                    except Exception as e:
                        print(f"      Error scraping Google query '{query}': {e}")
                        
        except Exception as e:
            print(f"   ❌ Google browser error: {e}")
            
        # Deduplicate
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            url_key = job.url.lower().rstrip('/')
            if url_key not in seen_urls:
                seen_urls.add(url_key)
            if job.url not in seen_urls: # Double check logic
                seen_urls.add(job.url)
                unique_jobs.append(job)
                
        self.jobs_found = len(unique_jobs)
        print(f"   📋 GoogleJobs: Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:limit]
    
    def _parse_response(self, html: str) -> list[Job]:
        """Parse Google search results for jobs"""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Strategy 1: Extract from JSON-LD structured data
        ld_jobs = self._extract_json_ld(soup)
        jobs.extend(ld_jobs)
        
        # Strategy 2: Parse embedded JSON data
        json_jobs = self._extract_embedded_json(html)
        jobs.extend(json_jobs)
        
        # Strategy 3: Parse HTML job cards
        if not jobs:
            html_jobs = self._parse_html_cards(soup)
            jobs.extend(html_jobs)
        
        return jobs
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> list[Job]:
        """Extract jobs from JSON-LD structured data"""
        jobs = []
        
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                # Handle single job
                if data.get('@type') == 'JobPosting':
                    job = self._parse_job_posting(data)
                    if job:
                        jobs.append(job)
                
                # Handle list of jobs
                elif isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'JobPosting':
                            job = self._parse_job_posting(item)
                            if job:
                                jobs.append(job)
                                
            except (json.JSONDecodeError, TypeError):
                continue
        
        return jobs
    
    def _extract_embedded_json(self, html: str) -> list[Job]:
        """Extract jobs from embedded JavaScript data"""
        jobs = []
        
        # Look for job data in various formats
        patterns = [
            r'window\.jobData\s*=\s*(\[.+?\]);',
            r'"jobListings"\s*:\s*(\[.+?\])',
            r'AF_initDataCallback\([^)]*data:\s*(\[.+?\])',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the match and parse
                    data = json.loads(match)
                    if isinstance(data, list):
                        for item in data:
                            job = self._parse_embedded_job(item)
                            if job:
                                jobs.append(job)
                except Exception:
                    continue
        
        return jobs
    
    def _parse_html_cards(self, soup: BeautifulSoup) -> list[Job]:
        """Parse job information from HTML elements"""
        jobs = []
        
        # Google Jobs uses various selectors
        selectors = [
            'div[data-hveid]',
            'li.iFjolb',
            'div.PwjeAc',
            'div.gws-plugins-horizon-jobs__li-ed',
            'div[jscontroller][data-ved]',
        ]
        
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                for card in cards[:20]:
                    job = self._parse_card(card)
                    if job:
                        jobs.append(job)
                if jobs:
                    break
        
        return jobs
    
    def _parse_job_posting(self, data: dict) -> Optional[Job]:
        """Parse a JobPosting JSON-LD object"""
        try:
            title = data.get("title", "")
            if not title:
                return None
            
            # Company
            hiring_org = data.get("hiringOrganization", {})
            company = hiring_org.get("name", "Unknown") if isinstance(hiring_org, dict) else "Unknown"
            
            # Location
            location = "Remote"
            job_location = data.get("jobLocation")
            if job_location:
                if isinstance(job_location, list) and job_location:
                    job_location = job_location[0]
                if isinstance(job_location, dict):
                    address = job_location.get("address", {})
                    if isinstance(address, dict):
                        parts = [
                            address.get("addressLocality", ""),
                            address.get("addressRegion", ""),
                            address.get("addressCountry", "")
                        ]
                        location = ", ".join(p for p in parts if p) or "Remote"
            
            # URL
            url = data.get("url") or data.get("sameAs") or data.get("directApply")
            if not url:
                return None
            
            # Date
            date_str = data.get("datePosted", "")
            posted_date = parse_date_string(date_str) if date_str else None
            
            # Salary
            salary = None
            base_salary = data.get("baseSalary", {})
            if isinstance(base_salary, dict):
                value = base_salary.get("value", {})
                if isinstance(value, dict):
                    min_val = value.get("minValue")
                    max_val = value.get("maxValue")
                    if min_val and max_val:
                        salary = f"${min_val:,.0f} - ${max_val:,.0f}"
            
            # Description
            description = data.get("description", "")
            if description:
                # Strip HTML
                description = re.sub(r'<[^>]+>', '', description)[:300]
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                description=description if description else None,
                salary_range=salary,
                source=JobSource.GOOGLE_JOBS,
                application_type=app_type,
                posted_date=posted_date,
                job_type="Full-time",
                tags=["google_jobs"],
            )
        except Exception:
            return None
    
    def _parse_embedded_job(self, item) -> Optional[Job]:
        """Parse job from embedded data structure"""
        try:
            if not isinstance(item, (list, dict)):
                return None
            
            # Google's data format varies, try to extract key fields
            if isinstance(item, dict):
                title = item.get("title", "") or item.get("jobTitle", "")
                company = item.get("company", "") or item.get("companyName", "")
                location = item.get("location", "") or item.get("city", "")
                url = item.get("url", "") or item.get("link", "")
            else:
                # List format - positions vary
                if len(item) < 3:
                    return None
                title = str(item[0]) if item[0] else ""
                company = str(item[1]) if len(item) > 1 and item[1] else "Unknown"
                location = str(item[2]) if len(item) > 2 and item[2] else "Remote"
                url = str(item[3]) if len(item) > 3 and item[3] else ""
            
            if not title or not url:
                return None
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                source=JobSource.GOOGLE_JOBS,
                application_type=app_type,
                job_type="Full-time",
                tags=["google_jobs"],
            )
        except Exception:
            return None
    
    def _parse_card(self, card) -> Optional[Job]:
        """Parse a job card HTML element"""
        try:
            # Title
            title_el = card.select_one('div.BjJfJf, h2, h3, [role="heading"], .job-title')
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            
            if not title or len(title) < 5:
                return None
            
            # Company
            company_el = card.select_one('div.vNEEBe, .company, [data-company]')
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            
            # Location
            location_el = card.select_one('div.Qk80Jf, .location')
            location = location_el.get_text(strip=True) if location_el else "Remote"
            
            # URL
            link_el = card.select_one('a[href*="jobs"], a[href*="careers"], a[data-url]')
            if link_el:
                url = link_el.get('href') or link_el.get('data-url', '')
            else:
                return None
            
            if not url or not url.startswith('http'):
                return None
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                source=JobSource.GOOGLE_JOBS,
                application_type=app_type,
                job_type="Full-time",
                tags=["google_jobs"],
            )
        except Exception:
            return None
