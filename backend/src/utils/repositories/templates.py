"""Email-template persistence. Uses self.session()."""
from datetime import datetime
from typing import Optional

from src.core.cold_email_models import EmailTemplate, ContactPersona
from src.utils.models import EmailTemplateModel


class TemplateRepositoryMixin:
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
                (EmailTemplateModel.persona_type.is_(None))
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
