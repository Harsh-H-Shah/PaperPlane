import httpx
import re
from typing import Optional
from datetime import datetime

from src.scrapers.base_scraper import BaseScraper
from src.core.job import Job, JobSource, ApplicationType
from src.classifiers.detector import detect_application_type


class YCJobsScraper(BaseScraper):
    SOURCE_NAME = "YCombinator"
    SOURCE_TYPE = JobSource.YC_JOBS
    
    API_URL = "https://www.workatastartup.com/api/companies/search"
    
    ROLE_KEYWORDS = ["software", "engineer", "developer", "frontend", "backend", "fullstack", "data", "ml", "ai"]
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or self.get_search_keywords()
        
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "query": "software engineer",
                    "page": 1,
                    "batch": "",
                    "remote": "true",
                    "visa": "true",
                }
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                }
                
                response = await client.get(self.API_URL, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    companies = data.get("companies", [])
                    
                    for company in companies[:limit * 2]:
                        company_jobs = self._parse_company(company, keywords)
                        jobs.extend(company_jobs)
                        
                        if len(jobs) >= limit:
                            break
                else:
                    jobs = await self._scrape_fallback(keywords, limit)
                    
        except Exception as e:
            print(f"Error fetching YC Jobs: {e}")
            jobs = await self._scrape_fallback(keywords, limit)
        
        self.jobs_found = len(jobs)
        return jobs[:limit]
    
    def _parse_company(self, company_data: dict, keywords: list[str]) -> list[Job]:
        jobs = []
        
        company_name = company_data.get("name", "Unknown")
        job_listings = company_data.get("jobs", [])
        
        for job_data in job_listings:
            title = job_data.get("title", "")
            
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in self.ROLE_KEYWORDS):
                continue
            
            url = f"https://www.workatastartup.com/jobs/{job_data.get('id', '')}"
            app_type, _ = detect_application_type(url)
            
            job = Job(
                title=title,
                company=company_name,
                location=job_data.get("locations_str", "Remote"),
                url=url,
                apply_url=job_data.get("url", url),
                application_type=app_type,
                job_type="Full-time",
                salary_min=job_data.get("salary_min"),
                salary_max=job_data.get("salary_max"),
                tags=["yc_startup", company_data.get("batch", "")],
                raw_data=job_data,
            )
            
            if self.should_include_job(job):
                jobs.append(job)
        
        return jobs
    
    async def _scrape_fallback(self, keywords: list[str], limit: int) -> list[Job]:
        jobs = []
        
        try:
            async with httpx.AsyncClient() as client:
                url = "https://www.workatastartup.com/companies"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                
                response = await client.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    job_links = re.findall(r'/jobs/(\d+)', response.text)
                    
                    for job_id in job_links[:limit]:
                        job = Job(
                            title="Software Engineer",
                            company="YC Startup",
                            location="Remote",
                            url=f"https://www.workatastartup.com/jobs/{job_id}",
                            apply_url=f"https://www.workatastartup.com/jobs/{job_id}",
                            tags=["yc_startup"],
                        )
                        jobs.append(job)
        except Exception:
            pass
        
        return jobs
