from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON, Enum as SQLEnum,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from src.core.job import Job, JobStatus, JobSource, ApplicationType
from src.core.application import Application, ApplicationStatus

Base = declarative_base()


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


class UserPreferencesModel(Base):
    """Stores user preferences like valorant_agent selection"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Database:
    def __init__(self, db_path: str = "data/applications.db", echo: bool = False):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=echo,
            connect_args={"check_same_thread": False}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def session(self) -> Session:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def add_job(self, job: Job) -> str:
        job_id = job.id or str(hash(job.url))
        job.id = job_id
        
        with self.session() as session:
            existing = session.query(JobModel).filter(JobModel.url == job.url).first()
            if existing:
                # If manual, reset status to NEW to ensure visibility
                if job.source == JobSource.MANUAL or job.source == JobSource.MANUAL.value:
                    existing.status = JobStatus.NEW.value
                    existing.source = JobSource.MANUAL.value
                    existing.discovered_at = datetime.now()
                return existing.id
            
            job_model = JobModel.from_job(job)
            session.add(job_model)
            session.flush()
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        with self.session() as session:
            job_model = session.query(JobModel).filter(JobModel.id == job_id).first()
            return job_model.to_job() if job_model else None
    
            job_model = session.query(JobModel).filter(JobModel.url == url).first()
            return job_model.to_job() if job_model else None
    
    def filter_existing_urls(self, urls: list[str]) -> set[str]:
        if not urls:
            return set()
        
        existing = set()
        # Process in chunks to avoid SQLite limits
        chunk_size = 500
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i:i + chunk_size]
            with self.session() as session:
                results = session.query(JobModel.url).filter(
                    JobModel.url.in_(chunk)
                ).all()
                existing.update(r[0] for r in results)
        return existing
    
    def add_jobs_bulk(self, jobs: list[Job]) -> int:
        if not jobs:
            return 0
            
        count = 0
        with self.session() as session:
            job_models = []
            for job in jobs:
                job.id = job.id or str(hash(job.url))
                job.discovered_at = datetime.now()
                job.status = JobStatus.NEW
                job_models.append(JobModel.from_job(job))
                
            if job_models:
                session.bulk_save_objects(job_models)
                count = len(job_models)
                
        return count
    
    def check_content_duplicates(self, candidates: list[Job]) -> set[str]:
        if not candidates:
            return set()
            
        duplicate_urls = set()
        
        # Prepare candidates for query
        # We check against jobs from last 7 days to keep query efficient
        cutoff_date = datetime.now().strftime("%Y-%m-%d")
        
        # We need to check one by one or construct a complex OR query.
        # A complex OR query is better: (title=t1 AND company=c1) OR (title=t2 AND company=c2)...
        # But SQLite limit is 1000 vars. So batching is needed.
        
        from sqlalchemy import or_, and_, func
        
        chunk_size = 50 
        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i + chunk_size]
            
            conditions = []
            for job in chunk:
                # Basic normalization
                t = job.title.lower().strip()
                c = job.company.lower().strip()
                conditions.append(
                    and_(
                        func.lower(JobModel.title) == t,
                        func.lower(JobModel.company) == c
                    )
                )
            
            if not conditions:
                continue
                
            with self.session() as session:
                matches = session.query(JobModel.url, JobModel.title, JobModel.company).filter(
                    or_(*conditions)
                ).all()
                
                # Double check matches in python to map back to candidate URLs
                # because the query returns existing URLs, we need to know which candidate caused it.
                # Actually, if we find a match (title+company), we just need to flag the candidate that has that title+company.
                
                matched_pairs = set()
                for url, title, company in matches:
                    matched_pairs.add((title.lower().strip(), company.lower().strip()))
                
                for job in chunk:
                    t = job.title.lower().strip()
                    c = job.company.lower().strip()
                    if (t, c) in matched_pairs:
                        duplicate_urls.add(job.url)
                        
        return duplicate_urls
    
    def get_jobs_by_status(self, status: JobStatus, limit: int = 100) -> list[Job]:
        with self.session() as session:
            job_models = session.query(JobModel).filter(
                JobModel.status == status.value
            ).limit(limit).all()
            return [jm.to_job() for jm in job_models]
    
    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        return self.get_jobs_by_status(JobStatus.NEW, limit) + \
               self.get_jobs_by_status(JobStatus.QUEUED, limit)
    
    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        with self.session() as session:
            job_model = session.query(JobModel).filter(JobModel.id == job_id).first()
            if job_model:
                job_model.status = status.value if hasattr(status, 'value') else status
                if status == JobStatus.APPLIED or status == JobStatus.APPLIED.value:
                    job_model.applied_at = datetime.now()
    
    def get_job_stats(self) -> dict:
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
            needs_review = session.query(JobModel).filter(
                JobModel.status == JobStatus.NEEDS_REVIEW.value
            ).count()
            expired = session.query(JobModel).filter(
                JobModel.status == JobStatus.EXPIRED.value
            ).count()
            
            return {
                "total": total,
                "applied": applied,
                "pending": pending,
                "failed": failed,
                "needs_review": needs_review,
                "expired": expired,
            }
    
    def add_application(self, application: Application) -> str:
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
                questions=[q.model_dump(mode='json') for q in application.questions],
                logs=[log.model_dump(mode='json') for log in application.logs],
            )
            session.add(app_model)
        
        return app_id
    
    def update_application(self, application: Application) -> None:
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
                app_model.questions = [q.model_dump(mode='json') for q in application.questions]
                app_model.logs = [log.model_dump(mode='json') for log in application.logs]
                app_model.error_message = application.error_message
                app_model.retry_count = application.retry_count


_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        from src.utils.config import get_settings
        settings = get_settings()
        _db = Database(
            db_path=settings.database.path,
            echo=settings.database.echo
        )
    return _db
