"""Single source of truth for filesystem locations.

Every path the backend needs (data dir, database, profile, logs, config, .env)
resolves from the **repository root**, independent of the current working
directory. This is why the app behaves the same whether you launch it from the
repo root, from `backend/`, or inside Docker.

Do NOT hardcode `"data/..."` or `"logs/..."` strings elsewhere — import the
helper from here instead. That was the source of the historical "two databases"
bug (a cwd-relative path sent local dev to `backend/data/` while Docker used the
mounted `/app/data`).
"""

from functools import lru_cache
from pathlib import Path

# In the Docker image the backend is copied to /app (WORKDIR), and the repo's
# ./data and ./logs are bind-mounted to /app/data and /app/logs.
_DOCKER_ROOT = Path("/app")


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Absolute path to the project root, regardless of where we were launched."""
    if (_DOCKER_ROOT / "main.py").exists():
        return _DOCKER_ROOT
    # This file lives at <repo>/backend/src/utils/paths.py
    return Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    return repo_root() / "data"


def logs_dir() -> Path:
    return repo_root() / "logs"


def config_dir() -> Path:
    return repo_root() / "config"


def env_file() -> Path:
    return repo_root() / ".env"


# --- Convenience file/dir paths (all live under data/ or logs/) ---

def db_path() -> Path:
    return data_dir() / "applications.db"


def profile_path() -> Path:
    return data_dir() / "profile.json"


def resume_path() -> Path:
    return data_dir() / "resume.pdf"


def llm_usage_path() -> Path:
    return data_dir() / "llm_usage.json"


def screenshots_dir() -> Path:
    return data_dir() / "screenshots"


def browser_context_dir() -> Path:
    return data_dir() / "browser_context"


def settings_file() -> Path:
    return config_dir() / "settings.yaml"


def activity_log() -> Path:
    return logs_dir() / "activity.log"


def resolve_under_root(path: str | Path) -> Path:
    """Resolve a possibly-relative path against the repo root.

    Absolute paths are returned unchanged; relative ones (e.g. a value read from
    settings.yaml like "data/applications.db") are anchored to the repo root.
    """
    p = Path(path)
    return p if p.is_absolute() else repo_root() / p


def ensure_directories() -> None:
    """Create the standard runtime directories if they don't exist."""
    for d in (data_dir(), screenshots_dir(), logs_dir(), config_dir()):
        d.mkdir(parents=True, exist_ok=True)
