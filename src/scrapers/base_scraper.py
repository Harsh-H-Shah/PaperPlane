"""
Base scraper class - abstract interface for all job scrapers
"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from src.core.job import Job, JobSource, JobStatus
from src.utils.config import get_settings
from src.utils.database import get_db


class BaseScraper(ABC):
    """
    Abstract base class for job scrapers.
    Each source (LinkedIn, Simplify, etc.) has its own subclass.
    """
    
    SOURCE_NAME = "Base"
    SOURCE_TYPE = JobSource.OTHER
    
    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()
        self.jobs_found = 0
        self.jobs_new = 0
    
    @abstractmethod
    async def scrape(
        self,
        keywords: list[str] = None,
        location: str = None,
        limit: int = 50,
    ) -> list[Job]:
        """
        Scrape jobs from this source.
        
        Args:
            keywords: Job titles/keywords to search for
            location: Location filter
            limit: Maximum number of jobs to return
        
        Returns:
            List of Job objects
        """
        pass
    
    def get_search_keywords(self) -> list[str]:
        """Get search keywords from settings"""
        return self.settings.search.titles
    
    def get_locations(self) -> list[str]:
        """Get locations from settings"""
        return self.settings.search.locations
    
    def should_include_job(self, job: Job) -> bool:
        """
        Check if a job matches our filter criteria.
        """
        title_lower = job.title.lower()
        company_lower = job.company.lower()
        
        # Check excluded companies
        for excluded in self.settings.search.exclude_companies:
            if excluded.lower() in company_lower:
                return False
        
        # Check excluded keywords
        for excluded in self.settings.search.exclude_keywords:
            if excluded.lower() in title_lower:
                return False
        
        return True
    
    def save_job(self, job: Job) -> Optional[str]:
        """
        Save a job to the database.
        Returns job ID if new, None if already exists.
        """
        # Check if already exists
        existing = self.db.get_job_by_url(job.url)
        if existing:
            return None
        
        # Set source and status
        job.source = self.SOURCE_TYPE
        job.status = JobStatus.NEW
        job.discovered_at = datetime.now()
        
        # Save to database
        job_id = self.db.add_job(job)
        self.jobs_new += 1
        return job_id
    
    def save_jobs(self, jobs: list[Job]) -> int:
        """
        Save multiple jobs to database.
        Returns count of new jobs saved.
        """
        saved = 0
        for job in jobs:
            if self.should_include_job(job):
                if self.save_job(job):
                    saved += 1
        return saved
    
    def get_stats(self) -> dict:
        """Get scraping statistics"""
        return {
            "source": self.SOURCE_NAME,
            "jobs_found": self.jobs_found,
            "jobs_new": self.jobs_new,
        }
