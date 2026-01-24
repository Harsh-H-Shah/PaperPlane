import httpx
import warnings
from typing import Optional
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress XML parsing warning for RSS feeds
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_string
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type





class BuiltInScraper(BaseScraper):
    SOURCE_NAME = "BuiltIn"
    SOURCE_TYPE = JobSource.BUILTIN
    
    # Targeting Entry Level Software Engineering in USA
    BASE_URL = "https://builtin.com/jobs/engineering/software-engineering/entry-level"
    INTERN_URL = "https://builtin.com/jobs/internships"
    
    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs = []
        keywords = keywords or ["Software Engineer"]
        
        # Scrape both Entry Level and Internships
        urls = [
            f"{self.BASE_URL}?search=Software+Engineer&country=USA&allLocations=true",
            f"{self.INTERN_URL}?search=Software+Engineer&country=USA&allLocations=true"
        ]
        
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            for url in urls:
                try:
                    if len(jobs) >= limit:
                        break
                        
                    response = await client.get(url, headers=headers, timeout=30, follow_redirects=True)
                    
                    if response.status_code == 200:
                        new_jobs = self._parse_html(response.text, keywords, limit - len(jobs))
                        jobs.extend(new_jobs)
                except Exception as e:
                    print(f"Error fetching BuiltIn URL {url}: {e}")
        
        self.jobs_found = len(jobs)
        # Deduplicate by URL
        unique_jobs = {job.url: job for job in jobs}
        return list(unique_jobs.values())[:limit]
    
    def _parse_html(self, html: str, keywords: list[str], limit: int) -> list[Job]:
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        # BuiltIn Job Cards
        job_cards = soup.select('div[data-id="job-card"], div.job-item, div.card-body')
        
        for card in job_cards:
            try:
                # Selectors based on recent analysis
                title_el = card.select_one('a[id^="job-card-alias-"], h2 a, a.card-alias-after-overlay')
                company_el = card.select_one('div[data-id="company-title"], a[href^="/company/"] span, .company-title')
                date_el = card.select_one('div.bounded-attribute-section span, span.job-date')
                
                if not title_el:
                    continue
                
                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True) if company_el else "Unknown Company"
                
                # Link is usually on the title element
                url = title_el.get('href', '')
                if not url.startswith('http'):
                    url = f"https://builtin.com{url}"
                
                # Date parsing
                posted_date = None
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    # "Reposted 19 Hours Ago" -> "19 Hours Ago"
                    date_text = date_text.replace("Reposted", "").replace("Posted", "").strip()
                    posted_date = parse_date_string(date_text)
                
                job = Job(
                    title=title,
                    company=company,
                    location="United States", # Default as we filtered by USA
                    url=url,
                    apply_url=url,
                    source=JobSource.BUILTIN,
                    posted_date=posted_date,
                    tags=["builtin", "entry-level" if "entry-level" in self.BASE_URL else "intern"],
                )
                
                if self.should_include_job(job):
                    jobs.append(job)
                    if len(jobs) >= limit:
                        break
            except Exception as e:
                # print(f"Error parsing BuiltIn card: {e}")
                continue
        
        return jobs



