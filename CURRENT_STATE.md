# PaperPlane — Current State Audit

> Snapshot taken before the refactor (branch `main`). Purpose: a plain-language map of **what works today**, **what is wired but unproven**, and **what exists but is dead/orphaned**, so we keep only the working parts and know what to fix later.

---

## TL;DR

- **Backend boots and serves all 16 read API endpoints (HTTP 200).** ✅
- **Frontend builds cleanly; all 6 pages compile and type-check.** ✅
- **There is real data**: 532 jobs (6 sources), 1 contact, 1 email, 7 email templates.
- **Core gap**: scraping has clearly worked in the past, but **0 applications have ever succeeded** — the auto-apply pipeline is wired end-to-end but has never produced an `applied` job (it's gated to "needs review", and the browser-fill path is unproven).
- **Several subsystems are dead code**: resume generator, scheduler, Discord notifier, ~4 scrapers, an `auto_submit` flag that's never read, and a `/api/scrapers/status` endpoint that returns a hardcoded fake list.
- **Biggest footgun**: configuration and file paths are **resolved relative to the current working directory**, so the app behaves differently depending on where you launch it.

---

## 1. Environment & setup gotchas (fix these first — they cause confusion)

| Issue | Detail | Impact |
|---|---|---|
| **Two virtualenvs** | `backend/.venv` (used, Python 3.12) and `backend/venv` (stray) | Confusing; delete `venv`. |
| **Two databases** | `data/applications.db` (61 KB, stale, Mar 29) and `backend/data/applications.db` (499 KB, active, Jun 10) | The app writes to whichever the cwd resolves to. The *real* data is in `backend/data/`. |
| **cwd-relative config** | `config/settings.yaml` is found by walking up from cwd. README says run from `backend/`, but `backend/config/` is **empty** → `settings.yaml` is **never loaded** in the documented workflow; defaults are used instead. | The root `config/settings.yaml` is effectively dead when run as documented. |
| **cwd-relative paths** | `database.path` (`"data/applications.db"`), `get_profile_path()` (`data/profile.json`), `.env` (`env_file=".env"`) all resolve against cwd, not the repo root. | `backend/data/` has **no** `profile.json` (it lives in root `data/`); secrets/profile loading silently depends on launch dir. |
| **`.env` location** | Single `.env` at repo root (8.6 KB, most keys set: Gemini, SMTP, Discord, ntfy, LinkedIn/BuiltIn/Jobright cookies). No `backend/.env`. | If launched from `backend/`, pydantic's `env_file=".env"` may not find it — verify before relying on env-based secrets. |

**Refactor priority:** centralize all path resolution to the repo root (one helper), pick one DB, one venv, one config-load strategy independent of cwd.

---

## 2. What WORKS today (verified by running it)

### Backend API — all return HTTP 200
`/api/auth/status`, `/api/stats`, `/api/gamification`, `/api/quests`, `/api/combat-history`, `/api/jobs` (+`?status=`), `/api/contacts`, `/api/emails`, `/api/templates`, `/api/email-stats`, `/api/profile`, `/api/scrapers/status`*, `/api/scrape/progress`, `/api/activity`, `/api/llm-usage`.

> *`/api/scrapers/status` returns 200 but the data is fake — see §4.

### Real data in the DB
- **532 jobs**, all `pending`, from: `jobright` (193), `simplify` (95), `greenhouse_jobs` (80), `cvrve` (69), `builtin` (53), `careerjet` (42).
- **1 contact, 1 email, 7 templates.**
- **Gamification**: Level 3 "Iron 1", 0 XP, 0 streak (because 0 jobs are `applied`).

### Frontend
- `npm run build` succeeds (Next.js 16 / Turbopack). All pages prerender: `/`, `/missions`, `/emails`, `/stats`, `/profile`, `/arsenal`.

---

## 3. Wired but UNPROVEN / conditional (works on paper, not confirmed end-to-end)

| Subsystem | State | Condition / blocker |
|---|---|---|
| **Scrapers (6 productive)** | simplify, cvrve, jobright, builtin, careerjet, greenhouse_jobs have produced data | builtin needs cookies (env); others are public. Not re-run in this audit. |
| **Fillers (6 wired)** | greenhouse, lever, workday, ashby, redirect, universal (fallback) — all mapped to `ApplicationType` and reachable by the orchestrator | Never confirmed to complete a real form fill. |
| **Apply pipeline** | Full path exists: `/api/apply/{job_id}` → orchestrator → browser → filler | **0 successes ever.** Gated by `review_mode: true` → every application stops at `NEEDS_REVIEW`, never `APPLIED`. Browser-fill correctness unverified; captcha unhandled. |
| **AI agent filler** | `ai_agent_filler.py` used only as a conditional fallback | Requires Gemini key + successful import; otherwise `universal_filler` takes over. |
| **Cold email send** | `email_sender.py` (SMTP) wired into `/api/emails/*/send` | Only active if `SMTP_USER`/`SMTP_PASSWORD` set; otherwise returns False. Not test-sent. |
| **Notifier (ntfy)** | wired into orchestrator events | Requires `NTFY_TOPIC`. |

---

## 4. EXISTS but DEAD / orphaned / wrong (candidates to remove or quarantine)

| Thing | Where | Problem |
|---|---|---|
| **`/api/scrapers/status` is a stub** | `src/dashboard/app.py` ~474–506 | Returns a **hardcoded** list of 4 (Simplify, CVRVE, Jobright, **WeWorkRemotely**). "WeWorkRemotely" has **no scraper class**. Ignores the real aggregator/config. |
| **Orphaned scrapers** | `google_jobs`, `glassdoor`, `levelsfyi`, `duckduckgo_search` | Registered in aggregator but produced **0 data** (likely blocked/broken). `yc_jobs.py` isn't even registered. |
| **Resume generator** | `src/resume/generator.py` | Never called by any endpoint; needs a LaTeX toolchain (`pdflatex`). |
| **Scheduler** | `src/scheduler/scheduler.py` | `JobScheduler` defined but never instantiated/invoked anywhere. |
| **Discord notifier** | `src/notifier/discord.py` | Defined but never instantiated (only ntfy is used). |
| **`auto_submit` flag** | `src/utils/config.py` (alias `AUTO_SUBMIT`) | Defined but **read nowhere** in the apply flow. |
| **Ashby duplicate handler** | `ashby_filler.py` `_handle_input` defined twice (~line 406 & 739) | Second silently shadows the first (latent bug). |
| **Orphaned scripts** | `backend/run_scrapers_now.py`, `backend/test_jobright_date.py` | Ad-hoc one-offs at backend root, not wired in / not real tests. |
| **Stray dirs** | `backend/venv`, root `data/applications.db` (stale) | Leftover duplicates. |

---

## 5. Why "0 applied" — the central thing to make work later

1. `review_mode: true` (default in `src/utils/config.py`, and in the unused root `settings.yaml`) → every successful fill is marked `NEEDS_REVIEW`, never auto-submitted.
2. The `auto_submit` config flag that *should* control this is **never read**.
3. The browser form-fill path (fillers) has never been confirmed to actually complete a submission; captchas/cookie walls are unhandled.

**This is the headline "needs to be made working" item** — but per the plan it's a *later* step. The refactor first makes the working parts clean and understandable.

---

## 6. Recommendation for the "keep only what works" refactor

**Keep & clean (core that demonstrably works):**
- Backend read API + the 6 productive scrapers + the 6 wired fillers + orchestrator + DB layer.
- Cold email + ntfy (conditional but wired) — keep, mark as "needs config".
- Entire frontend (all 6 pages build and are wired to the API).

**Quarantine (move to a `legacy/` or `experimental/` area, don't delete — we'll revisit):**
- Orphaned scrapers (google_jobs, glassdoor, levelsfyi, duckduckgo, yc), resume generator, scheduler, Discord notifier, ai_agent_filler.

**Fix as part of cleanup (cheap, high clarity):**
- Make `/api/scrapers/status` derive from the real config/aggregator (remove the fake list).
- Centralize path/config resolution to repo root (kill cwd-dependence).
- Remove the stray `venv`, the stale root DB, the duplicate Ashby handler, and the orphaned root scripts.

**Defer (explicitly "make working later"):**
- The auto-apply submission path (review_mode/auto_submit logic, filler correctness, captcha handling).

---

*Verification method: booted `python main.py dashboard` and probed every read endpoint (all 200); inspected DB row counts via the API; ran `npm run build` (success); static-traced scraper/filler wiring via the aggregator, classifier, and orchestrator. No applications were submitted and no scrapers were re-run live.*
