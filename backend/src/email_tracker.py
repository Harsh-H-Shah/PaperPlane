import re
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


from src.utils.config import get_settings
from src.utils.database import get_db
from src.core.job import JobStatus


class EmailType(str, Enum):
    REJECTION = "rejection"
    INTERVIEW = "interview"
    CONFIRMATION = "confirmation"
    STATUS_UPDATE = "status_update"
    UNKNOWN = "unknown"


@dataclass
class ParsedEmail:
    subject: str
    sender: str
    body: str
    date: datetime
    email_type: EmailType
    company: Optional[str] = None
    confidence: float = 0.0


class EmailPatterns:
    REJECTION_PATTERNS = [
        r"unfortunately.*not.*moving forward", r"after careful consideration.*not",
        r"will not be moving forward", r"decided.*not.*proceed", r"unable to offer.*position",
        r"decided to move forward with other candidates", r"not selected for",
        r"we regret to inform", r"we have decided to pursue other candidates",
        r"position has been filled", r"we will not be proceeding", r"thank you for.*applying.*however",
    ]
    
    INTERVIEW_PATTERNS = [
        r"schedule.*interview", r"invite.*interview", r"would like to.*interview",
        r"next.*round", r"phone screen", r"technical interview", r"onsite",
        r"meet.*team", r"availability.*call", r"book.*time", r"calendly",
    ]
    
    CONFIRMATION_PATTERNS = [
        r"application.*received", r"thank.*for applying",
        r"we have received your application", r"application submitted", r"your application to",
    ]
    
    JOB_SENDERS = [
        "greenhouse.io", "lever.co", "workday", "ashby", "careers",
        "talent", "recruiting", "hr@", "jobs@", "no-reply", "noreply",
    ]


class EmailTracker:
    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()
        self.patterns = EmailPatterns()
    
    def classify_email(self, subject: str, body: str, sender: str) -> tuple[EmailType, float]:
        text = f"{subject} {body}".lower()
        
        for pattern in self.patterns.REJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return EmailType.REJECTION, 0.9
        
        for pattern in self.patterns.INTERVIEW_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return EmailType.INTERVIEW, 0.85
        
        for pattern in self.patterns.CONFIRMATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return EmailType.CONFIRMATION, 0.8
        
        return EmailType.UNKNOWN, 0.0
    
    def extract_company(self, sender: str, subject: str, body: str) -> Optional[str]:
        if "@" in sender:
            domain = sender.split("@")[1].split(".")[0]
            if domain not in ["gmail", "outlook", "yahoo", "hotmail"]:
                return domain.title()
        
        match = re.search(r"application to\s+([A-Z][a-zA-Z\s]+)", subject)
        if match:
            return match.group(1).strip()
        
        return None
    
    def is_job_related(self, sender: str, subject: str) -> bool:
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        for pattern in self.patterns.JOB_SENDERS:
            if pattern in sender_lower:
                return True
        
        job_keywords = ["application", "job", "position", "role", "interview", "candidate"]
        for kw in job_keywords:
            if kw in subject_lower:
                return True
        
        return False
    
    def update_job_status(self, company: str, email_type: EmailType) -> bool:
        from src.utils.database import JobModel
        
        with self.db.session() as session:
            jobs = session.query(JobModel).filter(
                JobModel.company.ilike(f"%{company}%"),
                JobModel.status.in_([
                    JobStatus.APPLIED.value,
                    JobStatus.IN_PROGRESS.value,
                    JobStatus.NEEDS_REVIEW.value,
                ])
            ).all()
            
            if not jobs:
                return False
            
            new_status = None
            if email_type == EmailType.REJECTION:
                new_status = "rejected"
            elif email_type == EmailType.INTERVIEW:
                new_status = "interview"
            
            if new_status:
                for job in jobs:
                    job.status = new_status
                return True
        
        return False
    
    def parse_email(self, subject: str, body: str, sender: str, date: datetime = None) -> Optional[ParsedEmail]:
        if not self.is_job_related(sender, subject):
            return None
        
        email_type, confidence = self.classify_email(subject, body, sender)
        company = self.extract_company(sender, subject, body)
        
        return ParsedEmail(
            subject=subject,
            sender=sender,
            body=body[:500],
            date=date or datetime.now(),
            email_type=email_type,
            company=company,
            confidence=confidence,
        )
    
    async def check_gmail(self, max_results: int = 50) -> list[ParsedEmail]:
        print("📧 Gmail integration requires OAuth2 setup.")
        return []


NEW_STATUSES = {
    "rejected": "Application rejected",
    "interview": "Interview scheduled",
    "offer": "Offer received",
}
