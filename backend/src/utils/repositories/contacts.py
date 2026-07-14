"""Contact persistence for cold-email outreach. Uses self.session()."""
from typing import Optional

from src.core.cold_email_models import Contact
from src.utils.models import ContactModel


class ContactRepositoryMixin:
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
