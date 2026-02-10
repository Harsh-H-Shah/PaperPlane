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
    """Scrapes contacts from Apollo.io using API key or session cookies"""
    
    BASE_URL = "https://app.apollo.io"
    API_URL = "https://api.apollo.io/api/v1"  # Official API endpoint
    
    def __init__(self, api_key: str = None, cookies: str = None):
        self.api_key = api_key or os.getenv("APOLLO_API_KEY", "")
        self.cookies = cookies or os.getenv("APOLLO_COOKIES", "")
        self.enabled = bool(self.api_key) or bool(self.cookies)
        self.use_api_key = bool(self.api_key)
        
        if not self.enabled:
            print("   ⚠️ Apollo: No API key or cookies found. Set APOLLO_API_KEY or APOLLO_COOKIES in .env")
            print("      Get API key: https://app.apollo.io/#/settings/integrations/api")
            print("      OR use cookies: Copy _leadgenie_session, X-CSRF-TOKEN, _cf_bm from browser DevTools")
    
    def _get_headers(self) -> dict:
        if self.use_api_key:
            return {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            }
        else:
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
            print(f"   ⚠️ Apollo: Not enabled (no API key or cookies)")
            return []
        
        if self.use_api_key:
            print(f"   🔑 Using Apollo API key authentication")
        else:
            print(f"   🍪 Using Apollo cookie authentication")
        
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
                
                if not contacts and not self.use_api_key:
                    # Fallback to web scraping (only if using cookies)
                    print(f"   🌐 Falling back to web scraping...")
                    web_contacts = await self._search_via_web(client, company, limit)
                    contacts.extend([c for c in web_contacts if c.persona in personas])
                    
        except Exception as e:
            import traceback
            print(f"   ❌ Apollo error: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
        
        print(f"   📋 Apollo: Found {len(contacts)} contacts at {company}")
        return contacts[:limit]
    
    async def _search_via_api(
        self, 
        client: httpx.AsyncClient, 
        company: str, 
        limit: int
    ) -> list[Contact]:
        """Search using Apollo's official API"""
        contacts = []
        
        try:
            if self.use_api_key:
                # Use official Apollo API with API key
                # Apollo API uses query parameters, not JSON body
                from urllib.parse import urlencode, quote
                
                # Build title keywords for search
                title_keywords = []
                for keywords in PERSONA_KEYWORDS.values():
                    title_keywords.extend(keywords[:3])  # Get more keywords
                
                # Build query parameters - Apollo expects person_titles[]=value1&person_titles[]=value2 format
                query_parts = []
                query_parts.append(f"per_page={min(limit, 100)}")
                query_parts.append(f"page=1")
                query_parts.append(f"q_organization_name={quote(company)}")
                
                # Add person_titles as array parameters
                for title in title_keywords[:10]:
                    query_parts.append(f"person_titles[]={quote(title)}")
                
                # Build URL with query params
                query_string = "&".join(query_parts)
                url = f"{self.API_URL}/mixed_people/api_search?{query_string}"
                
                print(f"      Apollo API: Searching for contacts at {company}")
                print(f"      Apollo API: URL = {url.split('?')[0]}?[query params]")
                
                response = await client.post(
                    url,
                    headers=self._get_headers()
                )
                
                print(f"      Apollo API: Response status = {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    people = data.get("people", [])
                    
                    print(f"      Apollo API: Found {len(people)} people (before enrichment)")
                    if len(people) > 0:
                        print(f"      Apollo API: Sample person keys = {list(people[0].keys()) if people else 'N/A'}")
                    
                    # The search endpoint doesn't return emails, so we need to enrich
                    # Limit enrichment to avoid too many API calls and rate limits
                    enrich_limit = min(limit, 10)  # Enrich max 10 to avoid rate limits
                    enriched_count = 0
                    for person in people[:enrich_limit]:
                        # Apollo might use different field names - try both
                        person_id = person.get("id") or person.get("person_id") or person.get("apollo_id")
                        if not person_id:
                            print(f"      Warning: Person missing ID field: {list(person.keys())}")
                            continue
                        
                        # Try to enrich to get email
                        enriched = await self._enrich_person_via_api(client, person_id=person_id)
                        if enriched and enriched.get("email"):
                            contact = self._parse_person(enriched, company)
                            if contact:
                                contacts.append(contact)
                                enriched_count += 1
                        elif person.get("email"):  # If email already in search result (unlikely)
                            contact = self._parse_person(person, company)
                            if contact:
                                contacts.append(contact)
                    
                    print(f"      Apollo API: Successfully enriched {enriched_count}/{min(len(people), enrich_limit)} people")
                elif response.status_code == 401:
                    print(f"      Apollo API error: Unauthorized (401) - Check your API key")
                    print(f"      Response: {response.text[:300]}")
                elif response.status_code == 403:
                    print(f"      Apollo API error: Forbidden (403) - API key may not have required permissions")
                    print(f"      Response: {response.text[:300]}")
                else:
                    error_text = response.text[:500] if response.text else "No error message"
                    print(f"      Apollo API error: Status {response.status_code}")
                    print(f"      Response: {error_text}")
                    # Try to parse as JSON for better error message
                    try:
                        error_json = response.json()
                        if "error" in error_json:
                            print(f"      Error message: {error_json.get('error')}")
                    except:
                        pass
            else:
                # Fallback: Use cookie-based web scraping method
                print(f"      Using cookie-based web scraping (free method)")
                
                # Try HTML scraping first (more reliable with cookies)
                web_contacts = await self._search_via_web(client, company, limit)
                if web_contacts:
                    contacts.extend(web_contacts)
                    print(f"      Cookie method: Found {len(web_contacts)} contacts via HTML scraping")
                else:
                    # If HTML scraping failed, try API endpoints as fallback
                    print(f"      HTML scraping found nothing, trying API endpoints...")
                    title_keywords = []
                    for keywords in PERSONA_KEYWORDS.values():
                        title_keywords.extend(keywords[:2])
                    
                    search_payload = {
                        "q_organization_name": company,
                        "q_keywords": " OR ".join(title_keywords[:5]),
                        "per_page": min(limit, 25),
                        "page": 1,
                    }
                    
                    # Try multiple possible endpoints
                    endpoints = [
                        f"{self.BASE_URL}/api/v1/mixed_people/search",
                        f"{self.BASE_URL}/api/v1/people/search",
                    ]
                    
                    for endpoint in endpoints:
                        try:
                            response = await client.post(
                                endpoint,
                                json=search_payload,
                                headers=self._get_headers(),
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                people = data.get("people", []) or data.get("results", [])
                                
                                if people:
                                    print(f"      Cookie API: Found {len(people)} people via {endpoint}")
                                    for person in people:
                                        contact = self._parse_person(person, company)
                                        if contact:
                                            contacts.append(contact)
                                    break
                            elif response.status_code in [401, 403]:
                                print(f"      Endpoint {endpoint}: Auth failed ({response.status_code})")
                        except Exception as e:
                            print(f"      Endpoint {endpoint} error: {e}")
                            continue
                    
                    if not contacts:
                        print(f"      ⚠️ All methods failed. Possible reasons:")
                        print(f"         1. Cookies expired - refresh from browser")
                        print(f"         2. Apollo changed their endpoints")
                        print(f"         3. Account restrictions (free tier limitations)")
                        print(f"      💡 Tip: Try manual contact entry or use LinkedIn/company websites")
                        
        except Exception as e:
            import traceback
            print(f"      Apollo API error: {e}")
            print(f"      Traceback: {traceback.format_exc()}")
        
        return contacts
    
    async def _enrich_person_via_api(
        self,
        client: httpx.AsyncClient,
        person_id: str = None,
        email: str = None
    ) -> Optional[dict]:
        """Enrich a person via Apollo API to get email address"""
        if not self.use_api_key:
            return None
        
        try:
            # Use people/match endpoint - check if it uses query params or body
            # According to Apollo docs, people/match uses JSON body with api_key
            payload = {}
            if email:
                payload["email"] = email
            elif person_id:
                payload["person_id"] = person_id
            else:
                return None
            
            response = await client.post(
                f"{self.API_URL}/people/match",
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                person = data.get("person", {})
                if person:
                    return person
            else:
                error_text = response.text[:200] if response.text else "No error message"
                print(f"      Enrichment error: Status {response.status_code}, Response: {error_text}")
        except Exception as e:
            print(f"      Enrichment exception: {e}")
        
        return None
    
    async def _search_via_web(
        self, 
        client: httpx.AsyncClient, 
        company: str, 
        limit: int
    ) -> list[Contact]:
        """Scrape contacts from Apollo web interface HTML"""
        contacts = []
        
        try:
            # Step 1: Load the main Apollo page to establish session
            print(f"      Loading Apollo homepage to establish session...")
            response = await client.get(
                f"{self.BASE_URL}/",
                headers=self._get_headers(),
                follow_redirects=True,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"      Failed to load Apollo homepage: {response.status_code}")
                return contacts
            
            # Step 2: Try to access the people search page
            # Apollo uses React Router with hash-based routing
            search_urls = [
                f"{self.BASE_URL}/#/people?q_organization_name={company}",
                f"{self.BASE_URL}/#/people",
                f"{self.BASE_URL}/home#/people?q_organization_name={company}",
            ]
            
            for search_url in search_urls:
                try:
                    print(f"      Trying: {search_url}")
                    response = await client.get(
                        search_url,
                        headers=self._get_headers(),
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        # Extract contacts from embedded JSON in HTML
                        html_contacts = self._extract_contacts_from_html(response.text, company)
                        if html_contacts:
                            contacts.extend(html_contacts)
                            print(f"      Found {len(html_contacts)} contacts in HTML")
                            break
                except Exception as e:
                    print(f"      URL {search_url} error: {e}")
                    continue
            
            # Step 3: If HTML extraction failed, try to find API calls in the page
            if not contacts:
                print(f"      HTML extraction found nothing, checking for API endpoints in page...")
                # Look for API endpoints in JavaScript/network calls
                # This is a fallback - Apollo might load data via AJAX after page load
                # We'd need a browser automation tool (like Playwright) for this
                print(f"      Note: Apollo may load contacts via JavaScript after page load")
                print(f"      Consider using browser automation (Playwright/Selenium) for better results")
                
        except Exception as e:
            import traceback
            print(f"      Web scraping error: {e}")
            if "timeout" in str(e).lower():
                print(f"      Timeout - Apollo may be slow or blocking requests")
        
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
            # Method 1: Look for Apollo state in window.__APOLLO_STATE__
            apollo_state_patterns = [
                r'window\.__APOLLO_STATE__\s*=\s*(\{.+?\});',
                r'__APOLLO_STATE__\s*=\s*(\{.+?\});',
                r'apolloState\s*[:=]\s*(\{.+?\});',
            ]
            
            for pattern in apollo_state_patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        for key, value in data.items():
                            if key.startswith("Person:") and isinstance(value, dict):
                                contact = self._parse_embedded_person(value, company)
                                if contact:
                                    contacts.append(contact)
                        if contacts:
                            print(f"      Extracted {len(contacts)} contacts from Apollo state")
                            break
                    except json.JSONDecodeError:
                        continue
            
            # Method 2: Look for embedded JSON data in script tags
            if not contacts:
                script_pattern = r'<script[^>]*>(.*?)</script>'
                scripts = re.findall(script_pattern, html, re.DOTALL | re.IGNORECASE)
                for script in scripts:
                    # Look for people data
                    if 'people' in script.lower() or 'person' in script.lower():
                        # Try to find JSON objects
                        json_matches = re.findall(r'\{[^{}]*"name"[^{}]*"email"[^{}]*\}', script)
                        for json_str in json_matches:
                            try:
                                person_data = json.loads(json_str)
                                contact = self._parse_embedded_person(person_data, company)
                                if contact:
                                    contacts.append(contact)
                            except:
                                continue
            
            # Method 3: Parse HTML table/list structure (last resort)
            if not contacts:
                soup = BeautifulSoup(html, 'html.parser')
                # Look for common contact card patterns
                # This is very fragile and may break if Apollo changes their HTML
                contact_cards = soup.find_all(['div', 'tr'], class_=re.compile(r'person|contact|people', re.I))
                for card in contact_cards[:limit]:
                    name_elem = card.find(text=re.compile(r'[A-Z][a-z]+ [A-Z][a-z]+'))
                    email_elem = card.find(text=re.compile(r'[\w\.-]+@[\w\.-]+\.\w+'))
                    if name_elem and email_elem:
                        # This is very basic - would need more parsing
                        pass
                            
        except Exception as e:
            print(f"      HTML extraction error: {e}")
        
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
