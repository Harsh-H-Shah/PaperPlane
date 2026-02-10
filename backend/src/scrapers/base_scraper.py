from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
import time

from src.core.job import Job, JobSource, JobStatus
from src.utils.config import get_settings
from src.utils.database import get_db
from src.scrapers.job_filter import JobFilter
from src.scrapers.scraper_utils import (
    ScrapeResult, RetryConfig, get_metrics, get_rate_limiter
)


class BaseScraper(ABC):
    SOURCE_NAME = "Base"
    SOURCE_TYPE = JobSource.OTHER
    
    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()
        self.job_filter = JobFilter(
            max_years_experience=3,
            exclude_companies=self.settings.search.exclude_companies,
            max_days_old=self.settings.search.max_days_old
        )
        self.retry_config = RetryConfig(max_retries=3, base_delay=2.0)
        self.rate_limiter = get_rate_limiter(self.SOURCE_NAME)
        self.metrics = get_metrics(self.SOURCE_NAME)
        
        self.jobs_found = 0
        self.jobs_new = 0
        self.jobs_filtered = 0
    
    @abstractmethod
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        pass
    
    async def scrape_with_metrics(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> ScrapeResult:
        start_time = time.time()
        
        try:
            await self.rate_limiter.acquire()
            jobs = await self.scrape(keywords, location, limit)
            duration = time.time() - start_time
            
            result = ScrapeResult(
                success=True,
                jobs_found=len(jobs),
                jobs_new=self.jobs_new,
                jobs_filtered=self.jobs_filtered,
                duration_seconds=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            result = ScrapeResult(
                success=False,
                error=str(e),
                duration_seconds=duration
            )
        
        self.metrics.record_run(result)
        return result
    
    def get_search_keywords(self) -> list[str]:
        return self.settings.search.titles
    
    def get_locations(self) -> list[str]:
        return self.settings.search.locations
    
    def should_include_job(self, job: Job) -> bool:
        title_lower = job.title.lower()
        company_lower = job.company.lower()
        
        for excluded in self.settings.search.exclude_companies:
            if excluded.lower() in company_lower:
                self.jobs_filtered += 1
                return False
        
        for excluded in self.settings.search.exclude_keywords:
            if excluded.lower() in title_lower:
                self.jobs_filtered += 1
                return False
        
        should_include, reason = self.job_filter.should_include(job)
        if not should_include:
            self.jobs_filtered += 1
        
        return should_include
    
    def save_job(self, job: Job) -> Optional[str]:
        existing = self.db.get_job_by_url(job.url)
        if existing:
            return None
        
        job.source = self.SOURCE_TYPE
        job.status = JobStatus.NEW
        job.discovered_at = datetime.now()
        
        job_id = self.db.add_job(job)
        self.jobs_new += 1
        return job_id
    
    def save_jobs(self, jobs: list[Job]) -> int:
        saved = 0
        for job in jobs:
            if self.should_include_job(job):
                if self.save_job(job):
                    saved += 1
        return saved
    
    def get_stats(self) -> dict:
        return {
            "source": self.SOURCE_NAME,
            "jobs_found": self.jobs_found,
            "jobs_new": self.jobs_new,
            "jobs_filtered": self.jobs_filtered,
            "metrics": self.metrics.to_dict()
        }
    
    def reset_counters(self):
        self.jobs_found = 0
        self.jobs_new = 0
        self.jobs_filtered = 0
