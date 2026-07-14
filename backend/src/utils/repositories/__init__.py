"""Domain repository mixins composed by Database (src/utils/database.py).

Each mixin groups one domain's queries and relies on the host class providing a
``self.session()`` context manager.
"""
from src.utils.repositories.jobs import JobRepositoryMixin
from src.utils.repositories.applications import ApplicationRepositoryMixin
from src.utils.repositories.contacts import ContactRepositoryMixin
from src.utils.repositories.templates import TemplateRepositoryMixin
from src.utils.repositories.cold_emails import ColdEmailRepositoryMixin

__all__ = [
    "JobRepositoryMixin",
    "ApplicationRepositoryMixin",
    "ContactRepositoryMixin",
    "TemplateRepositoryMixin",
    "ColdEmailRepositoryMixin",
]
