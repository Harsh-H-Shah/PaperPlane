"""
Job Aggregator - combines results from multiple scrapers
"""

import asyncio
from typing import Optional
from datetime import datetime

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.simplify import SimplifyScraper
from src.scrapers.cvrve import CVRVEScraper
from src.scrapers.linkedin import LinkedInScraper
from src.core.job import Job
from src.utils.config import get_settings
from src.utils.database import get_db


class JobAggregator:
    """
    Aggregates job listings from multiple sources.
    Handles deduplication and filtering.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()
        self.scrapers: list[BaseScraper] = []
        self._setup_scrapers()
    
    def _setup_scrapers(self) -> None:
        """Initialize enabled scrapers"""
        scraper_config = self.settings.scrapers
        
        if scraper_config.simplify.enabled:
            self.scrapers.append(SimplifyScraper())
        
        if scraper_config.cvrve.enabled:
            self.scrapers.append(CVRVEScraper())
        
        if scraper_config.linkedin.enabled:
            self.scrapers.append(LinkedInScraper())
    
    async def scrape_all(
        self,
        keywords: list[str] = None,
        location: str = None,
        limit_per_source: int = 50,
    ) -> dict:
        """
        Scrape jobs from all enabled sources.
        
        Returns:
            Dictionary with stats and jobs
        """
        keywords = keywords or self.settings.search.titles
        locations = self.settings.search.locations
        location = location or (locations[0] if locations else "")
        
        all_jobs = []
        stats = {
            "sources": [],
            "total_found": 0,
            "total_new": 0,
            "duplicates_removed": 0,
        }
        
        # Run scrapers concurrently
        tasks = [
            scraper.scrape(keywords, location, limit_per_source)
            for scraper in self.scrapers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, Exception):
                print(f"Error from {scraper.SOURCE_NAME}: {result}")
                stats["sources"].append({
                    "name": scraper.SOURCE_NAME,
                    "found": 0,
                    "new": 0,
                    "error": str(result),
                })
            else:
                all_jobs.extend(result)
                scraper_stats = scraper.get_stats()
                stats["sources"].append({
                    "name": scraper.SOURCE_NAME,
                    "found": scraper_stats["jobs_found"],
                    "new": 0,  # Will update after dedup
                })
        
        stats["total_found"] = len(all_jobs)
        
        # Deduplicate
        unique_jobs = self._deduplicate(all_jobs)
        stats["duplicates_removed"] = len(all_jobs) - len(unique_jobs)
        
        # Save to database
        new_count = 0
        for job in unique_jobs:
            existing = self.db.get_job_by_url(job.url)
            if not existing:
                self.db.add_job(job)
                new_count += 1
        
        stats["total_new"] = new_count
        
        return {
            "stats": stats,
            "jobs": unique_jobs,
            "new_count": new_count,
        }
    
    def _deduplicate(self, jobs: list[Job]) -> list[Job]:
        """Remove duplicate jobs based on URL"""
        seen_urls = set()
        unique = []
        
        for job in jobs:
            # Normalize URL
            url = job.url.lower().rstrip('/')
            
            if url not in seen_urls:
                seen_urls.add(url)
                unique.append(job)
        
        return unique
    
    async def scrape_source(
        self,
        source: str,
        keywords: list[str] = None,
        limit: int = 50,
    ) -> list[Job]:
        """Scrape from a specific source"""
        source_lower = source.lower()
        
        scraper = None
        if source_lower == "simplify":
            scraper = SimplifyScraper()
        elif source_lower == "cvrve":
            scraper = CVRVEScraper()
        elif source_lower == "linkedin":
            scraper = LinkedInScraper()
        
        if not scraper:
            raise ValueError(f"Unknown source: {source}")
        
        keywords = keywords or self.settings.search.titles
        jobs = await scraper.scrape(keywords, limit=limit)
        
        # Save new jobs
        for job in jobs:
            scraper.save_job(job)
        
        return jobs
    
    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        """Get jobs ready for application"""
        return self.db.get_pending_jobs(limit)


async def run_scraper(
    sources: list[str] = None,
    limit: int = 50,
) -> dict:
    """
    Convenience function to run the scraper.
    
    Args:
        sources: List of sources to scrape (or all if None)
        limit: Max jobs per source
    
    Returns:
        Scraping results and stats
    """
    aggregator = JobAggregator()
    
    if sources:
        all_jobs = []
        for source in sources:
            jobs = await aggregator.scrape_source(source, limit=limit)
            all_jobs.extend(jobs)
        return {"jobs": all_jobs, "count": len(all_jobs)}
    else:
        return await aggregator.scrape_all(limit_per_source=limit)
