import httpx
from typing import Optional

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_value
from src.scrapers.job_filter import is_software_role
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type
from src.utils.logger import logger


class SimplifyScraper(BaseScraper):
    SOURCE_NAME = "Simplify"
    SOURCE_TYPE = JobSource.SIMPLIFY
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"
    NEW_GRAD_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []

        try:
            new_grad_jobs = await self._fetch_listings(self.NEW_GRAD_URL, limit)
            jobs.extend(new_grad_jobs)
        except Exception as e:
            logger.error(f"Error fetching Simplify new grad: {e}")

        if len(jobs) < limit:
            try:
                intern_jobs = await self._fetch_listings(self.GITHUB_RAW_URL, limit - len(jobs))
                jobs.extend(intern_jobs)
            except Exception as e:
                logger.error(f"Error fetching Simplify internships: {e}")

        self.jobs_found = len(jobs)
        return jobs[:limit]

    async def _fetch_listings(self, url: str, limit: int) -> list[Job]:
        jobs = []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            
            if response.status_code != 200:
                return jobs
            
            data = response.json()

            for item in data:
                # Skip inactive/expired listings and non-software roles.
                if item.get("active") is False:
                    continue
                if not is_software_role(item.get("title", "")):
                    continue

                job = self._parse_listing(item)
                if job and self.should_include_job(job):
                    jobs.append(job)

                    if len(jobs) >= limit:
                        break

        return jobs

    def _parse_listing(self, item: dict) -> Optional[Job]:
        try:
            url = item.get("url", "")
            if not url:
                return None
            
            app_type, _ = detect_application_type(url)
            
            locations = item.get("locations", [])
            location_str = ", ".join(locations) if locations else "Remote"
            
            posted_date = parse_date_value(item.get("date_posted"))
            
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
            logger.error(f"Error parsing Simplify listing: {e}")
            return None
