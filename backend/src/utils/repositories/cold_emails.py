"""Cold-email persistence + stats. Uses self.session()."""
from datetime import datetime
from typing import Optional

from src.core.cold_email_models import ColdEmail, EmailStatus
from src.utils.models import ColdEmailModel


class ColdEmailRepositoryMixin:
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
