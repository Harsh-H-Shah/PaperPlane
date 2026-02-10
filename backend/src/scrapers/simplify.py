import httpx
from typing import Optional
from datetime import datetime

from src.scrapers.base_scraper import BaseScraper
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type


class SimplifyScraper(BaseScraper):
    SOURCE_NAME = "Simplify"
    SOURCE_TYPE = JobSource.SIMPLIFY
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2025-Internships/dev/.github/scripts/listings.json"
    NEW_GRAD_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or self.get_search_keywords()
        
        try:
            new_grad_jobs = await self._fetch_listings(self.NEW_GRAD_URL, keywords, limit)
            jobs.extend(new_grad_jobs)
        except Exception as e:
            print(f"Error fetching Simplify new grad: {e}")
        
        if len(jobs) < limit:
            try:
                intern_jobs = await self._fetch_listings(self.GITHUB_RAW_URL, keywords, limit - len(jobs))
                jobs.extend(intern_jobs)
            except Exception as e:
                print(f"Error fetching Simplify internships: {e}")
        
        self.jobs_found = len(jobs)
        return jobs[:limit]
    
    async def _fetch_listings(self, url: str, keywords: list[str], limit: int) -> list[Job]:
        jobs = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            
            if response.status_code != 200:
                return jobs
            
            data = response.json()
            
            for item in data:
                title = item.get("title", "")
                if not self._matches_keywords(title, keywords):
                    continue
                
                job = self._parse_listing(item)
                if job and self.should_include_job(job):
                    jobs.append(job)
                    
                    if len(jobs) >= limit:
                        break
        
        return jobs
    
    def _matches_keywords(self, title: str, keywords: list[str]) -> bool:
        title_lower = title.lower()
        for kw in keywords:
            if kw.lower() in title_lower:
                return True
        return False
    
    def _parse_listing(self, item: dict) -> Optional[Job]:
        try:
            url = item.get("url", "")
            if not url:
                return None
            
            app_type, _ = detect_application_type(url)
            
            locations = item.get("locations", [])
            location_str = ", ".join(locations) if locations else "Remote"
            
            date_str = item.get("date_posted", "")
            posted_date = None
            if date_str:
                try:
                    posted_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    pass
            
            return Job(
                title=item.get("title", "Software Engineer"),
                company=item.get("company_name", "Unknown"),
                location=location_str,
                url=url,
                apply_url=url,
                application_type=app_type,
                posted_date=posted_date,
                job_type="Full-time",
                tags=item.get("terms", []),
                raw_data=item,
                source=JobSource.SIMPLIFY,
            )
        except Exception as e:
            print(f"Error parsing Simplify listing: {e}")
            return None
