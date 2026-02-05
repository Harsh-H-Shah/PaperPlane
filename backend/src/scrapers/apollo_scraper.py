"""
Apollo.io Contact Scraper - Finds hiring managers, recruiters, and engineering managers.
Uses browser cookies for authentication (supports Google OAuth login).
"""
import os
import re
import json
import httpx
import asyncio
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup

from src.core.cold_email_models import Contact, ContactPersona, ContactSource


# Job titles that indicate hiring-relevant roles
PERSONA_KEYWORDS = {
    ContactPersona.RECRUITER: [
        "recruiter", "talent acquisition", "sourcer", "recruiting",
        "talent partner", "staffing", "talent scout"
    ],
    ContactPersona.HIRING_MANAGER: [
        "hiring manager", "head of", "director of engineering",
        "vp of engineering", "cto", "chief technology"
    ],
    ContactPersona.ENGINEERING_MANAGER: [
        "engineering manager", "eng manager", "software manager",
        "tech lead", "team lead", "principal engineer", "staff engineer"
    ],
    ContactPersona.HR: [
        "human resources", "hr manager", "hr director", "people ops",
        "people operations", "hr business partner"
    ],
    ContactPersona.TALENT_ACQUISITION: [
        "talent acquisition", "ta manager", "ta lead", "ta specialist"
    ],
}


class ApolloScraper:
    """Scrapes contacts from Apollo.io using session cookies"""
    
    BASE_URL = "https://app.apollo.io"
    API_URL = "https://app.apollo.io/api/v1"
    
    def __init__(self, cookies: str = None):
        self.cookies = cookies or os.getenv("APOLLO_COOKIES", "")
        self.enabled = bool(self.cookies)
        
        if not self.enabled:
            print("   ⚠️ Apollo: No cookies found. Set APOLLO_COOKIES in .env")
    
    def _get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": self.cookies,
            "Origin": self.BASE_URL,
            "Referer": f"{self.BASE_URL}/",
        }
    
    def _classify_persona(self, title: str) -> ContactPersona:
        """Classify contact based on job title"""
        title_lower = title.lower()
        
        for persona, keywords in PERSONA_KEYWORDS.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return persona
        
        return ContactPersona.UNKNOWN
    
    async def search_contacts(
        self, 
        company: str, 
        personas: list[ContactPersona] = None,
        limit: int = 20
    ) -> list[Contact]:
        """Search for contacts at a company"""
        if not self.enabled:
            return []
        
        contacts = []
        personas = personas or [
            ContactPersona.RECRUITER,
            ContactPersona.HIRING_MANAGER,
            ContactPersona.ENGINEERING_MANAGER
        ]
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                # First try API search
                api_contacts = await self._search_via_api(client, company, limit)
                contacts.extend(api_contacts)
                
                # Filter by persona
                if personas:
                    contacts = [c for c in contacts if c.persona in personas]
                
                if not contacts:
                    # Fallback to web scraping
                    web_contacts = await self._search_via_web(client, company, limit)
                    contacts.extend([c for c in web_contacts if c.persona in personas])
                    
        except Exception as e:
            print(f"   ❌ Apollo error: {e}")
        
        print(f"   📋 Apollo: Found {len(contacts)} contacts at {company}")
        return contacts[:limit]
    
    async def _search_via_api(
        self, 
        client: httpx.AsyncClient, 
        company: str, 
        limit: int
    ) -> list[Contact]:
        """Search using Apollo's API"""
        contacts = []
        
        try:
            # Build search query for hiring-related titles
            title_keywords = []
            for keywords in PERSONA_KEYWORDS.values():
                title_keywords.extend(keywords[:2])  # Top 2 from each
            
            search_payload = {
                "q_organization_name": company,
                "q_keywords": " OR ".join(title_keywords[:5]),
                "per_page": min(limit, 25),
                "page": 1,
            }
            
            response = await client.post(
                f"{self.API_URL}/people/search",
                json=search_payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                people = data.get("people", [])
                
                for person in people:
                    contact = self._parse_person(person, company)
                    if contact:
                        contacts.append(contact)
                        
        except Exception as e:
            print(f"      Apollo API error: {e}")
        
        return contacts
    
    async def _search_via_web(
        self, 
        client: httpx.AsyncClient, 
        company: str, 
        limit: int
    ) -> list[Contact]:
        """Fallback: Search by scraping web interface"""
        contacts = []
        
        try:
            # Search URL
            search_url = f"{self.BASE_URL}/home#/people?q_organization_name={company}"
            
            response = await client.get(search_url, headers=self._get_headers())
            
            if response.status_code == 200:
                # Try to extract data from embedded JSON
                contacts = self._extract_contacts_from_html(response.text, company)
                
        except Exception:
            pass
        
        return contacts
    
    def _parse_person(self, person: dict, company: str) -> Optional[Contact]:
        """Parse a person from Apollo API response"""
        try:
            name = person.get("name", "")
            email = person.get("email") or person.get("revealed_email", "")
            title = person.get("title", "")
            linkedin = person.get("linkedin_url", "")
            
            # Skip if no email
            if not email:
                return None
            
            # Skip if email looks fake/generic
            if "@example.com" in email or "noreply" in email.lower():
                return None
            
            persona = self._classify_persona(title)
            
            return Contact(
                id=f"apollo_{person.get('id', hash(email))}",
                name=name,
                email=email,
                title=title,
                company=person.get("organization_name", company),
                linkedin_url=linkedin if linkedin else None,
                persona=persona,
                source=ContactSource.APOLLO,
                created_at=datetime.now(),
            )
        except Exception:
            return None
    
    def _extract_contacts_from_html(self, html: str, company: str) -> list[Contact]:
        """Extract contacts from Apollo web page HTML"""
        contacts = []
        
        try:
            # Look for embedded data
            match = re.search(r'window\.__APOLLO_STATE__\s*=\s*(\{.+?\});', html, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                
                for key, value in data.items():
                    if key.startswith("Person:") and isinstance(value, dict):
                        contact = self._parse_embedded_person(value, company)
                        if contact:
                            contacts.append(contact)
                            
        except Exception:
            pass
        
        return contacts
    
    def _parse_embedded_person(self, person: dict, company: str) -> Optional[Contact]:
        """Parse person from embedded Apollo state"""
        try:
            name = person.get("name", "")
            email = person.get("email", "")
            title = person.get("title", "")
            
            if not email or not name:
                return None
            
            persona = self._classify_persona(title)
            
            return Contact(
                id=f"apollo_{person.get('id', hash(email))}",
                name=name,
                email=email,
                title=title,
                company=company,
                persona=persona,
                source=ContactSource.APOLLO,
                created_at=datetime.now(),
            )
        except Exception:
            return None
    
    async def enrich_contact(self, contact: Contact) -> Contact:
        """Enrich contact with additional data"""
        if not self.enabled or not contact.email:
            return contact
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self.API_URL}/people/match",
                    json={"email": contact.email},
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    person = data.get("person", {})
                    
                    if person:
                        contact.linkedin_url = person.get("linkedin_url") or contact.linkedin_url
                        contact.title = person.get("title") or contact.title
                        contact.persona = self._classify_persona(contact.title)
                        
        except Exception:
            pass
        
        return contact


async def scrape_contacts_for_job(job, limit: int = 10) -> list[Contact]:
    """Helper function to scrape contacts for a job application"""
    scraper = ApolloScraper()
    
    if not scraper.enabled:
        return []
    
    contacts = await scraper.search_contacts(
        company=job.company,
        personas=[
            ContactPersona.RECRUITER,
            ContactPersona.HIRING_MANAGER,
            ContactPersona.ENGINEERING_MANAGER
        ],
        limit=limit
    )
    
    # Link contacts to job
    for contact in contacts:
        contact.job_id = job.id
    
    return contacts
