"""
Greenhouse Jobs Scraper - Fetches jobs from Greenhouse company job boards
Uses the public Greenhouse Job Board API (no authentication required)
API Docs: https://developers.greenhouse.io/job-board.html
"""
import httpx
import asyncio
from typing import Optional
from datetime import datetime

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_string
from src.core.job import Job, JobSource, ApplicationType
from src.classifiers.detector import detect_application_type


# Curated list of tech companies using Greenhouse
# Board tokens can be found in company career page URLs: boards.greenhouse.io/{token}
GREENHOUSE_BOARDS = [
    # FAANG-adjacent
    "airbnb", "stripe", "dropbox", "figma", "notion", "airtable",
    "doordash", "instacart", "lyft", "coinbase", "robinhood",
    # Enterprise
    "twilio", "datadog", "mongodb", "snowflake", "cloudflare",
    # Startups
    "retool", "vercel", "supabase", "linear", "loom", "mercury",
    "openai", "anthropic", "huggingface", "cohere", "stability",
    # Fintech
    "plaid", "brex", "ramp", "chime", "affirm",
    # Security
    "crowdstrike", "1password", "snyk",
    # Other notable
    "discord", "reddit", "duolingo", "canva", "miro",
]


class GreenhouseJobsScraper(BaseScraper):
    SOURCE_NAME = "GreenhouseJobs"
    SOURCE_TYPE = JobSource.GREENHOUSE_JOBS
    
    API_BASE = "https://boards-api.greenhouse.io/v1/boards"
    
    def __init__(self, board_tokens: list[str] = None):
        super().__init__()
        self.board_tokens = board_tokens or GREENHOUSE_BOARDS
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or self.get_search_keywords()
        
        # Scrape from multiple boards concurrently
        tasks = []
        for token in self.board_tokens:
            if len(jobs) >= limit:
                break
            tasks.append(self._fetch_board_jobs(token, keywords))
        
        # Run in batches to avoid overwhelming
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    continue
                for job in result:
                    if self.should_include_job(job):
                        jobs.append(job)
                        if len(jobs) >= limit:
                            break
            
            if len(jobs) >= limit:
                break
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        self.jobs_found = len(jobs)
        print(f"   📋 GreenhouseJobs: Found {len(jobs)} jobs from {len(self.board_tokens)} boards")
        return jobs[:limit]
    
    async def _fetch_board_jobs(self, board_token: str, keywords: list[str]) -> list[Job]:
        jobs = []
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.API_BASE}/{board_token}/jobs"
                params = {"content": "true"}
                
                headers = {
                    "User-Agent": "PaperPlane/1.0",
                    "Accept": "application/json",
                }
                
                response = await client.get(url, params=params, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    job_list = data.get("jobs", [])
                    
                    for item in job_list:
                        # Filter by keywords
                        title = item.get("title", "").lower()
                        if not any(kw.lower() in title for kw in keywords):
                            continue
                        
                        job = self._parse_job(item, board_token)
                        if job:
                            jobs.append(job)
                            
        except httpx.TimeoutException:
            pass  # Board may not exist or be slow
        except Exception:
            pass  # Skip boards that fail
        
        return jobs
    
    def _parse_job(self, item: dict, board_token: str) -> Optional[Job]:
        try:
            job_id = item.get("id")
            title = item.get("title", "")
            
            # Get location
            location_data = item.get("location", {})
            location = location_data.get("name", "Remote") if isinstance(location_data, dict) else "Remote"
            
            # Build URLs
            absolute_url = item.get("absolute_url", "")
            if not absolute_url:
                absolute_url = f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"
            
            # Parse date
            updated_at = item.get("updated_at", "")
            posted_date = parse_date_string(updated_at) if updated_at else None
            
            # Get departments
            departments = item.get("departments", [])
            dept_names = [d.get("name", "") for d in departments if d.get("name")]
            
            # Content/description
            content = item.get("content", "")
            
            return Job(
                title=title,
                company=board_token.replace("-", " ").title(),  # Best guess at company name
                location=location,
                url=absolute_url,
                apply_url=absolute_url,
                description=content[:500] if content else None,
                source=JobSource.GREENHOUSE_JOBS,
                application_type=ApplicationType.GREENHOUSE,
                posted_date=posted_date,
                job_type="Full-time",
                tags=["greenhouse", board_token] + dept_names[:2],
                external_id=str(job_id),
                raw_data={
                    "board_token": board_token,
                    "internal_job_id": item.get("internal_job_id"),
                    "requisition_id": item.get("requisition_id"),
                },
            )
        except Exception as e:
            return None
