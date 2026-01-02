"""
Job data model - represents a job posting
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    """Status of a job in our tracking system"""
    NEW = "new"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class JobSource(str, Enum):
    """Source where the job was discovered"""
    LINKEDIN = "linkedin"
    JOBRIGHT = "jobright"
    SIMPLIFY = "simplify"
    CVRVE = "cvrve"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    COMPANY_SITE = "company_site"
    MANUAL = "manual"
    OTHER = "other"


class ApplicationType(str, Enum):
    """Type of application portal"""
    WORKDAY = "workday"
    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ORACLE = "oracle"
    ADP = "adp"
    ICIMS = "icims"
    TALEO = "taleo"
    JOBVITE = "jobvite"
    LINKEDIN_EASY = "linkedin_easy"
    SMARTRECRUITERS = "smartrecruiters"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class Job(BaseModel):
    """
    Represents a job posting from any source.
    """
    # Unique identifier
    id: Optional[str] = Field(default=None, description="Internal job ID")
    
    # Basic info
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(default="", description="Job location")
    
    # URLs
    url: str = Field(..., description="URL to job posting")
    apply_url: Optional[str] = Field(default=None, description="Direct application URL")
    
    # Job details
    description: Optional[str] = Field(default=None, description="Full job description")
    salary_range: Optional[str] = Field(default=None, description="Salary range if available")
    job_type: Optional[str] = Field(default=None, description="Full-time, Part-time, Contract")
    experience_level: Optional[str] = Field(default=None, description="Entry, Mid, Senior, etc.")
    remote_type: Optional[str] = Field(default=None, description="Remote, Hybrid, On-site")
    
    # Classification
    source: JobSource = Field(default=JobSource.OTHER, description="Where job was found")
    application_type: ApplicationType = Field(
        default=ApplicationType.UNKNOWN, 
        description="Type of application system"
    )
    
    # Status tracking
    status: JobStatus = Field(default=JobStatus.NEW, description="Current status")
    
    # Timestamps
    posted_date: Optional[datetime] = Field(default=None, description="When job was posted")
    discovered_at: datetime = Field(
        default_factory=datetime.now, 
        description="When we discovered this job"
    )
    applied_at: Optional[datetime] = Field(default=None, description="When we applied")
    
    # Additional data
    tags: list[str] = Field(default_factory=list, description="Tags/keywords")
    external_id: Optional[str] = Field(default=None, description="ID from source platform")
    raw_data: Optional[dict] = Field(default=None, description="Raw scraped data")
    
    # Match score (how well it matches user preferences)
    match_score: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Match score 0-1"
    )
    
    class Config:
        use_enum_values = True
    
    def __str__(self) -> str:
        return f"{self.title} at {self.company}"
    
    def __repr__(self) -> str:
        return f"Job(title='{self.title}', company='{self.company}', status='{self.status}')"
    
    @property
    def is_actionable(self) -> bool:
        """Check if this job can be applied to"""
        return self.status in [JobStatus.NEW, JobStatus.QUEUED]
    
    @property  
    def is_linkedin_easy_apply(self) -> bool:
        """Check if this is a LinkedIn Easy Apply job"""
        return self.application_type == ApplicationType.LINKEDIN_EASY
    
    def mark_applied(self) -> None:
        """Mark this job as applied"""
        self.status = JobStatus.APPLIED
        self.applied_at = datetime.now()
    
    def mark_failed(self) -> None:
        """Mark this job as failed"""
        self.status = JobStatus.FAILED
    
    def mark_needs_review(self) -> None:
        """Mark this job as needing human review"""
        self.status = JobStatus.NEEDS_REVIEW
    
    def to_summary(self) -> dict:
        """Return a summary for notifications"""
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source": self.source,
            "status": self.status,
        }
