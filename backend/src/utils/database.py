"""Database access.

`Database` owns the SQLite engine + session lifecycle and gains all its query
methods from the domain repository mixins in src/utils/repositories/. The ORM
models live in src/utils/models/ and are re-exported here so existing imports
like `from src.utils.database import JobModel` keep working.

Use the `get_db()` singleton everywhere; don't construct Database directly.
"""
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import DatabaseError as SQLAlchemyDatabaseError

# Re-export the ORM models so callers can keep importing them from here.
from src.utils.models import (  # noqa: F401
    Base,
    JobModel,
    ApplicationModel,
    UserPreferencesModel,
    ContactModel,
    EmailTemplateModel,
    ColdEmailModel,
)
from src.utils.repositories import (
    JobRepositoryMixin,
    ApplicationRepositoryMixin,
    ContactRepositoryMixin,
    TemplateRepositoryMixin,
    ColdEmailRepositoryMixin,
)


class Database(
    JobRepositoryMixin,
    ApplicationRepositoryMixin,
    ContactRepositoryMixin,
    TemplateRepositoryMixin,
    ColdEmailRepositoryMixin,
):
    def __init__(self, db_path: str | None = None, echo: bool = False):
        from src.utils import paths
        self.db_path = Path(db_path) if db_path else paths.db_path()
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
