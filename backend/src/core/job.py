from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    NEW = "new"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    EXPIRED = "expired"
    REJECTED = "rejected"


class JobSource(str, Enum):
    JOBRIGHT = "jobright"
    SIMPLIFY = "simplify"
    CVRVE = "cvrve"
    BUILTIN = "builtin"
    WEWORKREMOTELY = "weworkremotely"
    YC_JOBS = "yc_jobs"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    COMPANY_SITE = "company_site"
    MANUAL = "manual"
    OTHER = "other"


class ApplicationType(str, Enum):
    WORKDAY = "workday"
    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ORACLE = "oracle"
    ADP = "adp"
    ICIMS = "icims"
    TALEO = "taleo"
    JOBVITE = "jobvite"
    SMARTRECRUITERS = "smartrecruiters"
    BUILTIN = "builtin"
    REDIRECTOR = "redirector"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class Job(BaseModel):
    id: Optional[str] = Field(default=None)
    title: str = Field(...)
    company: str = Field(...)
    location: str = Field(default="")
    url: str = Field(...)
    apply_url: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    salary_range: Optional[str] = Field(default=None)
    job_type: Optional[str] = Field(default=None)
    experience_level: Optional[str] = Field(default=None)
    remote_type: Optional[str] = Field(default=None)
    source: JobSource = Field(default=JobSource.OTHER)
    application_type: ApplicationType = Field(default=ApplicationType.UNKNOWN)
    status: JobStatus = Field(default=JobStatus.NEW)
    posted_date: Optional[datetime] = Field(default=None)
    discovered_at: datetime = Field(default_factory=datetime.now)
    applied_at: Optional[datetime] = Field(default=None)
    tags: list[str] = Field(default_factory=list)
    external_id: Optional[str] = Field(default=None)
    raw_data: Optional[dict] = Field(default=None)
    match_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    class Config:
        use_enum_values = True
    
    def __str__(self) -> str:
        return f"{self.title} at {self.company}"
    
    def __repr__(self) -> str:
        return f"Job(title='{self.title}', company='{self.company}', status='{self.status}')"
    
    @property
    def is_actionable(self) -> bool:
        return self.status in [JobStatus.NEW, JobStatus.QUEUED]
    
    
    def mark_applied(self) -> None:
        self.status = JobStatus.APPLIED
        self.applied_at = datetime.now()
    
    def mark_failed(self) -> None:
        self.status = JobStatus.FAILED
    
    def mark_needs_review(self) -> None:
        self.status = JobStatus.NEEDS_REVIEW
    
    def to_summary(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source": self.source,
            "status": self.status,
        }
