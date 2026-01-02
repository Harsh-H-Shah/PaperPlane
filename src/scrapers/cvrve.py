"""
CVRVE scraper - uses CVRVE's public GitHub job data
https://github.com/cvrve/Summer2025-Internships

CVRVE maintains an extensive list of tech job postings.
"""

import httpx
from typing import Optional
from datetime import datetime
import re

from src.scrapers.base_scraper import BaseScraper
from src.core.job import Job, JobSource, ApplicationType
from src.classifiers.detector import detect_application_type


class CVRVEScraper(BaseScraper):
    """
    Scraper for CVRVE job listings.
    Uses their public GitHub repository.
    """
    
    SOURCE_NAME = "CVRVE"
    SOURCE_TYPE = JobSource.CVRVE
    
    # CVRVE GitHub data URLs
    LISTINGS_URL = "https://raw.githubusercontent.com/cvrve/Summer2025-Internships/dev/.github/scripts/listings.json"
    NEW_GRAD_URL = "https://raw.githubusercontent.com/cvrve/New-Grad/dev/.github/scripts/listings.json"
    
    async def scrape(
        self,
        keywords: list[str] = None,
        location: str = None,
        limit: int = 50,
    ) -> list[Job]:
        """
        Scrape jobs from CVRVE's GitHub data.
        """
        jobs = []
        keywords = keywords or self.get_search_keywords()
        
        # Try new grad first
        try:
            new_grad_jobs = await self._fetch_listings(self.NEW_GRAD_URL, keywords, limit)
            jobs.extend(new_grad_jobs)
        except Exception as e:
            print(f"Error fetching CVRVE new grad: {e}")
        
        # Also try internship listings
        if len(jobs) < limit:
            try:
                intern_jobs = await self._fetch_listings(
                    self.LISTINGS_URL,
                    keywords,
                    limit - len(jobs)
                )
                jobs.extend(intern_jobs)
            except Exception as e:
                print(f"Error fetching CVRVE internships: {e}")
        
        self.jobs_found = len(jobs)
        return jobs[:limit]
    
    async def _fetch_listings(
        self,
        url: str,
        keywords: list[str],
        limit: int
    ) -> list[Job]:
        """Fetch and parse CVRVE listings"""
        jobs = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            
            if response.status_code != 200:
                return jobs
            
            data = response.json()
            
            for item in data:
                # Check keywords
                title = item.get("title", "") or item.get("role", "")
                company = item.get("company_name", "") or item.get("company", "")
                
                if not self._matches_keywords(title, keywords):
                    continue
                
                # Parse job
                job = self._parse_listing(item)
                if job and self.should_include_job(job):
                    jobs.append(job)
                    
                    if len(jobs) >= limit:
                        break
        
        return jobs
    
    def _matches_keywords(self, title: str, keywords: list[str]) -> bool:
        """Check if title matches keywords"""
        title_lower = title.lower()
        for kw in keywords:
            if kw.lower() in title_lower:
                return True
        return False
    
    def _parse_listing(self, item: dict) -> Optional[Job]:
        """Parse a CVRVE listing into a Job object"""
        try:
            # Get URL
            url = item.get("url", "") or item.get("apply_link", "")
            if not url:
                return None
            
            # Detect application type
            app_type, _ = detect_application_type(url)
            
            # Parse location
            locations = item.get("locations", [])
            if isinstance(locations, list):
                location_str = ", ".join(locations) if locations else "Remote"
            else:
                location_str = str(locations) or "Remote"
            
            # Get title and company
            title = item.get("title", "") or item.get("role", "Software Engineer")
            company = item.get("company_name", "") or item.get("company", "Unknown")
            
            # Parse date
            date_str = item.get("date_posted", "") or item.get("date", "")
            posted_date = None
            if date_str:
                try:
                    posted_date = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    try:
                        posted_date = datetime.strptime(date_str, "%m/%d/%Y")
                    except:
                        pass
            
            return Job(
                title=title,
                company=company,
                location=location_str,
                url=url,
                apply_url=url,
                application_type=app_type,
                posted_date=posted_date,
                job_type="Full-time",
                tags=item.get("terms", []) or item.get("tags", []),
                raw_data=item,
            )
        except Exception as e:
            print(f"Error parsing CVRVE listing: {e}")
            return None
