# PaperPlane — Development Guide

A short, practical guide to working in this repo: how it's laid out, how to run it,
and the conventions to follow when adding features. Keep this file updated as the
codebase evolves.

> For a snapshot of *what currently works vs. what still needs building*, see
> [CURRENT_STATE.md](CURRENT_STATE.md).

---

## Repository layout

```
paperplane/
├── backend/            # Python: FastAPI dashboard + Typer CLI + automation engine
│   ├── main.py         # CLI entry point (python main.py <command>)
│   ├── scripts/        # Dev/ops scripts (e.g. smoke_api.py)
│   └── src/
│       ├── core/       # Domain models (Job, Application, Applicant) — Pydantic
│       ├── dashboard/  # FastAPI app — thin app.py + api/ routers (see below)
│       │   ├── app.py        # builds FastAPI app, CORS, includes routers
│       │   ├── api/          # one APIRouter per domain (jobs, email, stats, …)
│       │   ├── dependencies.py  # admin auth
│       │   ├── state.py         # shared in-process state
│       │   ├── schemas.py       # pydantic request bodies
│       │   └── services/        # endpoint-agnostic logic (gamification)
│       ├── scrapers/   # Job-source scrapers (subclass BaseScraper)
│       ├── fillers/    # Per-ATS form fillers (subclass BaseFiller)
│       ├── classifiers/# Detects which ATS a job-apply page is (→ which filler)
│       ├── llm/        # Gemini client + prompts (answers open-ended questions)
│       ├── email/      # Cold-email subsystem (templates, send, schedule)
│       ├── notifier/   # ntfy push notifications
│       └── utils/      # config, paths, browser, logger
│           ├── models/       # SQLAlchemy ORM models (one Base)
│           ├── repositories/ # query methods grouped by domain (mixins)
│           └── database.py    # Database (engine+session) composes the mixins
├── frontend/           # Next.js 16 / React 19 dashboard UI
├── config/settings.yaml# Runtime configuration (search, scrapers, llm, etc.)
├── data/               # ALL runtime data (db, profile, resume, screenshots) — gitignored
├── logs/               # Logs (gitignored)
└── .env                # Secrets / cookies (gitignored)
```

## How to run

The app resolves all paths from the **repo root**, so it behaves the same no
matter which directory you launch from (see "Paths" below).

```bash
# Backend (dashboard API on :8080)
cd backend
python main.py dashboard          # or: --port 8080 --host 127.0.0.1

# Frontend (UI on :3000)
cd frontend
npm install
npm run dev

# Everything via Docker
docker-compose up
```

Useful CLI commands: `python main.py status | job-stats | jobs | scrape | apply | apply-url | llm-usage | init`.

---

## Conventions (please follow when adding code)

### 1. Paths — never hardcode `data/...` or `logs/...`
All filesystem locations come from **`backend/src/utils/paths.py`**. Use the
helpers (`paths.db_path()`, `paths.profile_path()`, `paths.data_dir()`, …) instead
of string literals like `Path("data/profile.json")`. This is the single source of
truth and the reason the app is cwd-independent. (Historically a cwd-relative path
caused a "two databases" bug — one in `backend/data/`, one at the root.)

### 2. Config & secrets
- Non-secret settings live in **`config/settings.yaml`** (loaded from the repo root).
- Secrets/cookies live in **`.env`** at the repo root (loaded via `paths.env_file()`).
- Access config through `get_settings()` (cached) — don't read env vars directly in feature code.

### 3. One database
`data/applications.db` (SQLite). Accessed via the `get_db()` singleton in
`src/utils/database.py`. There is no migration framework yet — schema is created
with `Base.metadata.create_all()` on startup. (Alembic is a planned follow-up.)

### 4. Logging, not print
Use `from src.utils.logger import logger`. The dashboard's live activity feed reads
from an in-memory log buffer, so `print()` won't show up there. (CLI commands in
`main.py` intentionally use `console.print` for user-facing terminal output.)

### 5. Adding a **scraper**
1. Create `src/scrapers/<source>.py`, subclass `BaseScraper`, set `SOURCE_NAME`, call `super().__init__()`.
2. Reuse `scraper_utils.parse_date_string()` for dates and the inherited rate limiter.
3. Register it in `src/scrapers/aggregator.py` (`_setup_scrapers` + the `scrape_source` map).
4. Add it to the list returned by `GET /api/scrapers/status` in `src/dashboard/app.py`.

### 6. Adding a **filler** (new ATS)
1. Create `src/fillers/<ats>_filler.py`, subclass `BaseFiller`, implement `can_handle()` + `fill()`.
2. Add the `ApplicationType` enum value in `src/core/job.py` and map it in `src/orchestrator.py`.
3. Add detection logic in `src/classifiers/detector.py`.

### 7. API endpoints
Each domain has its own router in `src/dashboard/api/` (e.g. `jobs.py`,
`email.py`, `stats.py`). To add an endpoint, add it to the relevant router and —
if it's a brand-new domain — create a router and `include_router` it in
`app.py`. Put request bodies in `schemas.py`, auth via `Depends(require_admin)`
from `dependencies.py`, shared progress state in `state.py`. The frontend calls
these through `frontend/lib/api.ts`; keep response shapes stable.

After changing endpoints, run the smoke check: start the server, then
`python scripts/smoke_api.py` — it probes the read endpoints and prints the
route table so you can confirm nothing regressed.

### 8. Database queries
`get_db()` returns a `Database` that composes per-domain repository mixins in
`src/utils/repositories/` (jobs, contacts, templates, cold_emails, applications).
To add a query, put the method on the matching mixin — it's available as
`db.<method>()` automatically. ORM models live in `src/utils/models/` (all share
the one `Base`); `database.py` re-exports them so `from src.utils.database import
JobModel` still works.

---

## What was intentionally removed (and why)

To keep only working code, these orphaned/non-functional pieces were deleted during
the foundation cleanup. They're recoverable from git history if revived later:

- **Scrapers** that produced no data: `google_jobs`, `glassdoor`, `levelsfyi`, `duckduckgo_search`, `yc_jobs`.
- **`ai_agent_filler`** — a conditional LLM-driven fallback that was never proven.
- **`src/resume/`** (LaTeX resume generator) — never wired to any endpoint; needed `pdflatex`.
- **`src/scheduler/`** — periodic scrape loop, never invoked by the app.
- **`notifier/discord.py`** — defined but never instantiated (only ntfy is used).
- Stray duplicates: a second `backend/venv`, a stale root `data/applications.db`, and one-off scripts `run_scrapers_now.py` / `test_jobright_date.py`.
- The fake `WeWorkRemotely` entry in `/api/scrapers/status` (no such scraper existed).

## Known gaps — "make working later"

- **Auto-apply has never completed a submission** (0 applied). It's gated by
  `application.review_mode: true`, and the browser form-fill path is unverified.
  The `auto_submit` flag exists in config but is currently not read.
- **Gemini SDK** uses the deprecated `google.generativeai` package — migrate to `google-genai`.
- **No automated tests / no DB migrations** yet.
