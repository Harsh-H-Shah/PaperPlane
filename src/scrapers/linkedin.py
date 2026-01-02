"""
LinkedIn Jobs scraper

NOTE: LinkedIn is protective of their data. This scraper:
1. Requires session cookies from a logged-in browser
2. Uses minimal requests to avoid rate limiting
3. May break if LinkedIn changes their API

For best results, use LinkedIn Easy Apply jobs.
"""

import httpx
from typing import Optional
from datetime import datetime
import json

from src.scrapers.base_scraper import BaseScraper
from src.core.job import Job, JobSource, ApplicationType
from src.utils.config import get_settings


class LinkedInScraper(BaseScraper):
    """
    Scraper for LinkedIn Jobs.
    Requires authentication cookies.
    """
    
    SOURCE_NAME = "LinkedIn"
    SOURCE_TYPE = JobSource.LINKEDIN
    
    # LinkedIn API endpoints
    SEARCH_URL = "https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards"
    JOB_URL = "https://www.linkedin.com/jobs/view/{job_id}"
    
    def __init__(self):
        super().__init__()
        self.cookies = self._get_cookies()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
            "x-li-lang": "en_US",
            "x-restli-protocol-version": "2.0.0",
        }
    
    def _get_cookies(self) -> dict:
        """Get LinkedIn cookies from settings"""
        settings = get_settings()
        cookies = {}
        
        if settings.linkedin_li_at:
            cookies["li_at"] = settings.linkedin_li_at
        if settings.linkedin_jsessionid:
            cookies["JSESSIONID"] = settings.linkedin_jsessionid
        
        return cookies
    
    def is_authenticated(self) -> bool:
        """Check if we have LinkedIn cookies"""
        return bool(self.cookies.get("li_at"))
    
    async def scrape(
        self,
        keywords: list[str] = None,
        location: str = None,
        limit: int = 25,
    ) -> list[Job]:
        """
        Scrape jobs from LinkedIn.
        
        NOTE: Without cookies, this will return empty results.
        """
        if not self.is_authenticated():
            print("⚠️ LinkedIn cookies not configured. Add LINKEDIN_LI_AT to .env")
            print("To get cookies: Login to LinkedIn, open DevTools, copy li_at cookie")
            return []
        
        jobs = []
        keywords = keywords or self.get_search_keywords()
        location = location or (self.get_locations()[0] if self.get_locations() else "")
        
        # Build search query
        keyword_str = " OR ".join(keywords)
        
        try:
            jobs = await self._search_jobs(keyword_str, location, limit)
        except Exception as e:
            print(f"LinkedIn scrape error: {e}")
        
        self.jobs_found = len(jobs)
        return jobs
    
    async def _search_jobs(
        self, 
        keywords: str, 
        location: str, 
        limit: int
    ) -> list[Job]:
        """Search LinkedIn jobs"""
        jobs = []
        
        # Note: This is a simplified version
        # Full implementation would use LinkedIn's Voyager API
        # which requires reverse-engineering their requests
        
        params = {
            "keywords": keywords,
            "location": location,
            "f_AL": "true",  # Easy Apply only
            "f_TP": "1",  # Past 24 hours
            "start": 0,
            "count": min(limit, 25),
        }
        
        try:
            async with httpx.AsyncClient(cookies=self.cookies) as client:
                # This is a placeholder - actual LinkedIn scraping
                # requires more complex API calls
                response = await client.get(
                    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                    params=params,
                    headers=self.headers,
                    timeout=30,
                )
                
                if response.status_code == 200:
                    # Parse HTML response for job cards
                    jobs = self._parse_job_cards(response.text)
                    
        except Exception as e:
            print(f"LinkedIn API error: {e}")
        
        return jobs[:limit]
    
    def _parse_job_cards(self, html: str) -> list[Job]:
        """Parse job cards from LinkedIn HTML"""
        jobs = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            cards = soup.find_all('div', class_='job-search-card')
            
            for card in cards:
                try:
                    # Extract job details
                    title_el = card.find('h3', class_='base-search-card__title')
                    company_el = card.find('h4', class_='base-search-card__subtitle')
                    location_el = card.find('span', class_='job-search-card__location')
                    link_el = card.find('a', class_='base-card__full-link')
                    
                    if not all([title_el, company_el, link_el]):
                        continue
                    
                    url = link_el.get('href', '')
                    
                    # Check if Easy Apply
                    is_easy_apply = 'Easy Apply' in card.get_text()
                    
                    job = Job(
                        title=title_el.get_text(strip=True),
                        company=company_el.get_text(strip=True),
                        location=location_el.get_text(strip=True) if location_el else "",
                        url=url,
                        apply_url=url,
                        application_type=ApplicationType.LINKEDIN_EASY if is_easy_apply else ApplicationType.CUSTOM,
                    )
                    
                    if self.should_include_job(job):
                        jobs.append(job)
                        
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Error parsing LinkedIn HTML: {e}")
        
        return jobs
