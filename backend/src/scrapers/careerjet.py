"""
Careerjet Scraper - Web scraping approach (no API key required)
Scrapes job listings directly from careerjet.com
"""
import httpx

from typing import Optional
from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_string
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type


class CareerjetScraper(BaseScraper):
    SOURCE_NAME = "Careerjet"
    SOURCE_TYPE = JobSource.CAREERJET
    
    BASE_URL = "https://www.careerjet.com"
    SEARCH_URL = "https://www.careerjet.com/search/jobs"
    
    def __init__(self):
        super().__init__()
        # Conservative rate limiting
        self.rate_limiter.rpm = 15
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or self.get_search_keywords()
        location = location or "USA"
        
        # Search for each keyword to maximize results
        for keyword in keywords[:3]:  # Top 3 keywords
            if len(jobs) >= limit:
                break
            
            # Paginate through results
            for page in range(1, 4):  # Up to 3 pages per keyword
                if len(jobs) >= limit:
                    break
                
                page_jobs = await self._search_page(keyword, location, page)
                for job in page_jobs:
                    if self.should_include_job(job):
                        jobs.append(job)
                        if len(jobs) >= limit:
                            break
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)
        
        self.jobs_found = len(unique_jobs)
        print(f"   📋 Careerjet: Found {len(unique_jobs)} unique jobs")
        return unique_jobs[:limit]
    
    async def _search_page(self, keyword: str, location: str, page: int) -> list[Job]:
        jobs = []
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer": self.BASE_URL,
                }
                
                params = {
                    "s": keyword,
                    "l": location,
                    "p": page,
                    "sort": "date",  # Most recent first
                }
                
                response = await client.get(
                    self.SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=30,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    jobs = self._parse_search_results(response.text)
                    if page == 1:
                        print(f"      Careerjet: Found {len(jobs)} jobs for '{keyword}' page {page}")
                        
        except Exception as e:
            print(f"   ❌ Careerjet error: {e}")
        
        return jobs
    
    def _parse_search_results(self, html: str) -> list[Job]:
        """Parse job listings from Careerjet search results page"""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Careerjet job card patterns
        job_selectors = [
            'article.job',
            'div.job',
            'li[data-url]',
            'article[data-job-id]',
        ]
        
        for selector in job_selectors:
            cards = soup.select(selector)
            if cards:
                for card in cards:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                break
        
        # Fallback: try to find any job-like elements
        if not jobs:
            # Look for elements with job URLs
            job_links = soup.select('a[href*="/job/"], a[href*="/viewjob/"]')
            for link in job_links:
                parent = link.find_parent(['article', 'div', 'li'])
                if parent:
                    job = self._parse_job_card(parent)
                    if job:
                        jobs.append(job)
        
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a single job card"""
        try:
            # Title and link
            title_el = card.select_one('h2 a, h3 a, a.job-title, header a, a[title]')
            if not title_el:
                title_el = card.select_one('a')
            
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
            company_el = card.select_one('.company, .employer, [class*="company"], p.company')
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            
            # Location
            location_el = card.select_one('.location, [class*="location"], .workplace')
            location = location_el.get_text(strip=True) if location_el else "USA"
            
            # Salary
            salary_el = card.select_one('.salary, [class*="salary"]')
            salary = salary_el.get_text(strip=True) if salary_el else None
            
            # Date
            date_el = card.select_one('.date, time, [class*="date"]')
            date_str = date_el.get_text(strip=True) if date_el else ""
            posted_date = parse_date_string(date_str) if date_str else None
            
            # Description snippet
            desc_el = card.select_one('.desc, .description, p:not(.company):not(.location)')
            description = desc_el.get_text(strip=True)[:300] if desc_el else None
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                description=description,
                salary_range=salary,
                source=JobSource.CAREERJET,
                application_type=app_type,
                posted_date=posted_date,
                job_type="Full-time",
                tags=["careerjet"],
            )
        except Exception:
            return None
