"""
Email Templates - High-converting templates for cold outreach.
Provides built-in templates and template rendering with variable substitution.
"""
import re
from typing import Optional
from datetime import datetime

from src.core.cold_email_models import (
    EmailTemplate, Contact, ContactPersona, DEFAULT_TEMPLATES
)
from src.utils.database import get_db


class TemplateManager:
    """Manages email templates and rendering"""
    
    def __init__(self):
        self.db = get_db()
        self._ensure_default_templates()
    
    def _ensure_default_templates(self):
        """Ensure default templates exist in database"""
        for template in DEFAULT_TEMPLATES:
            self.db.add_template(template)
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a template by ID"""
        return self.db.get_template(template_id)
    
    def get_all_templates(self) -> list[EmailTemplate]:
        """Get all templates"""
        return self.db.get_all_templates()
    
    def get_templates_for_persona(self, persona: ContactPersona) -> list[EmailTemplate]:
        """Get templates suitable for a persona"""
        return self.db.get_templates_for_persona(persona)
    
    def get_initial_template(self, persona: ContactPersona) -> Optional[EmailTemplate]:
        """Get the best initial template for a persona"""
        templates = self.get_templates_for_persona(persona)
        initial_templates = [t for t in templates if not t.is_followup]
        return initial_templates[0] if initial_templates else None
    
    def get_followup_template(self, day: int) -> Optional[EmailTemplate]:
        """Get followup template for specific day"""
        templates = self.db.get_all_templates()
        for t in templates:
            if t.is_followup and t.followup_day == day:
                return t
        return None
    
    def render_template(
        self, 
        template: EmailTemplate, 
        variables: dict
    ) -> tuple[str, str]:
        """
        Render template with variables.
        Returns (subject, body) tuple.
        """
        subject = self._substitute_variables(template.subject, variables)
        body = self._substitute_variables(template.body, variables)
        return subject, body
    
    def _substitute_variables(self, text: str, variables: dict) -> str:
        """Replace {variable} placeholders with actual values"""
        result = text
        
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value) if value else "")
        
        # Clean up any unreplaced placeholders
        result = re.sub(r'\{[a-z_]+\}', '', result)
        
        return result.strip()
    
    def add_custom_template(
        self,
        name: str,
        subject: str,
        body: str,
        persona_type: ContactPersona = None,
        is_followup: bool = False,
        followup_day: int = 0
    ) -> str:
        """Add a custom template"""
        template_id = f"custom_{name.lower().replace(' ', '_')}"
        
        template = EmailTemplate(
            id=template_id,
            name=name,
            subject=subject,
            body=body,
            persona_type=persona_type,
            is_followup=is_followup,
            followup_day=followup_day,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        return self.db.add_template(template)


def get_template_variables(
    contact: Contact,
    job = None,
    applicant = None,
    personalized_hook: str = ""
) -> dict:
    """
    Build template variables from contact, job, and applicant data.
    """
    variables = {
        # Contact info
        "first_name": contact.first_name,
        "recipient_name": contact.name,
        "recipient_title": contact.title,
        "company": contact.company,
        
        # Personalization
        "personalized_hook": personalized_hook,
    }
    
    # Add job info if available
    if job:
        variables.update({
            "job_title": job.title,
            "job_url": job.url,
            "original_subject": f"Re: {job.title} at {job.company}",
        })
    else:
        variables["job_title"] = "Software Engineer"
        variables["original_subject"] = f"Re: Opportunity at {contact.company}"
    
    # Add applicant info if available  
    if applicant:
        variables.update({
            "my_name": applicant.full_name,
            "my_email": applicant.email,
            "my_phone": getattr(applicant, 'phone', ''),
            "my_skills": ", ".join(applicant.skills[:3]) if hasattr(applicant, 'skills') else "software engineering",
            "my_recent_work": "building scalable applications",
            "company_excitement": f"the innovative work {contact.company} is doing",
            "tech_highlight": "your engineering culture",
        })
    else:
        # Defaults
        variables.update({
            "my_name": "Your Name",
            "my_email": "your.email@example.com",
            "my_skills": "software engineering",
            "my_recent_work": "building scalable applications",
            "company_excitement": f"the innovative work {contact.company} is doing",
            "tech_highlight": "your engineering culture",
        })
    
    return variables
