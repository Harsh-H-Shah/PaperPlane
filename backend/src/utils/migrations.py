"""Run Alembic migrations programmatically at startup.

Deliberately builds the Config WITHOUT the alembic.ini file so Alembic's
fileConfig() never runs — that would otherwise reconfigure (and disable) the
app's loggers. The DB URL is resolved by alembic/env.py from src.utils.paths,
so it always matches get_db().
"""
from pathlib import Path

from alembic import command
from alembic.config import Config

# src/utils/migrations.py -> parents[2] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_LOCATION = _BACKEND_ROOT / "alembic"


def _config(db_url: str) -> Config:
    cfg = Config()  # no ini file => env.py skips fileConfig (keeps our logging)
    cfg.set_main_option("script_location", str(_SCRIPT_LOCATION))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def stamp_head(db_url: str) -> None:
    """Mark the database as being at the latest revision without running migrations."""
    command.stamp(_config(db_url), "head")


def upgrade_head(db_url: str) -> None:
    """Apply any pending migrations up to the latest revision."""
    command.upgrade(_config(db_url), "head")
