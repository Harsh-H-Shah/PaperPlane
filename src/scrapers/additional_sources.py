import httpx
import warnings
from typing import Optional
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress XML parsing warning for RSS feeds
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from src.scrapers.base_scraper import BaseScraper
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type





class BuiltInScraper(BaseScraper):
    SOURCE_NAME = "BuiltIn"
    SOURCE_TYPE = JobSource.BUILTIN
    
    BASE_URL = "https://builtin.com/jobs/dev-engineering"
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or self.get_search_keywords()
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                
                url = f"{self.BASE_URL}?search=software+engineer"
                response = await client.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    jobs = self._parse_html(response.text, keywords, limit)
        except Exception as e:
            print(f"Error fetching BuiltIn: {e}")
        
        self.jobs_found = len(jobs)
        return jobs[:limit]
    
    def _parse_html(self, html: str, keywords: list[str], limit: int) -> list[Job]:
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        job_cards = soup.select('[data-id="job-card"], .job-card, article.job-listing')
        
        for card in job_cards[:limit * 2]:
            try:
                title_el = card.select_one('h2, .job-title, [data-id="job-title"]')
                company_el = card.select_one('.company-name, [data-id="company-name"]')
                link = card.select_one('a[href*="/job/"]')
                location_el = card.select_one('.job-location, [data-id="job-location"]')
                
                if not title_el or not link:
                    continue
                
                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Company"
                location = location_el.get_text(strip=True) if location_el else "United States"
                url = link.get('href', '')
                
                if not url.startswith('http'):
                    url = f"https://builtin.com{url}"
                
                job = Job(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    apply_url=url,
                    source=JobSource.BUILTIN,
                    tags=["builtin"],
                )
                
                if self.should_include_job(job):
                    jobs.append(job)
                    if len(jobs) >= limit:
                        break
            except Exception:
                continue
        
        return jobs


class DiceScraper(BaseScraper):
    SOURCE_NAME = "Dice"
    SOURCE_TYPE = JobSource.DICE
    
    API_URL = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "x-api-key": "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8",
                }
                
                params = {
                    "q": "software engineer entry level",
                    "countryCode2": "US",
                    "radius": "30",
                    "radiusUnit": "mi",
                    "page": "1",
                    "pageSize": str(limit),
                    "facets": "employmentType|postedDate|workFromHomeAvailability",
                    "fields": "id|jobId|guid|summary|title|postedDate|modifiedDate|companyName|salary|jobLocation|employmentType"
                }
                
                response = await client.get(self.API_URL, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    jobs = self._parse_response(data.get("data", []), limit)
        except Exception as e:
            print(f"Error fetching Dice: {e}")
        
        self.jobs_found = len(jobs)
        return jobs[:limit]
    
    def _parse_response(self, data: list, limit: int) -> list[Job]:
        jobs = []
        
        for item in data[:limit]:
            try:
                title = item.get("title", "")
                company = item.get("companyName", "Company")
                location_obj = item.get("jobLocation", {})
                location = location_obj.get("displayName", "United States")
                job_id = item.get("id", "")
                
                url = f"https://www.dice.com/job-detail/{job_id}"
                
                job = Job(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    apply_url=url,
                    source=JobSource.DICE,
                    tags=["dice"],
                )
                
                if self.should_include_job(job):
                    jobs.append(job)
            except Exception:
                continue
        
        return jobs
