"""ORM models for jobs and application attempts."""
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON

from src.core.job import Job, JobStatus, JobSource, ApplicationType
from src.core.application import ApplicationStatus
from src.utils.models.base import Base


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, default="")
    url = Column(String, nullable=False, unique=True)
    apply_url = Column(String)
    description = Column(Text)
    salary_range = Column(String)
    job_type = Column(String)
    experience_level = Column(String)
    remote_type = Column(String)
    source = Column(String, default=JobSource.OTHER.value)
    application_type = Column(String, default=ApplicationType.UNKNOWN.value)
    status = Column(String, default=JobStatus.NEW.value)
    posted_date = Column(DateTime)
    discovered_at = Column(DateTime, default=datetime.now)
    applied_at = Column(DateTime)
    tags = Column(JSON, default=list)
    external_id = Column(String)
    raw_data = Column(JSON)
    match_score = Column(Float)

    def to_job(self) -> Job:
        return Job(
            id=self.id,
            title=self.title,
            company=self.company,
            location=self.location,
            url=self.url,
            apply_url=self.apply_url,
            description=self.description,
            salary_range=self.salary_range,
            job_type=self.job_type,
            experience_level=self.experience_level,
            remote_type=self.remote_type,
            source=JobSource(self.source) if self.source else JobSource.OTHER,
            application_type=ApplicationType(self.application_type) if self.application_type else ApplicationType.UNKNOWN,
            status=JobStatus(self.status) if self.status else JobStatus.NEW,
            posted_date=self.posted_date,
            discovered_at=self.discovered_at,
            applied_at=self.applied_at,
            tags=self.tags or [],
            external_id=self.external_id,
            raw_data=self.raw_data,
            match_score=self.match_score,
        )

    @classmethod
    def from_job(cls, job: Job) -> "JobModel":
        return cls(
            id=job.id or str(hash(job.url)),
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            apply_url=job.apply_url,
            description=job.description,
            salary_range=job.salary_range,
            job_type=job.job_type,
            experience_level=job.experience_level,
            remote_type=job.remote_type,
            source=job.source,
            application_type=job.application_type,
            status=job.status,
            posted_date=job.posted_date,
            discovered_at=job.discovered_at,
            applied_at=job.applied_at,
            tags=job.tags,
            external_id=job.external_id,
            raw_data=job.raw_data,
            match_score=job.match_score,
        )


class ApplicationModel(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False)
    job_title = Column(String)
    company = Column(String)
    job_url = Column(String)
    application_type = Column(String, default=ApplicationType.UNKNOWN.value)
    status = Column(String, default=ApplicationStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer)
    current_page_url = Column(String)
    questions = Column(JSON, default=list)
    logs = Column(JSON, default=list)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    resume_uploaded = Column(Boolean, default=False)
    cover_letter_uploaded = Column(Boolean, default=False)
    screenshots = Column(JSON, default=list)
