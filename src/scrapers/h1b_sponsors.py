import httpx
import re
from typing import Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass

from src.utils.config import get_settings


@dataclass
class H1BSponsor:
    name: str
    h1b_filings: int
    avg_salary: Optional[int] = None
    approval_rate: Optional[float] = None
    careers_url: Optional[str] = None
    
    def __str__(self):
        return f"{self.name} ({self.h1b_filings} filings)"


COMPANY_CAREERS_URLS = {
    "GOOGLE LLC": "https://careers.google.com/jobs/results/",
    "MICROSOFT CORPORATION": "https://careers.microsoft.com/us/en/search-results",
    "AMAZON.COM SERVICES LLC": "https://www.amazon.jobs/en/search",
    "AMAZONCOM SERVICES LLC": "https://www.amazon.jobs/en/search",
    "AMAZON WEB SERVICES INC": "https://www.amazon.jobs/en/search",
    "META PLATFORMS INC": "https://www.metacareers.com/jobs/",
    "APPLE INC": "https://jobs.apple.com/en-us/search",
    "INTEL CORPORATION": "https://jobs.intel.com/en/search-jobs",
    "NVIDIA CORPORATION": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    "SALESFORCE INC": "https://careers.salesforce.com/en/jobs/",
    "ORACLE AMERICA INC": "https://careers.oracle.com/jobs/",
    "ADOBE INC": "https://careers.adobe.com/us/en/search-results",
    "UBER TECHNOLOGIES INC": "https://www.uber.com/us/en/careers/list/",
    "AIRBNB INC": "https://careers.airbnb.com/positions/",
    "STRIPE INC": "https://stripe.com/jobs/search",
    "COINBASE INC": "https://www.coinbase.com/careers/positions",
    "LINKEDIN CORPORATION": "https://careers.linkedin.com/",
    "TWITTER INC": "https://careers.twitter.com/en/roles.html",
    "SNAP INC": "https://careers.snap.com/jobs",
    "PAYPAL INC": "https://careers.pypl.com/home/jobs",
    "BLOOMBERG LP": "https://careers.bloomberg.com/job/search",
    "NETFLIX INC": "https://jobs.netflix.com/search",
    "SPOTIFY USA INC": "https://www.lifeatspotify.com/jobs",
    "DROPBOX INC": "https://www.dropbox.com/jobs/teams",
    "ZOOM VIDEO COMMUNICATIONS INC": "https://careers.zoom.us/jobs/search",
    "DATABRICKS INC": "https://www.databricks.com/company/careers",
    "SNOWFLAKE INC": "https://careers.snowflake.com/us/en/search-results",
    "CLOUDFLARE INC": "https://www.cloudflare.com/careers/jobs/",
    "TWILIO INC": "https://www.twilio.com/company/jobs",
    "PALANTIR TECHNOLOGIES INC": "https://www.palantir.com/careers/",
    "DOORDASH INC": "https://careers.doordash.com/",
    "INSTACART": "https://instacart.careers/",
    "LYFT INC": "https://www.lyft.com/careers",
    "ROBINHOOD MARKETS INC": "https://careers.robinhood.com/",
    "PLAID INC": "https://plaid.com/careers/",
    "FIGMA INC": "https://www.figma.com/careers/",
    "NOTION LABS INC": "https://www.notion.so/careers",
    "AIRTABLE INC": "https://airtable.com/careers",
    "MONGODB INC": "https://www.mongodb.com/company/careers",
    "HASHICORP INC": "https://www.hashicorp.com/careers",
    "GITLAB INC": "https://about.gitlab.com/jobs/",
    "GITHUB INC": "https://github.com/about/careers",
    "ELASTIC NV": "https://www.elastic.co/careers/",
    "COCKROACH LABS INC": "https://www.cockroachlabs.com/careers/",
    "CONFLUENT INC": "https://www.confluent.io/careers/",
    "OKTA INC": "https://www.okta.com/company/careers/",
    "CROWDSTRIKE INC": "https://www.crowdstrike.com/careers/",
    "PALO ALTO NETWORKS INC": "https://jobs.paloaltonetworks.com/",
    "ZSCALER INC": "https://www.zscaler.com/careers",
    "WEALTHFRONT INC": "https://www.wealthfront.com/careers",
    "CHIME FINANCIAL INC": "https://www.chime.com/careers/",
    "AFFIRM INC": "https://www.affirm.com/careers",
    "SQUARE INC": "https://careers.squareup.com/us/en/jobs",
    "BLOCK INC": "https://block.xyz/careers",
    "VISA INC": "https://usa.visa.com/careers.html",
    "MASTERCARD INCORPORATED": "https://careers.mastercard.com/",
    "AMERICAN EXPRESS": "https://www.americanexpress.com/en-us/careers/",
    "CAPITAL ONE": "https://www.capitalonecareers.com/",
    "JPMORGAN CHASE": "https://careers.jpmorgan.com/",
    "GOLDMAN SACHS": "https://www.goldmansachs.com/careers/",
    "MORGAN STANLEY": "https://www.morganstanley.com/careers/",
    "CITADEL LLC": "https://www.citadel.com/careers/",
    "TWO SIGMA": "https://www.twosigma.com/careers/",
    "JANE STREET": "https://www.janestreet.com/join-jane-street/open-roles/",
    "DE SHAW": "https://www.deshaw.com/careers",
}


class H1BSponsorScraper:
    H1BDATA_URL = "https://h1bdata.info/topcompanies.php"
    
    def __init__(self):
        self.settings = get_settings()
        self.sponsors: list[H1BSponsor] = []
    
    async def fetch_sponsors(self, limit: int = 200) -> list[H1BSponsor]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                }
                response = await client.get(self.H1BDATA_URL, headers=headers, follow_redirects=True)
                
                if response.status_code != 200:
                    print(f"Failed to fetch H1B data: {response.status_code}")
                    return self._get_fallback_sponsors()
                
                return self._parse_h1bdata(response.text, limit)
        except Exception as e:
            print(f"Error fetching H1B sponsors: {e}")
            return self._get_fallback_sponsors()
    
    def _parse_h1bdata(self, html: str, limit: int) -> list[H1BSponsor]:
        sponsors = []
        soup = BeautifulSoup(html, 'lxml')
        
        table = soup.find('table')
        if not table:
            return self._get_fallback_sponsors()
        
        rows = table.find_all('tr')[1:]
        
        for row in rows[:limit]:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            
            try:
                name = cols[1].get_text(strip=True).upper()
                filings_text = cols[2].get_text(strip=True).replace(',', '')
                filings = int(filings_text) if filings_text.isdigit() else 0
                
                avg_salary = None
                if len(cols) > 3:
                    salary_text = cols[3].get_text(strip=True).replace('$', '').replace(',', '')
                    if salary_text.isdigit():
                        avg_salary = int(salary_text)
                
                careers_url = self._get_careers_url(name)
                
                sponsors.append(H1BSponsor(
                    name=name,
                    h1b_filings=filings,
                    avg_salary=avg_salary,
                    careers_url=careers_url
                ))
            except Exception:
                continue
        
        self.sponsors = sponsors
        return sponsors
    
    def _get_careers_url(self, company_name: str) -> Optional[str]:
        name_upper = company_name.upper()
        
        if name_upper in COMPANY_CAREERS_URLS:
            return COMPANY_CAREERS_URLS[name_upper]
        
        for known_name, url in COMPANY_CAREERS_URLS.items():
            if known_name in name_upper or name_upper in known_name:
                return url
        
        return None
    
    def _get_fallback_sponsors(self) -> list[H1BSponsor]:
        fallback = [
            ("GOOGLE LLC", 8000), ("MICROSOFT CORPORATION", 7500),
            ("AMAZON.COM SERVICES LLC", 9000), ("META PLATFORMS INC", 3500),
            ("APPLE INC", 3000), ("NVIDIA CORPORATION", 2000),
            ("SALESFORCE INC", 1500), ("ORACLE AMERICA INC", 2500),
            ("ADOBE INC", 1200), ("UBER TECHNOLOGIES INC", 1000),
            ("AIRBNB INC", 800), ("STRIPE INC", 900),
            ("LINKEDIN CORPORATION", 1500), ("NETFLIX INC", 700),
            ("SNAP INC", 500), ("PAYPAL INC", 800),
            ("BLOOMBERG LP", 1200), ("SPOTIFY USA INC", 400),
            ("DROPBOX INC", 500), ("ZOOM VIDEO COMMUNICATIONS INC", 600),
            ("DATABRICKS INC", 800), ("SNOWFLAKE INC", 700),
            ("CLOUDFLARE INC", 500), ("TWILIO INC", 400),
            ("PALANTIR TECHNOLOGIES INC", 600), ("COINBASE INC", 500),
        ]
        
        sponsors = []
        for name, filings in fallback:
            sponsors.append(H1BSponsor(
                name=name,
                h1b_filings=filings,
                careers_url=COMPANY_CAREERS_URLS.get(name)
            ))
        
        return sponsors
    
    def get_tech_companies(self, min_filings: int = 100) -> list[H1BSponsor]:
        tech_keywords = ['TECH', 'SOFTWARE', 'CLOUD', 'DATA', 'DIGITAL', 'SOLUTIONS', 
                         'SYSTEMS', 'COMPUTING', 'INTERNET', 'LABS', 'PLATFORM']
        tech_names = list(COMPANY_CAREERS_URLS.keys())
        
        result = []
        for sponsor in self.sponsors:
            if sponsor.h1b_filings < min_filings:
                continue
            
            is_tech = any(kw in sponsor.name for kw in tech_keywords)
            is_known = any(tn in sponsor.name or sponsor.name in tn for tn in tech_names)
            
            if is_tech or is_known:
                result.append(sponsor)
        
        return result
    
    def get_with_careers_url(self) -> list[H1BSponsor]:
        return [s for s in self.sponsors if s.careers_url]


_scraper: Optional[H1BSponsorScraper] = None


def get_h1b_scraper() -> H1BSponsorScraper:
    global _scraper
    if _scraper is None:
        _scraper = H1BSponsorScraper()
    return _scraper
