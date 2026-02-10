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


# Default email templates - Short, direct, high-conversion cold emails
DEFAULT_TEMPLATES = [
    # ── Recruiter Templates ──
    EmailTemplate(
        id="recruiter_intro",
        name="Recruiter - Quick Intro",
        subject="{job_title} @ {company} — {my_name}",
        body="""Hi {first_name},

{personalized_hook}

I saw the {job_title} role and wanted to reach out. I'm a {my_current_role} with experience in {my_skills} — most recently {my_recent_work}.

Happy to send over more details or jump on a quick call if the timing works.

Best,
{my_name}""",
        persona_type=ContactPersona.RECRUITER,
        is_followup=False
    ),
    
    EmailTemplate(
        id="recruiter_direct",
        name="Recruiter - Straight to the Point",
        subject="Re: {job_title} at {company}",
        body="""Hi {first_name},

I applied for the {job_title} position and wanted to put a face to the application.

{personalized_hook}

Quick background — {my_highlights}. I think there's a strong fit here and would love to chat if you agree.

{my_name}""",
        persona_type=ContactPersona.RECRUITER,
        is_followup=False
    ),

    # ── Hiring Manager Templates ──
    EmailTemplate(
        id="hiring_manager_intro",
        name="Hiring Manager - Intro",
        subject="{job_title} — {my_name}",
        body="""Hi {first_name},

{personalized_hook}

I'm reaching out about the {job_title} role on your team. I've spent time {my_recent_work} and have hands-on experience with {my_skills}. {my_standout}

Would love to learn more about what your team is working on. Open to a quick chat anytime this week.

Best,
{my_name}""",
        persona_type=ContactPersona.HIRING_MANAGER,
        is_followup=False
    ),
    
    EmailTemplate(
        id="hiring_manager_short",
        name="Hiring Manager - Short & Direct",
        subject="Re: {job_title} @ {company}",
        body="""Hi {first_name},

{personalized_hook}

I applied for the {job_title} role and wanted to connect directly — {my_highlights}.

I'd love to hear about the problems your team is solving. Free for a quick call this week?

Best,
{my_name}""",
        persona_type=ContactPersona.HIRING_MANAGER,
        is_followup=False
    ),

    # ── Engineering Manager Templates ──
    EmailTemplate(
        id="engineering_manager_intro",
        name="Engineering Manager - Intro", 
        subject="Quick note about {job_title} @ {company}",
        body="""Hi {first_name},

{personalized_hook}

I applied for the {job_title} role and wanted to reach out. I'm a {my_current_role} who's worked across {my_skills} — {my_standout}

Curious about the technical challenges your team is focused on. Would you be open to a brief chat?

Best,
{my_name}""",
        persona_type=ContactPersona.ENGINEERING_MANAGER,
        is_followup=False
    ),

    # ── Follow-ups ──
    EmailTemplate(
        id="followup_1",
        name="Follow-up (Day 3)",
        subject="Re: {original_subject}",
        body="""Hi {first_name},

Just bumping this up — I know things get busy. Still very interested in the {job_title} role and would love to connect when you have a moment.

Best,
{my_name}""",
        is_followup=True,
        followup_day=3
    ),
    
    EmailTemplate(
        id="followup_2",
        name="Final Follow-up (Day 7)",
        subject="Re: {original_subject}",
        body="""Hi {first_name},

Last note from me on this — if the timing isn't right, totally understand. But if the {job_title} role is still open, I'd welcome the chance to chat.

Either way, appreciate your time.

{my_name}""",
        is_followup=True,
        followup_day=7
    ),
]
