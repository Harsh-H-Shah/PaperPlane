"""ORM models for the cold-email subsystem: contacts, templates, cold emails."""
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON

from src.core.cold_email_models import (
    Contact, EmailTemplate, ColdEmail,
    ContactPersona, ContactSource, EmailStatus,
)
from src.utils.models.base import Base


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
