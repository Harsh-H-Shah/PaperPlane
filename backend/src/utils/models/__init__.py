"""SQLAlchemy ORM models.

Import models from here (or via the `src.utils.database` re-export shim).
All models share the single `Base` defined in base.py.
"""
from src.utils.models.base import Base
from src.utils.models.job import JobModel, ApplicationModel
from src.utils.models.preferences import UserPreferencesModel
from src.utils.models.cold_email import (
    ContactModel,
    EmailTemplateModel,
    ColdEmailModel,
)

__all__ = [
    "Base",
    "JobModel",
    "ApplicationModel",
    "UserPreferencesModel",
    "ContactModel",
    "EmailTemplateModel",
    "ColdEmailModel",
]
