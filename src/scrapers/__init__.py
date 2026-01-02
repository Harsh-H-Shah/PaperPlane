"""
Scrapers Package - Job discovery from multiple sources

Supported sources:
- Simplify Jobs (simplify.jobs) - Public API
- CVRVE (cvrve.me) - GitHub-based job list
- LinkedIn (requires cookies)
- Jobright.ai
- Company career pages
"""

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.simplify import SimplifyScraper
from src.scrapers.cvrve import CVRVEScraper
from src.scrapers.aggregator import JobAggregator

__all__ = [
    "BaseScraper",
    "SimplifyScraper",
    "CVRVEScraper",
    "JobAggregator",
]
