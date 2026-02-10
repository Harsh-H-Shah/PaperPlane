import httpx
import re
import os
from typing import Optional

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_string
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type


class JobrightScraper(BaseScraper):
    SOURCE_NAME = "Jobright"
    SOURCE_TYPE = JobSource.JOBRIGHT
    
    API_URL = "https://jobright.ai/swan/recommend/list/jobs"
    GITHUB_API = "https://api.github.com/repos/jobright-ai/2026-Software-Engineer-New-Grad/readme"
    
    def __init__(self):
        super().__init__()
        self.user_id = os.getenv("JOBRIGHT_USER_ID")
        self.visitor_id = os.getenv("JOBRIGHT_VISITOR_ID")
        self.device_id = os.getenv("JOBRIGHT_DEVICE_ID")
        self.use_api = bool(self.user_id)
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or self.get_search_keywords()
        
        if self.use_api:
            try:
                api_jobs = await self._fetch_from_api(limit)
                jobs.extend(api_jobs)
            except Exception as e:
                print(f"Jobright API error: {e}, falling back to GitHub")
        
        if len(jobs) < limit:
            try:
                github_jobs = await self._fetch_from_github(keywords, limit - len(jobs))
                jobs.extend(github_jobs)
            except Exception as e:
                print(f"Jobright GitHub error: {e}")
        
        self.jobs_found = len(jobs)
        return jobs[:limit]
    
    async def _fetch_from_api(self, limit: int) -> list[Job]:
        jobs = []
        position = 0
        
        async with httpx.AsyncClient() as client:
            while len(jobs) < limit:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Referer": "https://jobright.ai/jobs/recommend",
                }
                
                cookies = {
                    "JR_userid": self.user_id or "",
                    "JR_visitor_id": self.visitor_id or "",
                    "JR_device_id": self.device_id or "",
                }
                
                # IMPORTANT: Jobright now requires SESSION_ID cookie
                session_id = os.getenv("JOBRIGHT_SESSION_ID")
                if session_id:
                    cookies["SESSION_ID"] = session_id
                
                # Check if we have what we need
                if not session_id and not self.user_id:
                     print("   [WARNING] No Jobright SESSION_ID or UserID found. API may fail.")
                
                params = {
                    "refresh": "true" if position == 0 else "false",
                    "sortCondition": "0",
                    "position": str(position),
                }
                
                response = await client.get(
                    self.API_URL, 
                    params=params, 
                    headers=headers, 
                    cookies=cookies,
                    timeout=30
                )
                
                print(f"   [DEBUG] Jobright API Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"   [DEBUG] Jobright API Error: {response.text}")
                    break
                
                data = response.json()
                
                # Handle new API structure: data['result']['jobList']
                result = data.get("result", {})
                if isinstance(result, dict) and "jobList" in result:
                    items = result.get("jobList", [])
                else:
                    items = data.get("data", [])
                
                if not items:
                    break
                
                for item in items:
                    job = self._parse_api_job(item)
                    if job and self.should_include_job(job):
                        jobs.append(job)
                        if len(jobs) >= limit:
                            break
                
                position += len(items)
                
                if len(items) < 20:
                    break
        
        return jobs
    
    def _parse_api_job(self, item: dict) -> Optional[Job]:
        try:
            job_data = item.get("jobResult", {})
            company_data = item.get("companyResult", {})
            
            title = job_data.get("jobTitle", "")
            company = company_data.get("companyName", "")
            apply_url = job_data.get("applyLink", "")
            original_url = job_data.get("originalUrl", "")
            location = job_data.get("location", "")
            
            if not apply_url:
                apply_url = original_url
            
            if not apply_url or not title:
                return None
            
            jobright_url = f"https://jobright.ai/jobs/info/{job_data.get('jobId', '')}"
            
            app_type, _ = detect_application_type(apply_url)
            
            salary_min = job_data.get("salaryMin")
            salary_max = job_data.get("salaryMax")
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=apply_url,
                apply_url=apply_url,
                source=JobSource.JOBRIGHT,
                application_type=app_type,
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=parse_date_string(job_data.get("publishTimeDesc")),
                tags=["jobright", "api"],
                raw_data={
                    "jobright_id": job_data.get("jobId"),
                    "jobright_url": jobright_url,
                    "skills": job_data.get("jdCoreSkills", []),
                    "posted": job_data.get("publishTimeDesc"),
                },
            )
        except Exception:
            return None
    
    async def _fetch_from_github(self, keywords: list[str], limit: int) -> list[Job]:
        jobs = []
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Accept": "application/vnd.github.v3.raw",
                "User-Agent": "PaperPlane/1.0"
            }
            response = await client.get(self.GITHUB_API, headers=headers, timeout=30)
            
            if response.status_code != 200:
                return jobs
            
            content = response.text
            lines = content.split('\n')
            
            for line in lines:
                if not line.startswith('|') or '---' in line:
                    continue
                
                if 'Company' in line and 'Job Title' in line:
                    continue
                
                job = self._parse_github_row(line)
                if job:
                    title_lower = job.title.lower()
                    if any(kw.lower() in title_lower for kw in keywords):
                        if self.should_include_job(job):
                            jobs.append(job)
                            if len(jobs) >= limit:
                                break
        
        return jobs
    
    def _parse_github_row(self, line: str) -> Optional[Job]:
        try:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) < 2:
                return None
            
            company = self._extract_text(parts[0])
            title = self._extract_text(parts[1])
            location = self._extract_text(parts[2]) if len(parts) > 2 else "Remote"
            
            url = self._extract_url(parts[1]) or self._extract_url(parts[0])
            if not url:
                return None
            
            app_type, _ = detect_application_type(url)
            
            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                apply_url=url,
                source=JobSource.JOBRIGHT,
                application_type=app_type,
                tags=["jobright", "github"],
            )
        except Exception:
            return None
    
    def _extract_text(self, cell: str) -> str:
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cell)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        return text.strip()
    
    def _extract_url(self, cell: str) -> Optional[str]:
        match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', cell)
        if match:
            return match.group(2)
        
        url_match = re.search(r'https?://[^\s\)\"]+', cell)
        if url_match:
            return url_match.group(0)
        
        return None
