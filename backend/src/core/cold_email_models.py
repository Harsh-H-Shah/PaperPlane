"""
Cold Email Models - Core data structures for cold email outreach.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class ContactPersona(str, Enum):
    """Target personas for cold outreach"""
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    ENGINEERING_MANAGER = "engineering_manager"
    HR = "hr"
    TALENT_ACQUISITION = "talent_acquisition"
    UNKNOWN = "unknown"


class ContactSource(str, Enum):
    """Source of contact information"""
    APOLLO = "apollo"
    LINKEDIN = "linkedin"
    COMPANY_WEBSITE = "company_website"
    MANUAL = "manual"


class EmailStatus(str, Enum):
    """Status of a cold email"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"


@dataclass
class Contact:
    """A person to cold email"""
    id: str = ""
    name: str = ""
    email: str = ""
    title: str = ""
    company: str = ""
    linkedin_url: Optional[str] = None
    persona: ContactPersona = ContactPersona.UNKNOWN
    source: ContactSource = ContactSource.MANUAL
    job_id: Optional[str] = None  # Link to job application
    created_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None
    
    @property
    def first_name(self) -> str:
        return self.name.split()[0] if self.name else ""


@dataclass
class EmailTemplate:
    """A reusable email template"""
    id: str = ""
    name: str = ""
    subject: str = ""
    body: str = ""
    persona_type: Optional[ContactPersona] = None  # Target persona or None for all
    is_followup: bool = False
    followup_day: int = 0  # Days after initial email (0 = initial)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ColdEmail:
    """An individual cold email"""
    id: str = ""
    contact_id: str = ""
    job_id: Optional[str] = None  
    template_id: Optional[str] = None
    
    # Email content
    subject: str = ""
    body: str = ""
    
    # Status tracking
    status: EmailStatus = EmailStatus.DRAFT
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    
    # Personalization
    personalization_data: dict = field(default_factory=dict)
    
    # Follow-up tracking
    parent_email_id: Optional[str] = None  # Link to original email for follow-ups
    followup_number: int = 0  # 0 = initial, 1 = first followup, etc.
    
    created_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None


# Default email templates
DEFAULT_TEMPLATES = [
    EmailTemplate(
        id="recruiter_intro",
        name="Recruiter Introduction",
        subject="Re: {job_title} at {company} - Quick Question",
        body="""Hi {first_name},

{personalized_hook}

I recently applied for the {job_title} position at {company} and wanted to reach out directly. With my background in {my_skills}, I believe I could make a meaningful contribution to your team.

I'd love to learn more about the role and share how my experience aligns with what you're looking for. Would you have 15 minutes for a quick chat this week?

Best regards,
{my_name}

P.S. Happy to send over my portfolio or any additional materials if helpful!""",
        persona_type=ContactPersona.RECRUITER,
        is_followup=False
    ),
    
    EmailTemplate(
        id="hiring_manager_intro",
        name="Hiring Manager Introduction",
        subject="{job_title} Application - {my_name}",
        body="""Hi {first_name},

{personalized_hook}

I'm reaching out because I applied for the {job_title} role on your team and wanted to express my genuine interest in the position.

What excites me most about this opportunity is {company_excitement}. I've been working on {my_recent_work}, and I see strong alignment with what your team is building.

Would you be open to a brief conversation about the role? I'd love to learn more about your team's priorities and share how I could contribute.

Thanks for considering,
{my_name}""",
        persona_type=ContactPersona.HIRING_MANAGER,
        is_followup=False
    ),
    
    EmailTemplate(
        id="engineering_manager_intro",
        name="Engineering Manager Introduction", 
        subject="Fellow Engineer Interested in {company}",
        body="""Hi {first_name},

{personalized_hook}

I came across the {job_title} role at {company} and was impressed by {tech_highlight}. As someone who specializes in {my_skills}, I'd love to learn more about the technical challenges your team is tackling.

I recently applied through your job board, but wanted to reach out directly to express my enthusiasm for potentially joining your team.

Would you be open to a quick technical chat? I'm genuinely curious about {company}'s engineering culture and stack.

Best,
{my_name}""",
        persona_type=ContactPersona.ENGINEERING_MANAGER,
        is_followup=False
    ),
    
    EmailTemplate(
        id="followup_1",
        name="First Follow-up (Day 3)",
        subject="Re: {original_subject}",
        body="""Hi {first_name},

I wanted to follow up on my previous email about the {job_title} position. I understand how busy things can get!

I'm still very interested in the opportunity and would welcome any chance to discuss how I could contribute to {company}.

Is there a better time or way to connect?

Best,
{my_name}""",
        is_followup=True,
        followup_day=3
    ),
    
    EmailTemplate(
        id="followup_2",
        name="Second Follow-up (Day 7)",
        subject="Re: {original_subject}",
        body="""Hi {first_name},

Just wanted to send one final follow-up regarding the {job_title} role at {company}.

If now isn't the right time, I completely understand. But if there's any opportunity to connect, even briefly, I'd appreciate the chance.

Either way, thanks for your time, and best of luck with your hiring!

Cheers,
{my_name}""",
        is_followup=True,
        followup_day=7
    ),
]
