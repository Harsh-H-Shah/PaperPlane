"""
Levels.fyi Jobs Scraper - Enhanced version for maximum job discovery
Scrapes job listings from Levels.fyi job board and company pages.

This scraper uses multiple approaches:
1. Main jobs page with filters
2. Individual company career pages
3. Salary data with job links
"""
import httpx
import re
import json
import asyncio
from typing import Optional
from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.core.job import Job, JobSource, ApplicationType
from src.classifiers.detector import detect_application_type


# Top tech companies on Levels.fyi with active job postings
TOP_COMPANIES = [
    "google", "meta", "amazon", "apple", "microsoft", "netflix",
    "stripe", "airbnb", "uber", "lyft", "doordash", "instacart",
    "robinhood", "coinbase", "square", "plaid", "brex",
    "datadog", "snowflake", "mongodb", "cloudflare", "twilio",
    "figma", "notion", "discord", "slack", "dropbox", "zoom",
    "salesforce", "adobe", "nvidia", "intel", "amd",
    "openai", "anthropic", "databricks", "palantir",
    "pinterest", "snap", "twitter", "linkedin", "indeed",
    "roblox", "unity", "epic-games", "riot-games",
    "oracle", "ibm", "cisco", "vmware", "servicenow",
]


class LevelsfyiScraper(BaseScraper):
    SOURCE_NAME = "Levelsfyi"
    SOURCE_TYPE = JobSource.LEVELSFYI
    
    BASE_URL = "https://www.levels.fyi"
    JOBS_URL = "https://www.levels.fyi/jobs"
    COMPANIES_URL = "https://www.levels.fyi/companies"
    
    # Experience level filters
    EXPERIENCE_FILTERS = ["entry", "junior", "mid", "senior"]
    
    def __init__(self):
        super().__init__()
        # Rate limiting
        self.rate_limiter.rpm = 30  # Faster rate for levels.fyi
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or self.get_search_keywords()
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                # Strategy 1: Main jobs page with keyword filters (fast)
                main_jobs = await self._scrape_main_jobs(client, keywords, limit)
                jobs.extend(main_jobs)
                
                # Strategy 2: Only scrape companies if we need more jobs
                if len(jobs) < limit:
                    # Limit to 10 companies max for speed
                    company_jobs = await self._scrape_company_jobs(client, keywords, min(10, limit - len(jobs)))
                    jobs.extend(company_jobs)
                
                # Strategy 3: Try API endpoints if available
                if len(jobs) < limit:
                    api_jobs = await self._try_api_endpoints(client, keywords, limit - len(jobs))
                    jobs.extend(api_jobs)
                    
        except Exception as e:
            print(f"   ❌ Levels.fyi error: {e}")
        
        # Deduplicate
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            url_key = job.url.lower().rstrip('/')
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_jobs.append(job)
        
        self.jobs_found = len(unique_jobs)
        print(f"   📋 Levels.fyi: Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:limit]
    
    async def _scrape_main_jobs(self, client: httpx.AsyncClient, keywords: list[str], limit: int) -> list[Job]:
        """Scrape the main jobs listing page"""
        jobs = []
        
        headers = self._get_headers()
        
        # Try different URL patterns
        urls_to_try = [
            f"{self.JOBS_URL}",
            f"{self.JOBS_URL}?title=Software+Engineer",
            f"{self.JOBS_URL}?title=Engineer",
            f"{self.BASE_URL}/?tab=jobs",
        ]
        
        for url in urls_to_try:
            if len(jobs) >= limit:
                break
                
            try:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    page_jobs = self._parse_jobs_page(response.text, keywords)
                    if page_jobs:
                        jobs.extend(page_jobs)
                        print(f"      Levels.fyi: Found {len(page_jobs)} jobs from {url}")
                        
            except Exception:
                continue
        
        return jobs[:limit]
    
    async def _scrape_company_jobs(self, client: httpx.AsyncClient, keywords: list[str], limit: int) -> list[Job]:
        """Scrape job listings from individual company pages"""
        jobs = []
        headers = self._get_headers()
        
        batch_size = 3  # Smaller batches for faster results
        max_companies = 10  # Limit companies to check
        for i in range(0, min(len(TOP_COMPANIES), max_companies), batch_size):
            if len(jobs) >= limit:
                break
                
            batch = TOP_COMPANIES[i:i + batch_size]
            tasks = [self._fetch_company_jobs(client, headers, company, keywords) for company in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    for job in result:
                        if self.should_include_job(job):
                            jobs.append(job)
                            if len(jobs) >= limit:
                                break
            
            # Small delay between batches
            await asyncio.sleep(0.3)
        
        return jobs
    
    async def _fetch_company_jobs(self, client: httpx.AsyncClient, headers: dict, company: str, keywords: list[str]) -> list[Job]:
        """Fetch jobs from a specific company page"""
        jobs = []
        
        try:
            # Try different URL patterns
            urls = [
                f"{self.COMPANIES_URL}/{company}/jobs",
                f"{self.COMPANIES_URL}/{company}",
                f"{self.BASE_URL}/company/{company}/jobs",
            ]
            
            for url in urls[:1]:  # Only try first URL pattern for speed
                try:
                    response = await client.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        jobs = self._parse_company_page(response.text, company, keywords)
                        if jobs:
                            break
                except Exception:
                    continue
                    
        except Exception:
            pass
        
        return jobs
    
    async def _try_api_endpoints(self, client: httpx.AsyncClient, keywords: list[str], limit: int) -> list[Job]:
        """Try known API endpoints"""
        jobs = []
        headers = self._get_headers()
        headers["Accept"] = "application/json"
        
        # Known API patterns
        api_endpoints = [
            f"{self.BASE_URL}/api/jobs",
            f"{self.BASE_URL}/api/v1/jobs",
            f"{self.BASE_URL}/_next/data/jobs.json",
        ]
        
        for endpoint in api_endpoints:
            try:
                response = await client.get(endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        api_jobs = self._parse_api_response(data, keywords)
                        jobs.extend(api_jobs)
                        if jobs:
                            print(f"      Levels.fyi: Found {len(jobs)} jobs from API")
                            break
                    except json.JSONDecodeError:
                        continue
            except Exception:
                continue
        
        return jobs[:limit]
    
    def _get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": self.BASE_URL,
        }
    
    def _parse_jobs_page(self, html: str, keywords: list[str]) -> list[Job]:
        """Parse jobs from the main jobs page"""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Try to extract from Next.js data first (more reliable)
        next_data = self._extract_next_data(html)
        if next_data:
            jobs = self._parse_next_data_jobs(next_data, keywords)
            if jobs:
                return jobs
        
        # Fallback to HTML parsing
        job_selectors = [
            'a[href*="/jobs/"]',
            'div[class*="JobCard"]',
            'div[class*="job-card"]',
            'tr[class*="job"]',
            'article[class*="job"]',
        ]
        
        for selector in job_selectors:
            elements = soup.select(selector)
            if elements:
                for el in elements[:50]:
                    job = self._parse_job_element(el, keywords)
                    if job:
                        jobs.append(job)
                if jobs:
                    break
        
        return jobs
    
    def _parse_company_page(self, html: str, company: str, keywords: list[str]) -> list[Job]:
        """Parse jobs from a company page"""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Try Next.js data
        next_data = self._extract_next_data(html)
        if next_data:
            jobs = self._parse_next_data_jobs(next_data, keywords, default_company=company.replace("-", " ").title())
            if jobs:
                return jobs
        
        # Find job listings
        job_links = soup.select('a[href*="job"], a[href*="career"], a[href*="position"]')
        
        for link in job_links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            # Filter by keywords
            if not any(kw.lower() in title.lower() for kw in keywords):
                continue
            
            # Make absolute URL
            if href.startswith('/'):
                url = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                url = href
            else:
                continue
            
            app_type, _ = detect_application_type(url)
            
            job = Job(
                title=title,
                company=company.replace("-", " ").title(),
                location="Remote",
                url=url,
                apply_url=url,
                source=JobSource.LEVELSFYI,
                application_type=app_type,
                job_type="Full-time",
                tags=["levelsfyi", company],
            )
            jobs.append(job)
        
        return jobs
    
    def _extract_next_data(self, html: str) -> Optional[dict]:
        """Extract __NEXT_DATA__ JSON from page"""
        try:
            match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except Exception:
            pass
        return None
    
    def _parse_next_data_jobs(self, data: dict, keywords: list[str], default_company: str = None) -> list[Job]:
        """Parse jobs from Next.js data"""
        jobs = []
        
        try:
            # print(f"DEBUG: Parsing Next.js data keys in props: {list(data.get('props', {}).keys())}")
            props = data.get("props", {}).get("pageProps", {})
            # print(f"DEBUG: Parsing Next.js pageProps keys: {list(props.keys())}")
            
            # NEW: Handle initialJobsData structure (company-grouped jobs)
            if "initialJobsData" in props:
                jobs_data = props["initialJobsData"]
                results = jobs_data.get("results", [])
                
                for company_data in results:
                    company_name = company_data.get("companyName", "Unknown")
                    company_slug = company_data.get("companySlug", "")
                    company_jobs = company_data.get("jobs", [])
                    # print(f"DEBUG: Processing {company_name}: {len(company_jobs)} jobs")
                    
                    for item in company_jobs:
                        job = self._parse_levels_job(item, company_name, company_slug, keywords)
                        if job:
                            jobs.append(job)
                        else:
                            pass # print(f"DEBUG: Failed to parse job from {company_name}")
                
                if jobs:
                    return jobs
            
            # Fallback: Look for job listings in various locations
            job_keys = ["jobs", "listings", "positions", "openings", "jobListings", "allJobs"]
            
            for key in job_keys:
                if key in props:
                    items = props[key]
                    if isinstance(items, list):
                        for item in items:
                            job = self._parse_json_job(item, keywords, default_company)
                            if job:
                                jobs.append(job)
            
            # Also check nested data
            if "data" in props:
                data_obj = props["data"]
                for key in job_keys:
                    if key in data_obj:
                        items = data_obj[key]
                        if isinstance(items, list):
                            for item in items:
                                job = self._parse_json_job(item, keywords, default_company)
                                if job:
                                    jobs.append(job)
                                    
        except Exception:
            pass
        
        return jobs
    
    def _parse_levels_job(self, item: dict, company_name: str, company_slug: str, keywords: list[str]) -> Optional[Job]:
        """Parse a job from Levels.fyi initialJobsData structure"""
        try:
            title = item.get("title", "")
            if not title:
                return None
            
            job_slug = item.get("slug", "")
            job_id = item.get("id", "")
            
            # Build URL - prefer slug for clean URL, fallback to ID, fallback to applicationUrl
            if job_slug:
                url = f"https://www.levels.fyi/jobs/{company_slug}/{job_slug}"
            elif job_id:
                url = f"https://www.levels.fyi/jobs?jobId={job_id}"
            elif item.get("applicationUrl"):
                url = item.get("applicationUrl")
            else:
                return None
            
            # Location
            location = "Remote"
            if item.get("location"):
                location = item.get("location")
            elif item.get("locations") and isinstance(item.get("locations"), list) and len(item.get("locations")) > 0:
                location = item.get("locations")[0]
            elif item.get("workArrangement") == "remote":
                location = "Remote"
            
            # Salary info
            salary = None
            min_comp = item.get("minTotalSalary") or item.get("minBaseSalary") or item.get("minTotalComp")
            max_comp = item.get("maxTotalSalary") or item.get("maxBaseSalary") or item.get("maxTotalComp")
            
            if min_comp and max_comp:
                salary = f"${int(min_comp):,} - ${int(max_comp):,}"
            
            return Job(
                title=title,
                company=company_name,
                location=location,
                url=url,
                apply_url=item.get("applicationUrl", url),
                salary_range=salary,
                source=self.SOURCE_TYPE,
                application_type=ApplicationType.REDIRECTOR,
                job_type="Full-time",
                tags=["levelsfyi"],
            )
        except Exception:
            # print(f"DEBUG: Levels.fyi parse error: {e}")
            return None
    
    def _parse_api_response(self, data: dict, keywords: list[str]) -> list[Job]:
        """Parse jobs from API response"""
        jobs = []
        
        try:
            # Handle different API response formats
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("jobs", []) or data.get("data", []) or data.get("results", [])
            else:
                return jobs
            
            for item in items:
                job = self._parse_json_job(item, keywords)
                if job:
                    jobs.append(job)
                    
        except Exception:
            pass
        
        return jobs
    
    def _parse_job_element(self, element, keywords: list[str]) -> Optional[Job]:
        """Parse a job from HTML element"""
        try:
            # Get text and check keywords
            text = element.get_text(strip=True)
            if not any(kw.lower() in text.lower() for kw in keywords):
                return None
            
            # Title
            title_el = element.select_one('h2, h3, h4, [class*="title"]')
            title = title_el.get_text(strip=True) if title_el else text[:50]
            
            # URL
            if element.name == 'a':
                href = element.get('href', '')
            else:
                link = element.select_one('a')
                href = link.get('href', '') if link else ''
            
            if not href:
                return None
            
            if href.startswith('/'):
                url = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                url = href
            else:
                return None
            
            # Company
            company_el = element.select_one('[class*="company"], [class*="employer"]')
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            
            # Location
            location_el = element.select_one('[class*="location"]')
            location = location_el.get_text(strip=True) if location_el else "Remote"
            
            # Salary (levels.fyi specialty)
            salary_el = element.select_one('[class*="salary"], [class*="comp"], [class*="pay"]')
            salary = salary_el.get_text(strip=True) if salary_el else None
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                salary_range=salary,
                source=JobSource.LEVELSFYI,
                application_type=app_type,
                job_type="Full-time",
                tags=["levelsfyi", "salary_transparent"],
            )
        except Exception:
            return None
    
    def _parse_json_job(self, item: dict, keywords: list[str], default_company: str = None) -> Optional[Job]:
        """Parse a job from JSON data"""
        try:
            title = item.get("title", "") or item.get("jobTitle", "") or item.get("name", "")
            
            if not title:
                return None
            
            # Filter by keywords
            if not any(kw.lower() in title.lower() for kw in keywords):
                return None
            
            # Company
            company = item.get("company", "") or item.get("companyName", "") or item.get("employer", "")
            if isinstance(company, dict):
                company = company.get("name", "")
            company = company or default_company or "Unknown"
            
            # Location
            location = item.get("location", "") or item.get("city", "") or item.get("office", "")
            if isinstance(location, dict):
                location = location.get("name", "") or location.get("city", "")
            location = location or "Remote"
            
            # URL
            url = item.get("url", "") or item.get("applyUrl", "") or item.get("jobUrl", "") or item.get("link", "")
            if not url:
                job_id = item.get("id", "") or item.get("jobId", "")
                if job_id:
                    url = f"{self.JOBS_URL}/{job_id}"
                else:
                    return None
            
            if not url.startswith('http'):
                url = f"{self.BASE_URL}{url}" if url.startswith('/') else f"{self.BASE_URL}/{url}"
            
            # Salary
            salary = item.get("salary", "") or item.get("compensation", "") or item.get("pay", "")
            if isinstance(salary, dict):
                salary = f"${salary.get('min', 0):,} - ${salary.get('max', 0):,}"
            elif isinstance(salary, (int, float)):
                salary = f"${salary:,}"
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                salary_range=str(salary) if salary else None,
                source=JobSource.LEVELSFYI,
                application_type=app_type,
                job_type="Full-time",
                tags=["levelsfyi", "salary_transparent"],
                raw_data=item,
            )
        except Exception:
            return None
