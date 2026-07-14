"""ORM model for simple key/value user preferences (e.g. valorant_agent)."""
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime

from src.utils.models.base import Base


class UserPreferencesModel(Base):
    """Stores user preferences like valorant_agent selection"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
