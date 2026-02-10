"""
Glassdoor Jobs Scraper - Uses browser session cookies for authentication
Supports Google OAuth by capturing cookies after manual login.

Setup:
1. Login to Glassdoor in your browser (can use Google Sign-in)
2. Export cookies using a browser extension (e.g., "Cookie-Editor")
3. Set GLASSDOOR_COOKIES in .env with the cookie string

Alternatively, provide session cookies directly:
- GLASSDOOR_GSID: The GSESSIONID cookie value
"""
import httpx
import os
import re
import json
from typing import Optional

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_string
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type


class GlassdoorScraper(BaseScraper):
    SOURCE_NAME = "Glassdoor"
    SOURCE_TYPE = JobSource.GLASSDOOR
    
    BASE_URL = "https://www.glassdoor.com"
    JOBS_URL = "https://www.glassdoor.com/Job/jobs.htm"
    
    # Job type and seniority filters for new grad/entry level
    SENIORITY_FILTERS = ["entrylevel", "midseniorlevel"]
    
    def __init__(self):
        super().__init__()
        # Get cookies from env
        self.cookies_str = os.getenv("GLASSDOOR_COOKIES", "")
        self.gsid = os.getenv("GLASSDOOR_GSID", "")
        self.enabled = bool(self.cookies_str or self.gsid)
        
        # Conservative rate limiting
        self.rate_limiter.rpm = 10
        
        if not self.enabled:
            print("   ⚠️ Glassdoor: No session cookies found.")
            print("      To enable: Login to Glassdoor in browser, export cookies,")
            print("      and set GLASSDOOR_COOKIES or GLASSDOOR_GSID in .env")
    
    def _get_cookies(self) -> dict:
        """Parse cookies from environment"""
        cookies = {}
        
        if self.gsid:
            cookies["GSESSIONID"] = self.gsid
        
        if self.cookies_str:
            # Parse cookie string (format: "name1=value1; name2=value2")
            for part in self.cookies_str.split(';'):
                if '=' in part:
                    name, value = part.strip().split('=', 1)
                    cookies[name] = value
        
        print(f"   DEBUG: Glassdoor using cookies: {list(cookies.keys())}")
        return cookies
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        from src.utils.browser import browser_session
        
        jobs = []
        keywords = keywords or self.get_search_keywords()
        location = location or "United States"
        
        print("   🔄 Glassdoor: Switch to Playwright (Browser) scraping to bypass WAF...")
        
        try:
            async with browser_session() as (manager, page):
                # Add cookies if available
                cookies_dict = self._get_cookies()
                if cookies_dict and manager.context:
                    playwright_cookies = []
                    for name, value in cookies_dict.items():
                        playwright_cookies.append({
                            "name": name,
                            "value": value,
                            "domain": ".glassdoor.com",
                            "path": "/"
                        })
                    await manager.context.add_cookies(playwright_cookies)
                
                # Search for keywords
                for keyword in keywords[:3]:
                    if len(jobs) >= limit:
                        break
                    
                    # Paginate through results
                    for p_num in range(1, 4):  # Up to 3 pages per keyword
                        if len(jobs) >= limit:
                            break
                        
                        # Construct URL
                        keyword_slug = keyword.lower().replace(" ", "-")
                        location_slug = location.lower().replace(" ", "-").replace(",", "")
                        
                        search_path = f"/Job/{location_slug}-{keyword_slug}-jobs-SRCH_IL.0,{len(location_slug)}_IN1_KO{len(location_slug)+1},{len(location_slug)+1+len(keyword_slug)}"
                        if p_num > 1:
                            search_path += f"_IP{p_num}"
                        search_path += ".htm"
                        
                        url = f"{self.BASE_URL}{search_path}"
                        
                        print(f"      Glassdoor: Navigating to {url}...")
                        try:
                            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(3000) # Wait for JS to load jobs
                            
                            # maybe handle captcha if present?
                            title = await page.title()
                            if "Just a moment" in title or "Cloudflare" in title:
                                print("      ⚠️ Glassdoor: Cloudflare challenge detected. Waiting...")
                                await page.wait_for_timeout(5000)
                            
                            html = await page.content()
                            page_jobs = self._parse_jobs_html(html)
                            
                            if p_num == 1:
                                print(f"      Glassdoor: Found {len(page_jobs)} jobs for '{keyword}'")
                                
                            for job in page_jobs:
                                if self.should_include_job(job):
                                    jobs.append(job)
                                    if len(jobs) >= limit:
                                        break
                                        
                        except Exception as e:
                            print(f"      Error on page {p_num}: {e}")
                            
        except Exception as e:
            print(f"   ❌ Glassdoor browser error: {e}")
        
        # Deduplicate
        seen = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen:
                seen.add(job.url)
                unique_jobs.append(job)
        
        self.jobs_found = len(unique_jobs)
        print(f"   📋 Glassdoor: Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:limit]
    
    async def _search_page(self, client: httpx.AsyncClient, keyword: str, location: str, page: int) -> list[Job]:
        jobs = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Referer": "https://www.glassdoor.com/",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
            
            # Glassdoor search URL structure
            # Example: /Job/united-states-software-engineer-jobs-SRCH_IL.0,13_IN1_KO14,31.htm
            keyword_slug = keyword.lower().replace(" ", "-")
            location_slug = location.lower().replace(" ", "-").replace(",", "")
            
            # Construct search URL
            search_path = f"/Job/{location_slug}-{keyword_slug}-jobs-SRCH_IL.0,{len(location_slug)}_IN1_KO{len(location_slug)+1},{len(location_slug)+1+len(keyword_slug)}"
            if page > 1:
                search_path += f"_IP{page}"
            search_path += ".htm"
            
            url = f"{self.BASE_URL}{search_path}"
            
            response = await client.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                jobs = self._parse_jobs_html(response.text)
                if page == 1:
                    print(f"      Glassdoor: Found {len(jobs)} jobs for '{keyword}'")
            else:
                # Fallback to simple search
                params = {
                    "sc.keyword": keyword,
                    "locT": "N",
                    "locId": "1",
                }
                response = await client.get(self.JOBS_URL, params=params, headers=headers, timeout=30)
                if response.status_code == 200:
                    jobs = self._parse_jobs_html(response.text)
                    
        except Exception as e:
            if "403" in str(e) or "401" in str(e):
                print("   ⚠️ Glassdoor: Authentication required. Please update cookies.")
        
        return jobs
    
    def _parse_jobs_html(self, html: str) -> list[Job]:
        """Parse Glassdoor jobs search results"""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Try multiple selectors for job cards
        job_selectors = [
            'li[data-jobid]',
            'li.react-job-listing',
            'article[data-id]',
            'div[data-test="job-link"]',
            'a[data-test="job-link"]',
        ]
        
        for selector in job_selectors:
            cards = soup.select(selector)
            if cards:
                for card in cards:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                break
        
        # Try embedded JSON data
        if not jobs:
            jobs = self._extract_from_json(html)
        
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a single job card"""
        try:
            # Title
            title_el = card.select_one('a[data-test="job-link"], .job-title, a.jobLink, h2 a')
            if not title_el:
                title_el = card.select_one('a[href*="job-listing"]')
            
            if not title_el:
                return None
            
            title = title_el.get_text(strip=True)
            href = title_el.get('href', '')
            
            if not title or len(title) < 3:
                return None
            
            # Make absolute URL
            if href.startswith('/'):
                url = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                url = href
            else:
                return None
            
            # Company
            company_el = card.select_one('[data-test="employer-name"], .employer-name, .job-employer')
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            # Clean rating from company name
            company = re.sub(r'\s*\d+\.?\d*\s*★?$', '', company).strip()
            
            # Location
            location_el = card.select_one('[data-test="job-location"], .location, .job-location')
            location = location_el.get_text(strip=True) if location_el else "Remote"
            
            # Salary
            salary_el = card.select_one('[data-test="salary-estimate"], .salary-estimate')
            salary = salary_el.get_text(strip=True) if salary_el else None
            
            # Date
            date_el = card.select_one('[data-test="listing-age"], .listing-age')
            date_str = date_el.get_text(strip=True) if date_el else ""
            posted_date = parse_date_string(date_str) if date_str else None
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                salary_range=salary,
                source=JobSource.GLASSDOOR,
                application_type=app_type,
                posted_date=posted_date,
                job_type="Full-time",
                tags=["glassdoor"],
            )
        except Exception:
            return None
    
    def _extract_from_json(self, html: str) -> list[Job]:
        """Extract jobs from embedded Apollo state or NEXT_DATA"""
        jobs = []
        
        try:
            # Look for Apollo state
            patterns = [
                r'window\.__APOLLO_STATE__\s*=\s*({.+?});',
                r'"jobListings":\s*(\[.+?\])',
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        # Parse job data from Apollo cache
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if 'JobListing' in key and isinstance(value, dict):
                                    job = self._parse_apollo_job(value)
                                    if job:
                                        jobs.append(job)
                        elif isinstance(data, list):
                            for item in data:
                                job = self._parse_apollo_job(item)
                                if job:
                                    jobs.append(job)
                    except json.JSONDecodeError:
                        continue
                    
        except Exception:
            pass
        
        return jobs
    
    def _parse_apollo_job(self, data: dict) -> Optional[Job]:
        """Parse job from Apollo state data"""
        try:
            title = data.get("jobTitle", "") or data.get("title", "")
            company = data.get("employer", {}).get("name", "") or data.get("companyName", "")
            location = data.get("location", "") or data.get("city", "")
            
            if not title:
                return None
            
            job_id = data.get("jobId", "") or data.get("id", "")
            url = f"{self.BASE_URL}/job-listing/{job_id}" if job_id else ""
            
            if not url:
                return None
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company if isinstance(company, str) else "Unknown",
                location=location,
                url=url,
                apply_url=url,
                source=JobSource.GLASSDOOR,
                application_type=app_type,
                job_type="Full-time",
                tags=["glassdoor"],
            )
        except Exception:
            return None
