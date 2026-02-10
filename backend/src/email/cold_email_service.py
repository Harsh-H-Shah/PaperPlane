"""
Cold Email Service - Main orchestrator for cold email outreach.
Ties together scraping, templates, personalization, scheduling, and sending.
"""
from datetime import datetime
from typing import Optional

from src.core.cold_email_models import (
    Contact, ColdEmail, EmailStatus, ContactPersona
)
from src.core.job import Job
from src.utils.database import get_db
from src.scrapers.apollo_scraper import ApolloScraper
from src.email.email_templates import TemplateManager, get_template_variables
from src.email.email_personalizer import EmailPersonalizer
from src.email.email_scheduler import EmailScheduler
from src.email.email_sender import EmailSender


class ColdEmailService:
    """Main service for managing cold email outreach"""
    
    def __init__(self):
        self.db = get_db()
        self.scraper = ApolloScraper()
        self.templates = TemplateManager()
        self.personalizer = EmailPersonalizer()
        self.scheduler = EmailScheduler()
        self.sender = EmailSender()
    
    async def create_campaign_for_job(
        self,
        job: Job,
        max_contacts: int = 5,
        personas: list[ContactPersona] = None
    ) -> dict:
        """
        Create a cold email campaign for a job application.
        Scrapes contacts and creates personalized emails.
        """
        personas = personas or [
            ContactPersona.RECRUITER,
            ContactPersona.HIRING_MANAGER,
            ContactPersona.ENGINEERING_MANAGER
        ]
        
        result = {
            "job_id": job.id,
            "company": job.company,
            "contacts_found": 0,
            "emails_created": 0,
            "emails_scheduled": 0,
        }
        
        # 1. Scrape contacts
        print(f"   🔍 Searching for contacts at {job.company}...")
        contacts = await self.scraper.search_contacts(
            company=job.company,
            personas=personas,
            limit=max_contacts
        )
        
        if not contacts:
            print(f"   ⚠️ No contacts found for {job.company}")
            return result
        
        result["contacts_found"] = len(contacts)
        
        # 2. Save contacts
        for contact in contacts:
            contact.job_id = job.id
            self.db.add_contact(contact)
        
        # 3. Create personalized emails
        emails = []
        for contact in contacts:
            email = await self._create_email_for_contact(contact, job)
            if email:
                emails.append(email)
        
        result["emails_created"] = len(emails)
        
        # 4. Schedule emails
        if emails:
            scheduled = self.scheduler.schedule_batch(emails)
            result["emails_scheduled"] = len(scheduled)
        
        print(f"   ✅ Campaign created: {result['emails_scheduled']} emails scheduled")
        return result
    
    async def _create_email_for_contact(
        self,
        contact: Contact,
        job: Job = None
    ) -> Optional[ColdEmail]:
        """Create a personalized email for a contact"""
        
        # Get appropriate template
        template = self.templates.get_initial_template(contact.persona)
        if not template:
            template = self.templates.get_template("recruiter_intro")
        
        if not template:
            return None
        
        # Get template variables
        variables = get_template_variables(contact, job)
        
        # Generate personalized hook
        hook = await self.personalizer.generate_personalized_hook(contact, job)
        variables["personalized_hook"] = hook
        
        # Render template
        subject, body = self.templates.render_template(template, variables)
        
        # Create email
        email = ColdEmail(
            contact_id=contact.id,
            job_id=job.id if job else None,
            template_id=template.id,
            subject=subject,
            body=body,
            status=EmailStatus.DRAFT,
            personalization_data=variables,
        )
        
        return email
    
    async def send_email_now(self, email_id: str) -> bool:
        """Send a specific email immediately"""
        email = self.db.get_cold_email(email_id)
        if not email:
            return False
        
        return await self.sender.send(email)
    
    async def process_scheduled(self) -> dict:
        """Process all scheduled emails that are due"""
        return await self.sender.process_pending()
    
    async def schedule_followups(self) -> int:
        """Schedule follow-up emails for sent emails without replies"""
        sent_emails = self.db.get_cold_emails_by_status(EmailStatus.SENT)
        followups_created = 0
        
        for email in sent_emails:
            # Skip if already has a followup
            if email.followup_number >= 2:  # Max 2 followups
                continue
            
            # Check if enough time has passed
            if not email.sent_at:
                continue
            
            next_followup_num = email.followup_number + 1
            delay_days = self.scheduler.FOLLOWUP_DELAYS.get(next_followup_num, 7)
            
            days_since_sent = (datetime.now() - email.sent_at).days
            
            if days_since_sent >= delay_days:
                followup = self.scheduler.schedule_followup(
                    email.id, 
                    next_followup_num
                )
                if followup:
                    # Fill in template
                    contact = self.db.get_contact(email.contact_id)
                    if contact:
                        template = self.templates.get_followup_template(delay_days)
                        if template:
                            variables = email.personalization_data
                            variables["original_subject"] = email.subject
                            _, body = self.templates.render_template(template, variables)
                            followup.body = body
                    
                    self.db.add_cold_email(followup)
                    followups_created += 1
        
        return followups_created
    
    def get_stats(self) -> dict:
        """Get cold email campaign statistics"""
        return self.db.get_email_stats()
    
    def get_all_emails(self, limit: int = 100) -> list[ColdEmail]:
        """Get all cold emails"""
        return self.db.get_all_cold_emails(limit)
    
    def get_all_contacts(self, limit: int = 100) -> list[Contact]:
        """Get all contacts"""
        return self.db.get_all_contacts(limit)


# Singleton instance
_service: Optional[ColdEmailService] = None


def get_cold_email_service() -> ColdEmailService:
    global _service
    if _service is None:
        _service = ColdEmailService()
    return _service
