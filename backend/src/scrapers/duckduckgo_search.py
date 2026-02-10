"""
DuckDuckGo Search Scraper - Completely free, no API key needed.
Uses DuckDuckGo to find companies and careers pages semantically.
"""
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urlparse
from datetime import datetime

try:
    from duckduckgo_search import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False
    DDGS = None

from src.scrapers.base_scraper import BaseScraper
from src.core.job import Job, JobSource, ApplicationType
from src.scrapers.job_filter import JobFilter
from src.utils.logger import logger


class DuckDuckGoScraper(BaseScraper):
    """
    Uses DuckDuckGo search (completely free, no API key needed)
    to find companies and their careers pages.
    """
    SOURCE_NAME = "DuckDuckGo"
    SOURCE_TYPE = JobSource.OTHER
    
    def __init__(self):
        super().__init__()
        if not DDG_AVAILABLE:
            raise ImportError("duckduckgo-search not installed. Run: pip install duckduckgo-search")
        self.ddgs = DDGS()
        self.job_filter = JobFilter()
    
    async def scrape(self, keywords: List[str] = None, location: str = None, limit: int = 50) -> List[Job]:
        """
        Search for companies matching keywords, then find their careers pages.
        """
        keywords = keywords or self.get_search_keywords()
        location = location or "United States"
        
        jobs = []
        
        # Search for companies
        for keyword in keywords[:3]:  # Limit to avoid rate limits
            if len(jobs) >= limit:
                break
            
            query = f"{keyword} companies {location}"
            logger.info(f"   🔍 DuckDuckGo: Searching for '{query}'...")
            
            try:
                # Search for companies
                company_results = await self._search_companies(query, num_results=20)
                
                # For each company, find careers page and extract jobs
                for company in company_results[:10]:  # Limit companies per keyword
                    if len(jobs) >= limit:
                        break
                    
                    careers_url = await self._find_careers_page(company["domain"])
                    if careers_url:
                        # Extract jobs from careers page
                        company_jobs = await self._extract_jobs_from_careers(
                            careers_url, company["name"], keyword
                        )
                        jobs.extend(company_jobs)
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"   ❌ DuckDuckGo search error for '{query}': {e}")
                continue
        
        # Filter jobs
        filtered_jobs = [job for job in jobs if self.should_include_job(job)]
        self.jobs_found = len(filtered_jobs)
        
        return filtered_jobs[:limit]
    
    async def _search_companies(self, query: str, num_results: int = 20) -> List[Dict]:
        """Search for companies using DuckDuckGo"""
        results = []
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ddgs_results = await loop.run_in_executor(
                None,
                lambda: list(self.ddgs.text(query, max_results=num_results))
            )
            
            for result in ddgs_results:
                domain = self._extract_domain(result.get("href", ""))
                if domain:
                    results.append({
                        "name": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", ""),
                        "domain": domain
                    })
        
        except Exception as e:
            logger.error(f"   ⚠️ DuckDuckGo search error: {e}")
        
        return results
    
    async def _find_careers_page(self, company_domain: str) -> Optional[str]:
        """Find careers page for a company"""
        if not company_domain:
            return None
        
        # Try multiple search queries
        queries = [
            f"{company_domain} careers",
            f"{company_domain} jobs",
            f"site:{company_domain} careers",
            f"site:{company_domain} jobs"
        ]
        
        for query in queries:
            try:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None,
                    lambda: list(self.ddgs.text(query, max_results=5))
                )
                
                for result in results:
                    url = result.get("href", "").lower()
                    # Check if it's a careers/jobs page
                    if any(keyword in url for keyword in ["careers", "jobs", "join", "hiring", "work-with-us"]):
                        return result.get("href", "")
                
                # Small delay between queries
                await asyncio.sleep(0.5)
            
            except Exception as e:
                logger.debug(f"   ⚠️ Error finding careers page for {company_domain}: {e}")
                continue
        
        return None
    
    async def _extract_jobs_from_careers(self, careers_url: str, company_name: str, keyword: str) -> List[Job]:
        """
        Extract jobs from a careers page.
        This is a simplified version - you can enhance it with more sophisticated parsing.
        """
        jobs = []
        
        try:
            # Use existing browser session if available
            from src.utils.browser import browser_session
            
            async with browser_session() as (manager, page):
                await page.goto(careers_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)  # Wait for dynamic content
                
                # Extract job listings (simplified - can be enhanced)
                job_elements = await page.evaluate("""
                    () => {
                        const jobs = [];
                        // Look for common job listing patterns
                        const selectors = [
                            'a[href*="job"]',
                            'a[href*="career"]',
                            'a[href*="position"]',
                            '[class*="job"]',
                            '[class*="position"]',
                            '[id*="job"]'
                        ];
                        
                        selectors.forEach(selector => {
                            document.querySelectorAll(selector).forEach(el => {
                                const text = el.textContent?.trim() || '';
                                const href = el.href || el.getAttribute('href') || '';
                                if (text.length > 10 && text.length < 200) {
                                    jobs.push({
                                        title: text,
                                        url: href.startsWith('http') ? href : new URL(href, window.location.href).href
                                    });
                                }
                            });
                        });
                        
                        return jobs.slice(0, 20); // Limit results
                    }
                """)
                
                for job_data in job_elements:
                    # Create Job object
                    job = Job(
                        url=job_data.get("url", careers_url),
                        title=job_data.get("title", f"{keyword} at {company_name}"),
                        company=company_name,
                        source=JobSource.OTHER,
                        description=f"Job found on {company_name} careers page",
                        posted_at=datetime.now()
                    )
                    
                    # Detect application type
                    app_type, _ = self._detect_application_type(job.url)
                    job.application_type = app_type
                    
                    jobs.append(job)
        
        except Exception as e:
            logger.debug(f"   ⚠️ Error extracting jobs from {careers_url}: {e}")
        
        return jobs
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            # Remove port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            return domain if domain else None
        except:
            return None
    
    def _detect_application_type(self, url: str) -> tuple:
        """Detect application type from URL"""
        from src.classifiers.detector import detect_application_type
        try:
            return detect_application_type(url)
        except:
            return ApplicationType.UNKNOWN, 0.0

