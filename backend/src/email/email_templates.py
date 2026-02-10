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
        """Ensure default templates exist in database, and clean up removed ones"""
        default_ids = {t.id for t in DEFAULT_TEMPLATES}
        
        # Update/insert current defaults
        for template in DEFAULT_TEMPLATES:
            self.db.add_template(template)
        
        # Remove templates that are no longer in defaults (but keep custom ones)
        existing = self.db.get_all_templates()
        for t in existing:
            if not t.id.startswith("custom_") and t.id not in default_ids:
                self.db.delete_template(t.id)
    
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


def _extract_skills_text(applicant) -> str:
    """
    Extract a clean, readable skills string from applicant data.
    Handles both Skills objects and raw dict/list structures.
    """
    if not hasattr(applicant, 'skills') or not applicant.skills:
        return "full-stack development"
    
    skills_obj = applicant.skills
    top_skills = []
    
    # Handle Skills object with programming_languages (Skill objects)
    if hasattr(skills_obj, 'programming_languages') and skills_obj.programming_languages:
        langs = skills_obj.programming_languages
        if isinstance(langs, list):
            if langs and hasattr(langs[0], 'name'):
                top_skills.extend([s.name for s in langs[:3]])
            else:
                top_skills.extend([str(s) for s in langs[:3]])
    
    # Handle raw "languages" field (list of strings — Harsh's format)
    if not top_skills and hasattr(skills_obj, 'languages') and skills_obj.languages:
        if isinstance(skills_obj.languages, list):
            top_skills.extend(skills_obj.languages[:3])
    
    # Handle Skills object — also a plain dict
    if not top_skills and isinstance(skills_obj, dict):
        for key in ['languages', 'programming_languages']:
            raw = skills_obj.get(key, [])
            if raw and isinstance(raw, list):
                for item in raw[:3]:
                    if isinstance(item, dict) and 'name' in item:
                        top_skills.append(item['name'])
                    elif isinstance(item, str):
                        top_skills.append(item)
                break

    # Add frameworks if we have room
    frameworks = []
    if hasattr(skills_obj, 'frameworks') and skills_obj.frameworks:
        frameworks = skills_obj.frameworks if isinstance(skills_obj.frameworks, list) else []
    elif isinstance(skills_obj, dict):
        frameworks = skills_obj.get('frameworks', [])
    
    if frameworks:
        top_skills.extend(frameworks[:2])
    
    # Use all_technical as final fallback
    if not top_skills and hasattr(skills_obj, 'all_technical') and skills_obj.all_technical:
        top_skills = skills_obj.all_technical[:4]
    
    # Deduplicate, pick top 3-4
    seen = set()
    unique = []
    for s in top_skills:
        s_str = str(s)
        if s_str.lower() not in seen:
            seen.add(s_str.lower())
            unique.append(s_str)
    unique = unique[:4]
    
    if not unique:
        return "full-stack development"
    if len(unique) == 1:
        return unique[0]
    if len(unique) == 2:
        return f"{unique[0]} and {unique[1]}"
    return f"{', '.join(unique[:-1])}, and {unique[-1]}"


def _extract_recent_work(applicant) -> str:
    """Extract a short, natural phrase about recent work — no trailing period."""
    if not hasattr(applicant, 'experience') or not applicant.experience:
        return "building production systems"
    
    exp = applicant.experience[0]
    company = getattr(exp, 'company', '') or ''
    description = getattr(exp, 'description', '') or ''
    
    # Clean up combined company names (e.g. "Stony Brook University | Mechanismic Inc.")
    if '|' in company:
        company = company.split('|')[-1].strip()
    
    # Try to use a short, specific description if available
    if description:
        # Clean it: lowercase first letter, strip trailing period
        desc = description.rstrip('.')
        if len(desc) < 80:
            # Make it lowercase to flow as "I've spent time {desc}"
            return desc[0].lower() + desc[1:]
    
    if company:
        return f"building software at {company.rstrip('.')}"
    return "building production systems"


def _extract_current_role(applicant) -> str:
    """Extract current role title, short and clean."""
    if not hasattr(applicant, 'experience') or not applicant.experience:
        return "Software Engineer"
    
    exp = applicant.experience[0]
    title = getattr(exp, 'title', '') or ''
    
    # Shorten long titles
    if title:
        # "Graduate Software Research Assistant" -> keep as is, it's descriptive
        return title
    return "Software Engineer"


def _extract_highlights(applicant) -> str:
    """Build a short, punchy highlights sentence from the applicant's best stuff."""
    parts = []
    
    # Check for notable companies
    if hasattr(applicant, 'experience') and applicant.experience:
        notable_companies = []
        for exp in applicant.experience:
            company = getattr(exp, 'company', '') or ''
            if 'meta' in company.lower() or 'facebook' in company.lower():
                notable_companies.append('Meta')
            elif 'google' in company.lower():
                notable_companies.append('Google')
            elif 'amazon' in company.lower() or 'aws' in company.lower():
                notable_companies.append('Amazon')
            elif 'apple' in company.lower():
                notable_companies.append('Apple')
            elif 'microsoft' in company.lower():
                notable_companies.append('Microsoft')
        
        if notable_companies:
            parts.append(f"I've interned at {' and '.join(notable_companies[:2])}")
    
    # Check for education
    if hasattr(applicant, 'education') and applicant.education:
        edu = applicant.education[0]
        degree = getattr(edu, 'degree', '') or ''
        institution = getattr(edu, 'institution', '') or ''
        if degree and institution:
            short_degree = degree
            if 'master' in degree.lower():
                field = getattr(edu, 'field', '') or ''
                short_degree = f"MS {field}" if field else "MS"
            elif 'bachelor' in degree.lower():
                field = getattr(edu, 'field', '') or ''
                short_degree = f"BS {field}" if field else "BS"
            
            short_uni = institution
            for prefix in ['University of ', 'The ']:
                if short_uni.startswith(prefix):
                    short_uni = short_uni[len(prefix):]
            
            if parts:
                parts.append(f"currently finishing my {short_degree} at {short_uni}")
            else:
                parts.append(f"I'm currently finishing my {short_degree} at {short_uni}")
    
    if parts:
        return ', '.join(parts)
    
    # Fallback to achievements
    if hasattr(applicant, 'achievements') and applicant.achievements:
        achievement = applicant.achievements[0]
        name = getattr(achievement, 'name', '') or (achievement.get('name', '') if isinstance(achievement, dict) else '')
        if name:
            return name
    
    return "I have experience building production systems end-to-end"


def _extract_standout(applicant) -> str:
    """One standout fact — a short 'wow' line that fits naturally in an email."""
    
    # Check for notable open source / projects first (most impressive in emails)
    if hasattr(applicant, 'projects') and applicant.projects:
        for proj in applicant.projects:
            name = getattr(proj, 'name', '') or (proj.get('name', '') if isinstance(proj, dict) else '')
            name_lower = name.lower()
            if any(notable in name_lower for notable in ['metamask', 'bitcoin', 'ethereum']):
                # Extract the brand name (after — or – separator)
                brand = None
                for sep in ['—', '–', '-']:
                    if sep in name:
                        brand = name.split(sep)[-1].strip()
                        break
                if not brand:
                    brand = name.split('—')[0].strip()
                return f"I've also contributed to {brand} open source."
    
    # Check for hackathon wins
    if hasattr(applicant, 'achievements') and applicant.achievements:
        for ach in applicant.achievements:
            name = getattr(ach, 'name', '') or (ach.get('name', '') if isinstance(ach, dict) else '')
            if name and 'won' in name.lower():
                return name + '.'
    
    # Check for publications
    if hasattr(applicant, 'publications') and applicant.publications:
        return "I've also published research in the space."
    
    return ""


def get_template_variables(
    contact: Contact,
    job = None,
    applicant = None,
    personalized_hook: str = ""
) -> dict:
    """
    Build template variables from contact, job, and applicant data.
    Handles missing fields gracefully.
    """
    # Safely extract first name
    first_name = ""
    if contact and contact.name:
        name_parts = contact.name.strip().split()
        first_name = name_parts[0] if name_parts else contact.name
    
    company_name = (contact.company if contact else "") or "your company"
    
    variables = {
        # Contact info
        "first_name": first_name or "there",
        "recipient_name": (contact.name if contact else "") or "there",
        "recipient_title": (contact.title if contact else "") or "",
        "company": company_name,
        
        # Personalization hook
        "personalized_hook": personalized_hook or f"I came across {company_name} and was impressed by what you're building.",
    }
    
    # Job info
    if job:
        variables.update({
            "job_title": job.title or "Software Engineer",
            "job_url": getattr(job, 'url', '') or '',
            "original_subject": f"{job.title} at {job.company}" if job.title and job.company else f"Opportunity at {company_name}",
        })
    else:
        variables["job_title"] = "Software Engineer"
        variables["original_subject"] = f"Opportunity at {company_name}"
    
    # Applicant info
    if applicant:
        variables.update({
            "my_name": getattr(applicant, 'full_name', '') or getattr(applicant, 'name', '') or "Your Name",
            "my_email": getattr(applicant, 'email', '') or "",
            "my_phone": getattr(applicant, 'phone', '') or '',
            "my_skills": _extract_skills_text(applicant),
            "my_recent_work": _extract_recent_work(applicant),
            "my_current_role": _extract_current_role(applicant),
            "my_highlights": _extract_highlights(applicant),
            "my_standout": _extract_standout(applicant),
            "company_excitement": f"what {variables['company']} is building",
            "tech_highlight": "your engineering culture",
        })
    else:
        variables.update({
            "my_name": "Your Name",
            "my_email": "",
            "my_skills": "full-stack development",
            "my_recent_work": "building production systems",
            "my_current_role": "Software Engineer",
            "my_highlights": "I have experience building production systems end-to-end.",
            "my_standout": "",
            "company_excitement": f"what {company_name} is building",
            "tech_highlight": "your engineering culture",
        })
    
    return variables
