"""Pydantic request bodies for the dashboard API, grouped in one place."""
from typing import Optional

from pydantic import BaseModel


# ---- Jobs ----

class JobUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class JobCreate(BaseModel):
    title: str
    company: str
    url: str
    location: Optional[str] = ""
    source: Optional[str] = "manual"
    application_type: Optional[str] = "unknown"


# ---- Scraping ----

class ScrapeRequest(BaseModel):
    sources: Optional[list[str]] = None
    limit: int = 100


# ---- Profile ----

class ProfileUpdate(BaseModel):
    valorant_agent: Optional[str] = None


# ---- Cold email ----

class ContactCreate(BaseModel):
    name: str
    email: str
    title: Optional[str] = ""
    company: str
    linkedin_url: Optional[str] = None
    persona: Optional[str] = "unknown"
    job_id: Optional[str] = None
    notes: Optional[str] = None


class EmailCreate(BaseModel):
    contact_id: str
    job_id: Optional[str] = None
    template_id: Optional[str] = None
    subject: str
    body: str


class CampaignCreate(BaseModel):
    job_id: str
    max_contacts: int = 5
    personas: Optional[list[str]] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    persona: Optional[str] = None
    job_id: Optional[str] = None
    notes: Optional[str] = None


class EmailUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[str] = None


class RenderEmail(BaseModel):
    contact_id: str
    job_id: Optional[str] = None
    template_id: Optional[str] = None
