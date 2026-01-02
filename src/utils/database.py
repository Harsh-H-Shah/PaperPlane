"""
Database utilities - SQLite with SQLAlchemy ORM
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from src.core.job import Job, JobStatus, JobSource, ApplicationType
from src.core.application import Application, ApplicationStatus

Base = declarative_base()


class JobModel(Base):
    """SQLAlchemy model for Job"""
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
        """Convert to Job model"""
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
        """Create from Job model"""
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
    """SQLAlchemy model for Application"""
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


class Database:
    """
    Database manager for AutoApplier.
    Handles all database operations with SQLite.
    """
    
    def __init__(self, db_path: str = "data/applications.db", echo: bool = False):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=echo,
            connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def session(self) -> Session:
        """Get a database session"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # Job operations
    def add_job(self, job: Job) -> str:
        """Add a job to the database"""
        job_id = job.id or str(hash(job.url))
        job.id = job_id
        
        with self.session() as session:
            # Check if exists
            existing = session.query(JobModel).filter(JobModel.url == job.url).first()
            if existing:
                return existing.id
            
            job_model = JobModel.from_job(job)
            session.add(job_model)
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with self.session() as session:
            job_model = session.query(JobModel).filter(JobModel.id == job_id).first()
            return job_model.to_job() if job_model else None
    
    def get_job_by_url(self, url: str) -> Optional[Job]:
        """Get a job by URL"""
        with self.session() as session:
            job_model = session.query(JobModel).filter(JobModel.url == url).first()
            return job_model.to_job() if job_model else None
    
    def get_jobs_by_status(self, status: JobStatus, limit: int = 100) -> list[Job]:
        """Get jobs by status"""
        with self.session() as session:
            job_models = session.query(JobModel).filter(
                JobModel.status == status.value
            ).limit(limit).all()
            return [jm.to_job() for jm in job_models]
    
    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        """Get jobs ready for application"""
        return self.get_jobs_by_status(JobStatus.NEW, limit) + \
               self.get_jobs_by_status(JobStatus.QUEUED, limit)
    
    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        """Update job status"""
        with self.session() as session:
            job_model = session.query(JobModel).filter(JobModel.id == job_id).first()
            if job_model:
                job_model.status = status.value
                if status == JobStatus.APPLIED:
                    job_model.applied_at = datetime.now()
    
    def get_job_stats(self) -> dict:
        """Get job statistics"""
        with self.session() as session:
            total = session.query(JobModel).count()
            applied = session.query(JobModel).filter(
                JobModel.status == JobStatus.APPLIED.value
            ).count()
            pending = session.query(JobModel).filter(
                JobModel.status.in_([JobStatus.NEW.value, JobStatus.QUEUED.value])
            ).count()
            failed = session.query(JobModel).filter(
                JobModel.status == JobStatus.FAILED.value
            ).count()
            
            return {
                "total": total,
                "applied": applied,
                "pending": pending,
                "failed": failed,
            }
    
    # Application operations
    def add_application(self, application: Application) -> str:
        """Add an application record"""
        app_id = application.id or f"app_{application.job_id}_{int(datetime.now().timestamp())}"
        application.id = app_id
        
        with self.session() as session:
            app_model = ApplicationModel(
                id=app_id,
                job_id=application.job_id,
                job_title=application.job_title,
                company=application.company,
                job_url=application.job_url,
                application_type=application.application_type,
                status=application.status,
                created_at=application.created_at,
                questions=[q.model_dump() for q in application.questions],
                logs=[log.model_dump() for log in application.logs],
            )
            session.add(app_model)
        
        return app_id
    
    def update_application(self, application: Application) -> None:
        """Update an application record"""
        with self.session() as session:
            app_model = session.query(ApplicationModel).filter(
                ApplicationModel.id == application.id
            ).first()
            
            if app_model:
                app_model.status = application.status
                app_model.started_at = application.started_at
                app_model.completed_at = application.completed_at
                app_model.current_step = application.current_step
                app_model.total_steps = application.total_steps
                app_model.questions = [q.model_dump() for q in application.questions]
                app_model.logs = [log.model_dump() for log in application.logs]
                app_model.error_message = application.error_message
                app_model.retry_count = application.retry_count


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get the global database instance"""
    global _db
    if _db is None:
        from src.utils.config import get_settings
        settings = get_settings()
        _db = Database(
            db_path=settings.database.path,
            echo=settings.database.echo
        )
    return _db
