"""The single SQLAlchemy declarative Base shared by every ORM model.

All models must subclass THIS Base so that `Base.metadata` sees every table
(used by create_all on startup and, later, by Alembic autogenerate).
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
