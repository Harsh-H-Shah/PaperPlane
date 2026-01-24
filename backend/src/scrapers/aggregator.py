import asyncio
from typing import Optional
from datetime import datetime

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.simplify import SimplifyScraper
from src.scrapers.cvrve import CVRVEScraper
from src.scrapers.jobright import JobrightScraper
from src.scrapers.additional_sources import BuiltInScraper
from src.scrapers.link_validator import get_link_validator, get_incremental_scraper
from src.core.job import Job
from src.utils.config import get_settings
from src.utils.database import get_db


class JobAggregator:
    def __init__(self, validate_links: bool = False):
        self.settings = get_settings()
        self.db = get_db()
        self.validate_links = validate_links
        self.scrapers: list[BaseScraper] = []
        self.incremental = get_incremental_scraper()
        self.validator = get_link_validator() if validate_links else None
        self._setup_scrapers()
        self.incremental.load_from_db(self.db)
    
    def _setup_scrapers(self) -> None:
        scraper_config = self.settings.scrapers
        
        if scraper_config.simplify.enabled:
            self.scrapers.append(SimplifyScraper())
        
        if scraper_config.cvrve.enabled:
            self.scrapers.append(CVRVEScraper())
        
        
        self.scrapers.append(JobrightScraper())
        self.scrapers.append(BuiltInScraper())
    
    async def scrape_all(self, keywords: list[str] = None, location: str = None, limit_per_source: int = 50) -> dict:
        keywords = keywords or self.settings.search.titles
        locations = self.settings.search.locations
        location = location or (locations[0] if locations else "")
        
        all_jobs = []
        stats = {
            "sources": [],
            "total_found": 0,
            "total_new": 0,
            "duplicates_removed": 0,
            "invalid_links": 0,
            "already_seen": 0,
        }
        
        tasks = [scraper.scrape(keywords, location, limit_per_source) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, Exception):
                print(f"Error from {scraper.SOURCE_NAME}: {result}")
                stats["sources"].append({"name": scraper.SOURCE_NAME, "found": 0, "new": 0, "error": str(result)})
            else:
                all_jobs.extend(result)
                scraper_stats = scraper.get_stats()
                stats["sources"].append({
                    "name": scraper.SOURCE_NAME,
                    "found": scraper_stats["jobs_found"],
                    "filtered": scraper_stats.get("jobs_filtered", 0),
                    "new": 0
                })
        
        stats["total_found"] = len(all_jobs)
        
        # Deduplicate and filter existing in one go
        unique_candidates = self._deduplicate_candidates(all_jobs)
        candidate_urls = [j.url for j in unique_candidates]
        existing_urls = self.db.filter_existing_urls(candidate_urls)
        
        new_jobs_candidates = [j for j in unique_candidates if j.url not in existing_urls]
        stats["already_seen"] = len(unique_candidates) - len(new_jobs_candidates)
        
        # Content-based duplication check
        content_duplicates = self.db.check_content_duplicates(new_jobs_candidates)
        new_jobs_filtered = [j for j in new_jobs_candidates if j.url not in content_duplicates]
        stats["duplicates_removed"] += len(new_jobs_candidates) - len(new_jobs_filtered)
        
        # Incremental filter (double check, though DB check covers mostly everything)
        new_jobs = self.incremental.filter_new_jobs(new_jobs_filtered)
        
        if self.validate_links and new_jobs:
            if not self.validator:
                self.validator = get_link_validator()
            valid_jobs, invalid = await self.validator.validate_jobs(new_jobs)
            stats["invalid_links"] = len(invalid)
            new_jobs = valid_jobs
        
        # Bulk insert
        new_count = self.db.add_jobs_bulk(new_jobs)
        stats["total_new"] = new_count
        
        return {"stats": stats, "jobs": new_jobs, "new_count": new_count}
    
    def _deduplicate_candidates(self, jobs: list[Job]) -> list[Job]:
        seen_urls = set()
        unique = []
        
        for job in jobs:
            url = job.url.lower().rstrip('/')
            if url not in seen_urls:
                seen_urls.add(url)
                unique.append(job)
        
        return unique
    
    async def scrape_source(self, source: str, keywords: list[str] = None, limit: int = 50) -> list[Job]:
        source_lower = source.lower()
        
        scraper_map = {
            "simplify": SimplifyScraper,
            "cvrve": CVRVEScraper,
            "jobright": JobrightScraper,
            "builtin": BuiltInScraper,
        }
        
        scraper_class = scraper_map.get(source_lower)
        if not scraper_class:
            raise ValueError(f"Unknown source: {source}. Available: {list(scraper_map.keys())}")
        
        scraper = scraper_class()
        keywords = keywords or self.settings.search.titles
        jobs = await scraper.scrape(keywords, limit=limit)
        
        raw_count = len(jobs)
        
        # Initial memory-based filtering
        new_jobs = self.incremental.filter_new_jobs(jobs)
        
        if self.validate_links:
            if not self.validator:
                self.validator = get_link_validator()
            valid_jobs, invalid = await self.validator.validate_jobs(new_jobs)
            print(f"Validated {len(new_jobs)} jobs: {len(valid_jobs)} valid, {len(invalid)} invalid")
            new_jobs = valid_jobs
        
        # Check DB existence in bulk
        candidate_urls = [j.url for j in new_jobs]
        existing_urls = self.db.filter_existing_urls(candidate_urls)
        final_new_jobs = [j for j in new_jobs if j.url not in existing_urls]
        
        # Content-based check
        content_duplicates = self.db.check_content_duplicates(final_new_jobs)
        final_new_jobs = [j for j in final_new_jobs if j.url not in content_duplicates]
        
        self.db.add_jobs_bulk(final_new_jobs)
        
        return final_new_jobs, raw_count
    
    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        return self.db.get_pending_jobs(limit)
    
    def get_stats(self) -> dict:
        return {
            "seen_urls": self.incremental.seen_count,
            "scrapers": [s.SOURCE_NAME for s in self.scrapers],
        }


async def run_scraper(sources: list[str] = None, limit: int = 50, validate: bool = True) -> dict:
    aggregator = JobAggregator(validate_links=validate)
    
    if sources:
        all_jobs = []
        for source in sources:
            jobs, _ = await aggregator.scrape_source(source, limit=limit)
            all_jobs.extend(jobs)
        return {"jobs": all_jobs, "count": len(all_jobs)}
    else:
        return await aggregator.scrape_all(limit_per_source=limit)
