from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON, Enum as SQLEnum,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import DatabaseError as SQLAlchemyDatabaseError

from src.core.job import Job, JobStatus, JobSource, ApplicationType
from src.core.application import Application, ApplicationStatus
from src.core.cold_email_models import (
    Contact, EmailTemplate, ColdEmail,
    ContactPersona, ContactSource, EmailStatus
)

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


class ContactModel(Base):
    """Contact for cold email outreach"""
    __tablename__ = "contacts"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    title = Column(String)
    company = Column(String, nullable=False)
    linkedin_url = Column(String)
    persona = Column(String, default=ContactPersona.UNKNOWN.value)
    source = Column(String, default=ContactSource.MANUAL.value)
    job_id = Column(String)  # Optional link to job
    created_at = Column(DateTime, default=datetime.now)
    notes = Column(Text)
    
    def to_contact(self) -> Contact:
        return Contact(
            id=self.id,
            name=self.name,
            email=self.email,
            title=self.title or "",
            company=self.company,
            linkedin_url=self.linkedin_url,
            persona=ContactPersona(self.persona) if self.persona else ContactPersona.UNKNOWN,
            source=ContactSource(self.source) if self.source else ContactSource.MANUAL,
            job_id=self.job_id,
            created_at=self.created_at,
            notes=self.notes,
        )
    
    @classmethod
    def from_contact(cls, contact: Contact) -> "ContactModel":
        return cls(
            id=contact.id or f"contact_{hash(contact.email)}",
            name=contact.name,
            email=contact.email,
            title=contact.title,
            company=contact.company,
            linkedin_url=contact.linkedin_url,
            persona=contact.persona.value if hasattr(contact.persona, 'value') else contact.persona,
            source=contact.source.value if hasattr(contact.source, 'value') else contact.source,
            job_id=contact.job_id,
            created_at=contact.created_at,
            notes=contact.notes,
        )


class EmailTemplateModel(Base):
    """Email template for cold outreach"""
    __tablename__ = "email_templates"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    persona_type = Column(String)  # Target persona or null for all
    is_followup = Column(Boolean, default=False)
    followup_day = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_template(self) -> EmailTemplate:
        return EmailTemplate(
            id=self.id,
            name=self.name,
            subject=self.subject,
            body=self.body,
            persona_type=ContactPersona(self.persona_type) if self.persona_type else None,
            is_followup=self.is_followup,
            followup_day=self.followup_day,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
    
    @classmethod
    def from_template(cls, template: EmailTemplate) -> "EmailTemplateModel":
        return cls(
            id=template.id,
            name=template.name,
            subject=template.subject,
            body=template.body,
            persona_type=template.persona_type.value if template.persona_type else None,
            is_followup=template.is_followup,
            followup_day=template.followup_day,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


class ColdEmailModel(Base):
    """Individual cold email"""
    __tablename__ = "cold_emails"
    
    id = Column(String, primary_key=True)
    contact_id = Column(String, nullable=False)
    job_id = Column(String)
    template_id = Column(String)
    
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    
    status = Column(String, default=EmailStatus.DRAFT.value)
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    replied_at = Column(DateTime)
    
    personalization_data = Column(JSON, default=dict)
    parent_email_id = Column(String)
    followup_number = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.now)
    error_message = Column(Text)
    
    def to_cold_email(self) -> ColdEmail:
        return ColdEmail(
            id=self.id,
            contact_id=self.contact_id,
            job_id=self.job_id,
            template_id=self.template_id,
            subject=self.subject,
            body=self.body,
            status=EmailStatus(self.status) if self.status else EmailStatus.DRAFT,
            scheduled_at=self.scheduled_at,
            sent_at=self.sent_at,
            opened_at=self.opened_at,
            replied_at=self.replied_at,
            personalization_data=self.personalization_data or {},
            parent_email_id=self.parent_email_id,
            followup_number=self.followup_number,
            created_at=self.created_at,
            error_message=self.error_message,
        )
    
    @classmethod
    def from_cold_email(cls, email: ColdEmail) -> "ColdEmailModel":
        return cls(
            id=email.id or f"email_{int(datetime.now().timestamp())}",
            contact_id=email.contact_id,
            job_id=email.job_id,
            template_id=email.template_id,
            subject=email.subject,
            body=email.body,
            status=email.status.value if hasattr(email.status, 'value') else email.status,
            scheduled_at=email.scheduled_at,
            sent_at=email.sent_at,
            opened_at=email.opened_at,
            replied_at=email.replied_at,
            personalization_data=email.personalization_data,
            parent_email_id=email.parent_email_id,
            followup_number=email.followup_number,
            created_at=email.created_at,
            error_message=email.error_message,
        )


class Database:
    def __init__(self, db_path: str = "data/applications.db", echo: bool = False):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._echo = echo
        self.engine, self.SessionLocal = self._create_engine_and_session()

    def _create_engine_and_session(self):
        engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=self._echo,
            connect_args={"check_same_thread": False}
        )
        session_factory = sessionmaker(bind=engine)
        try:
            Base.metadata.create_all(engine)
        except SQLAlchemyDatabaseError as e:
            orig = str(e.orig) if getattr(e, "orig", None) else str(e)
            if "malformed" in orig.lower() or "disk image" in orig.lower():
                engine.dispose()
                if self.db_path.exists():
                    backup_path = self.db_path.with_suffix(self.db_path.suffix + ".corrupted")
                    try:
                        self.db_path.rename(backup_path)
                    except OSError:
                        try:
                            import shutil
                            shutil.copy(self.db_path, backup_path)
                            self.db_path.unlink()
                        except Exception:
                            self.db_path.unlink(missing_ok=True)
                engine = create_engine(
                    f"sqlite:///{self.db_path}",
                    echo=self._echo,
                    connect_args={"check_same_thread": False}
                )
                session_factory = sessionmaker(bind=engine)
                Base.metadata.create_all(engine)
            else:
                raise
        return engine, session_factory
    
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
    
    # ============ Cold Email Methods ============
    
    def add_contact(self, contact: Contact) -> str:
        """Add a contact for cold emailing"""
        contact_id = contact.id or f"contact_{abs(hash(contact.email))}"
        contact.id = contact_id
        
        with self.session() as session:
            existing = session.query(ContactModel).filter(
                ContactModel.email == contact.email
            ).first()
            if existing:
                return existing.id
            
            contact_model = ContactModel.from_contact(contact)
            session.add(contact_model)
        
        return contact_id
    
    def get_contact(self, contact_id: str) -> Optional[Contact]:
        with self.session() as session:
            model = session.query(ContactModel).filter(
                ContactModel.id == contact_id
            ).first()
            return model.to_contact() if model else None
    
    def get_contacts_for_company(self, company: str, limit: int = 50) -> list[Contact]:
        with self.session() as session:
            models = session.query(ContactModel).filter(
                ContactModel.company.ilike(f"%{company}%")
            ).limit(limit).all()
            return [m.to_contact() for m in models]
    
    def get_all_contacts(self, limit: int = 100) -> list[Contact]:
        with self.session() as session:
            models = session.query(ContactModel).order_by(
                ContactModel.created_at.desc()
            ).limit(limit).all()
            return [m.to_contact() for m in models]
    
    def add_contacts_bulk(self, contacts: list[Contact]) -> int:
        if not contacts:
            return 0
        
        count = 0
        with self.session() as session:
            for contact in contacts:
                existing = session.query(ContactModel).filter(
                    ContactModel.email == contact.email
                ).first()
                if not existing:
                    contact.id = contact.id or f"contact_{abs(hash(contact.email))}"
                    session.add(ContactModel.from_contact(contact))
                    count += 1
        
        return count
    
    def add_template(self, template: EmailTemplate) -> str:
        """Add an email template"""
        with self.session() as session:
            existing = session.query(EmailTemplateModel).filter(
                EmailTemplateModel.id == template.id
            ).first()
            if existing:
                # Update existing
                existing.name = template.name
                existing.subject = template.subject
                existing.body = template.body
                existing.updated_at = datetime.now()
                return existing.id
            
            model = EmailTemplateModel.from_template(template)
            session.add(model)
        
        return template.id
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        with self.session() as session:
            model = session.query(EmailTemplateModel).filter(
                EmailTemplateModel.id == template_id
            ).first()
            return model.to_template() if model else None
    
    def get_all_templates(self) -> list[EmailTemplate]:
        with self.session() as session:
            models = session.query(EmailTemplateModel).all()
            return [m.to_template() for m in models]
    
    def get_templates_for_persona(self, persona: ContactPersona) -> list[EmailTemplate]:
        with self.session() as session:
            models = session.query(EmailTemplateModel).filter(
                (EmailTemplateModel.persona_type == persona.value) |
                (EmailTemplateModel.persona_type == None)
            ).all()
            return [m.to_template() for m in models]
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template by ID"""
        with self.session() as session:
            model = session.query(EmailTemplateModel).filter(
                EmailTemplateModel.id == template_id
            ).first()
            if model:
                session.delete(model)
                return True
            return False
    
    def add_cold_email(self, email: ColdEmail) -> str:
        """Add a cold email to queue"""
        email_id = email.id or f"email_{int(datetime.now().timestamp())}"
        email.id = email_id
        
        with self.session() as session:
            model = ColdEmailModel.from_cold_email(email)
            session.add(model)
        
        return email_id
    
    def get_cold_email(self, email_id: str) -> Optional[ColdEmail]:
        with self.session() as session:
            model = session.query(ColdEmailModel).filter(
                ColdEmailModel.id == email_id
            ).first()
            return model.to_cold_email() if model else None
    
    def get_cold_emails_by_status(self, status: EmailStatus, limit: int = 100) -> list[ColdEmail]:
        with self.session() as session:
            models = session.query(ColdEmailModel).filter(
                ColdEmailModel.status == status.value
            ).order_by(ColdEmailModel.scheduled_at).limit(limit).all()
            return [m.to_cold_email() for m in models]
    
    def get_pending_emails(self, limit: int = 50) -> list[ColdEmail]:
        """Get emails scheduled to be sent"""
        with self.session() as session:
            models = session.query(ColdEmailModel).filter(
                ColdEmailModel.status == EmailStatus.SCHEDULED.value,
                ColdEmailModel.scheduled_at <= datetime.now()
            ).order_by(ColdEmailModel.scheduled_at).limit(limit).all()
            return [m.to_cold_email() for m in models]
    
    def update_cold_email_status(self, email_id: str, status: EmailStatus, error: str = None) -> None:
        with self.session() as session:
            model = session.query(ColdEmailModel).filter(
                ColdEmailModel.id == email_id
            ).first()
            if model:
                model.status = status.value
                if status == EmailStatus.SENT:
                    model.sent_at = datetime.now()
                elif status == EmailStatus.OPENED:
                    model.opened_at = datetime.now()
                elif status == EmailStatus.REPLIED:
                    model.replied_at = datetime.now()
                if error:
                    model.error_message = error
    
    def get_all_cold_emails(self, limit: int = 100) -> list[ColdEmail]:
        with self.session() as session:
            models = session.query(ColdEmailModel).order_by(
                ColdEmailModel.created_at.desc()
            ).limit(limit).all()
            return [m.to_cold_email() for m in models]
    
    def get_email_stats(self) -> dict:
        """Get cold email statistics"""
        with self.session() as session:
            total = session.query(ColdEmailModel).count()
            sent = session.query(ColdEmailModel).filter(
                ColdEmailModel.status.in_([
                    EmailStatus.SENT.value, 
                    EmailStatus.OPENED.value, 
                    EmailStatus.REPLIED.value
                ])
            ).count()
            opened = session.query(ColdEmailModel).filter(
                ColdEmailModel.status.in_([
                    EmailStatus.OPENED.value, 
                    EmailStatus.REPLIED.value
                ])
            ).count()
            replied = session.query(ColdEmailModel).filter(
                ColdEmailModel.status == EmailStatus.REPLIED.value
            ).count()
            scheduled = session.query(ColdEmailModel).filter(
                ColdEmailModel.status == EmailStatus.SCHEDULED.value
            ).count()
            
            return {
                "total": total,
                "sent": sent,
                "opened": opened,
                "replied": replied,
                "scheduled": scheduled,
                "open_rate": (opened / sent * 100) if sent > 0 else 0,
                "reply_rate": (replied / sent * 100) if sent > 0 else 0,
            }

    def search_contacts(self, query: str = None, job_id: str = None, persona: str = None, limit: int = 100) -> list[Contact]:
        """Search contacts with optional filters"""
        from sqlalchemy import or_
        with self.session() as session:
            q = session.query(ContactModel)
            if query:
                t = f"%{query}%"
                q = q.filter(or_(ContactModel.name.ilike(t), ContactModel.email.ilike(t), ContactModel.company.ilike(t), ContactModel.title.ilike(t)))
            if job_id:
                q = q.filter(ContactModel.job_id == job_id)
            if persona:
                q = q.filter(ContactModel.persona == persona)
            return [m.to_contact() for m in q.order_by(ContactModel.created_at.desc()).limit(limit).all()]

    def update_contact_fields(self, contact_id: str, **kwargs) -> bool:
        """Update specific fields on a contact"""
        with self.session() as session:
            model = session.query(ContactModel).filter(ContactModel.id == contact_id).first()
            if not model:
                return False
            for k, v in kwargs.items():
                if hasattr(model, k) and v is not None:
                    setattr(model, k, v)
            return True

    def delete_contact(self, contact_id: str) -> bool:
        """Delete a contact"""
        with self.session() as session:
            model = session.query(ContactModel).filter(ContactModel.id == contact_id).first()
            if model:
                session.delete(model)
                return True
            return False

    def search_cold_emails(self, query: str = None, status: str = None, job_id: str = None, contact_id: str = None, limit: int = 100) -> list[ColdEmail]:
        """Search cold emails with optional filters"""
        from sqlalchemy import or_
        with self.session() as session:
            q = session.query(ColdEmailModel)
            if query:
                t = f"%{query}%"
                q = q.filter(or_(ColdEmailModel.subject.ilike(t), ColdEmailModel.body.ilike(t)))
            if status:
                q = q.filter(ColdEmailModel.status == status)
            if job_id:
                q = q.filter(ColdEmailModel.job_id == job_id)
            if contact_id:
                q = q.filter(ColdEmailModel.contact_id == contact_id)
            return [m.to_cold_email() for m in q.order_by(ColdEmailModel.created_at.desc()).limit(limit).all()]

    def update_cold_email_fields(self, email_id: str, **kwargs) -> bool:
        """Update specific fields on a cold email"""
        with self.session() as session:
            model = session.query(ColdEmailModel).filter(ColdEmailModel.id == email_id).first()
            if not model:
                return False
            for k, v in kwargs.items():
                if hasattr(model, k) and v is not None:
                    setattr(model, k, v)
            return True

    def delete_cold_email(self, email_id: str) -> bool:
        """Delete a cold email"""
        with self.session() as session:
            model = session.query(ColdEmailModel).filter(ColdEmailModel.id == email_id).first()
            if model:
                session.delete(model)
                return True
            return False


# Database singleton
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
