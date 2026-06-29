"""Alembic environment.

Derives the database URL from src.utils.paths (the same location get_db() uses)
and targets Base.metadata so autogenerate sees every model.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `src` importable when Alembic runs from the backend/ dir.
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import paths  # noqa: E402
from src.utils.database import Base  # noqa: E402  (re-exports the single Base + registers all models)

config = context.config

# Resolve the database URL. Precedence:
#   1. a url already set on the Config (programmatic callers pass self.db_path)
#   2. ALEMBIC_DB_URL env var (used to autogenerate the baseline vs a temp DB)
#   3. the real database path from src.utils.paths (CLI default)
_url = (
    config.get_main_option("sqlalchemy.url")
    or os.environ.get("ALEMBIC_DB_URL")
    or f"sqlite:///{paths.db_path()}"
)
config.set_main_option("sqlalchemy.url", _url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER support
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # required for SQLite ALTER support
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
