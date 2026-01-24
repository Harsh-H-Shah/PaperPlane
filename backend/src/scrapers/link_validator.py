import asyncio
import httpx
from typing import Optional
from datetime import datetime
from src.core.job import Job


class LinkValidator:
    DEAD_LINK_PATTERNS = [
        "job not found", "job does not exist", "position has been filled",
        "this job is no longer available", "expired", "page not found",
        "404", "job has been removed", "no longer accepting", "closed"
    ]
    
    REDIRECT_DOMAINS = [
        "jobright.ai/jobs/info",
        "simplify.jobs",
    ]
    
    PHISHING_KEYWORDS = [
        "telegram", "whatsapp", "kindly", "check processing", 
        "bank account", "payment", "money order", "typing", "data entry",
        "confidential", "verification code", "wire transfer",
        "google hangouts", "icq", "skype id",
        "yahoo messenger", "investment", "cryptocurrency",
    ]
    
    SUSPICIOUS_DOMAINS = [
        "blogspot", "wordpress", "wixsite", "weebly",
        "yolasite", "jimdo", "site123", "bravenet",
        "angelfire", "tripod", "geocities",
    ]
    
    def __init__(self, timeout: float = 10.0, max_concurrent: int = 10):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cache: dict[str, bool] = {}
    
    async def is_valid(self, url: str) -> tuple[bool, Optional[str], Optional[str]]:
        if url in self._cache:
            return self._cache[url]
        
        # Check suspicious domains first
        url_lower = url.lower()
        for domain in self.SUSPICIOUS_DOMAINS:
            if domain in url_lower:
                 result = (False, f"Suspicious domain: {domain}", None)
                 self._cache[url] = result
                 return result
        
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    response = await client.head(url, headers=headers)
                    final_url = str(response.url)
                    
                    if response.status_code == 404:
                        result = (False, "404 Not Found", final_url)
                        self._cache[url] = result
                        return result
                    
                    if response.status_code >= 400:
                        # Fallback to GET if HEAD fails (some servers block HEAD)
                        try:
                            response = await client.get(url, headers=headers)
                            final_url = str(response.url)
                            if response.status_code >= 400:
                                result = (False, f"HTTP {response.status_code}", final_url)
                                self._cache[url] = result
                                return result
                        except Exception:
                            result = (False, f"HTTP {response.status_code}", final_url)
                            self._cache[url] = result
                            return result
                    
                    result = (True, None, final_url)
                    self._cache[url] = result
                    return result
                    
            except httpx.TimeoutException:
                # Assume valid if timeout, but can't get final URL
                return True, None, url
            except Exception as e:
                return True, None, url

    def _detect_application_type(self, url: str) -> str:
        from src.core.job import ApplicationType
        url_lower = url.lower()
        
        if "greenhouse.io" in url_lower:
            return ApplicationType.GREENHOUSE
        if "lever.co" in url_lower:
            return ApplicationType.LEVER
        if "workday" in url_lower:
            return ApplicationType.WORKDAY
        if "ashby" in url_lower or "ashbyhq.com" in url_lower:
            return ApplicationType.ASHBY
        if "oracle" in url_lower or "oraclecloud" in url_lower:
            return ApplicationType.ORACLE
        if "adp.com" in url_lower:
            return ApplicationType.ADP
        if "icims.com" in url_lower:
            return ApplicationType.ICIMS
        if "taleo.net" in url_lower:
            return ApplicationType.TALEO
        if "jobvite.com" in url_lower:
            return ApplicationType.JOBVITE
        if "smartrecruiters.com" in url_lower:
            return ApplicationType.SMARTRECRUITERS
        
        return ApplicationType.UNKNOWN

    async def validate_with_content(self, url: str) -> tuple[bool, Optional[str], Optional[str]]:
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 404:
                        return False, "Page not found", None
                    
                    if response.status_code >= 400:
                        return False, f"HTTP {response.status_code}", None
                    
                    content_lower = response.text.lower()
                    for pattern in self.DEAD_LINK_PATTERNS:
                        if pattern in content_lower:
                            return False, f"Dead link: {pattern}", None
                    
                    for pattern in self.PHISHING_KEYWORDS:
                        if pattern in content_lower:
                             return False, f"Phishing indicator: {pattern}", None
                    
                    final_url = str(response.url)
                    
                    return True, None, final_url
                    
            except Exception as e:
                return True, None, None



    async def validate_jobs(self, jobs: list[Job], check_content: bool = False) -> tuple[list[Job], list[dict]]:
        valid_jobs = []
        invalid_jobs = []
        
        # Identify interaction-heavy jobs (Jobright)
        playwright_jobs = [j for j in jobs if "jobright.ai" in j.url]
        standard_jobs = [j for j in jobs if j not in playwright_jobs]
        
        tasks = []
        
        if check_content:
            tasks.extend([self.validate_with_content(job.url) for job in standard_jobs])
        else:
            tasks.extend([self.is_valid(job.url) for job in standard_jobs])
            
        results_map = {}
        
        # Run standard tasks
        standard_results = await asyncio.gather(*tasks) if tasks else []
        for job, res in zip(standard_jobs, standard_results):
            results_map[job.id or job.url] = res
            
        # Run Jobright tasks with fast HTTP resolution (no browser needed)
        if playwright_jobs:
            print(f"[DEBUG] Processing {len(playwright_jobs)} Jobright jobs with HTTP resolution...")
            
            async def resolve_jobright_http(job: Job) -> tuple[str, tuple]:
                """Resolve Jobright links via HTTP - much faster than browser."""
                url = job.url
                job_key = job.id or job.url
                
                try:
                    async with httpx.AsyncClient(
                        follow_redirects=True, 
                        timeout=15.0,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    ) as client:
                        # Try to get the page and extract the apply link from HTML/redirects
                        response = await client.get(url)
                        final_url = str(response.url)
                        
                        # If we landed on a different domain, that's the apply URL
                        if "jobright.ai" not in final_url:
                            print(f"[DEBUG] HTTP resolved: {url} -> {final_url}")
                            return (job_key, (True, None, final_url))
                        
                        # Parse HTML to find the direct apply link
                        import re
                        content = response.text
                        
                        # Look for applyLink or originalUrl in the page content/JSON
                        apply_link_match = re.search(r'"applyLink"\s*:\s*"([^"]+)"', content)
                        if apply_link_match:
                            apply_url = apply_link_match.group(1).replace('\\/', '/')
                            print(f"[DEBUG] Found applyLink: {apply_url}")
                            return (job_key, (True, None, apply_url))
                        
                        original_url_match = re.search(r'"originalUrl"\s*:\s*"([^"]+)"', content)
                        if original_url_match:
                            orig_url = original_url_match.group(1).replace('\\/', '/')
                            print(f"[DEBUG] Found originalUrl: {orig_url}")
                            return (job_key, (True, None, orig_url))
                        
                        # Look for external links that look like ATS systems
                        ats_patterns = [
                            r'href="(https://[^"]*greenhouse\.io[^"]*)"',
                            r'href="(https://[^"]*lever\.co[^"]*)"',
                            r'href="(https://[^"]*workday[^"]*)"',
                            r'href="(https://[^"]*ashbyhq\.com[^"]*)"',
                            r'href="(https://[^"]*icims\.com[^"]*)"',
                            r'href="(https://[^"]*smartrecruiters\.com[^"]*)"',
                        ]
                        for pattern in ats_patterns:
                            match = re.search(pattern, content, re.IGNORECASE)
                            if match:
                                ats_url = match.group(1)
                                print(f"[DEBUG] Found ATS link: {ats_url}")
                                return (job_key, (True, None, ats_url))
                        
                        # Couldn't find direct link - use original URL but mark job valid
                        print(f"[DEBUG] No direct link found, using original: {url}")
                        return (job_key, (True, None, url))
                        
                except Exception as e:
                    print(f"[DEBUG] HTTP resolution failed for {url}: {e}")
                    return (job_key, (True, None, url))  # Return original URL on error
            
            # Process in parallel batches
            batch_tasks = [resolve_jobright_http(job) for job in playwright_jobs]
            batch_results = await asyncio.gather(*batch_tasks)
            
            for job_key, result in batch_results:
                results_map[job_key] = result
        
        # Reconstruct ordered results
        for job in jobs:
            result = results_map.get(job.id or job.url)
            
            if check_content:
                is_valid, reason, final_url = result
            else:
                if len(result) == 3:
                     is_valid, reason, final_url = result
                else:
                     is_valid, reason = result
                     final_url = job.url
            
            if final_url and final_url != job.url:
                job.apply_url = final_url
                # Detect Platform/ATS
                app_type = self._detect_application_type(final_url)
                if app_type != "unknown":
                    job.application_type = app_type
            
            if is_valid:
                valid_jobs.append(job)
            else:
                invalid_jobs.append({"job": job, "reason": reason})
        
        return valid_jobs, invalid_jobs
    
    def clear_cache(self):
        self._cache.clear()


class IncrementalScraper:
    def __init__(self):
        self._seen_urls: set[str] = set()
        self._last_scrape: dict[str, datetime] = {}
    
    def load_from_db(self, db):
        from src.utils.database import JobModel
        with db.session() as session:
            urls = session.query(JobModel.url).all()
            self._seen_urls = {url[0].lower().rstrip('/') for url in urls}
    
    def is_new(self, url: str) -> bool:
        normalized = url.lower().rstrip('/')
        return normalized not in self._seen_urls
    
    def mark_seen(self, url: str):
        normalized = url.lower().rstrip('/')
        self._seen_urls.add(normalized)
    
    def filter_new_jobs(self, jobs: list[Job]) -> list[Job]:
        new_jobs = []
        for job in jobs:
            if self.is_new(job.url):
                new_jobs.append(job)
                self.mark_seen(job.url)
        return new_jobs
    
    def record_scrape(self, source: str):
        self._last_scrape[source] = datetime.now()
    
    def get_last_scrape(self, source: str) -> Optional[datetime]:
        return self._last_scrape.get(source)
    
    @property
    def seen_count(self) -> int:
        return len(self._seen_urls)


_validator: Optional[LinkValidator] = None
_incremental: Optional[IncrementalScraper] = None


def get_link_validator() -> LinkValidator:
    global _validator
    if _validator is None:
        _validator = LinkValidator()
    return _validator


def get_incremental_scraper() -> IncrementalScraper:
    global _incremental
    if _incremental is None:
        _incremental = IncrementalScraper()
    return _incremental
