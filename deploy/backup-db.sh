#!/bin/bash
# Nightly SQLite backup, safe while the app is running (uses SQLite's online
# backup API). Runs inside the backend container so file ownership matches.
# Keeps the last 14 days in data/backups/.
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose -f docker-compose.prod.yml exec -T backend python - <<'EOF'
import sqlite3
from datetime import date
from pathlib import Path

backups = Path("/app/data/backups")
backups.mkdir(exist_ok=True)

src = sqlite3.connect("/app/data/applications.db")
dst = sqlite3.connect(backups / f"applications-{date.today():%Y-%m-%d}.db")
with dst:
    src.backup(dst)
dst.close()
src.close()

for old in sorted(backups.glob("applications-*.db"))[:-14]:
    old.unlink()
EOF
