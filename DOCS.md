# PaperPlane Documentation ✈️

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Job Discovery Pipeline](#job-discovery-pipeline)
4. [Application Filling System](#application-filling-system)
5. [Frontend Dashboard](#frontend-dashboard)
6. [Backend API Reference](#backend-api-reference)
7. [Database Schema](#database-schema)
8. [Configuration Reference](#configuration-reference)
9. [Development Guide](#development-guide)
10. [Troubleshooting](#troubleshooting)

---

## Overview

PaperPlane automates the job application process for software engineers. It:

1. **Discovers** jobs from 15+ sources (LinkedIn, Jobright, Greenhouse, Glassdoor, etc.)
2. **Classifies** application types (Greenhouse, Lever, Workday, Ashby, etc.)
3. **Auto-fills** forms using your profile data + LLM for complex questions
4. **Notifies** you via Discord/ntfy when manual input is needed
5. **Tracks** everything in a gamified dashboard

### Design Principles

- **Plugin Architecture**: Each scraper, filler, and classifier extends a base class — add new platforms without touching core logic
- **Async-First**: All I/O operations use `asyncio` for parallel processing
- **Human-in-the-Loop**: CAPTCHAs, complex forms, and unfamiliar questions trigger notifications instead of guessing
- **Incremental Processing**: Seen URLs are tracked to avoid reprocessing

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│ Frontend (Next.js)                                                │
│   paperplane.harsh.software                                       │
│   ├── Dashboard (stats, charts, gamification)                     │
│   ├── Job Management (view, filter, apply, delete)                │
│   ├── Email Campaigns                                             │
│   └── Profile & Settings                                          │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ REST API (JSON)
┌──────────────────────────▼─────────────────────────────────────────┐
│ Backend (FastAPI + Python)                                         │
│   api.paperplane.harsh.software:8080                               │
│                                                                    │
│   ┌─── Scrapers ───┐  ┌── Classifiers ──┐  ┌──── Fillers ────┐   │
│   │ Jobright       │  │ ATS Detector    │  │ Greenhouse      │   │
│   │ Simplify       │  │ Link Validator  │  │ Lever           │   │
│   │ CVRVE          │  │ Job Filter      │  │ Ashby           │   │
│   │ Greenhouse Jobs│  └─────────────────┘  │ Workday         │   │
│   │ Glassdoor      │                       │ AI Agent Filler │   │
│   │ Levels.fyi     │  ┌── Orchestrator ──┐ │ Universal       │   │
│   │ Careerjet      │  │ Workflow engine  │ │ Redirect        │   │
│   │ Google Jobs    │  │ that coordinates │ └─────────────────┘   │
│   │ YC Jobs        │  │ scrape → fill    │                       │
│   │ WeWorkRemotely │  └─────────────────┘  ┌── LLM Client ────┐ │
│   └────────────────┘                       │ Gemini Pro       │  │
│                        ┌── Notifiers ────┐ │ Answer Validator │  │
│   ┌── Database ──────┐ │ Discord         │ └─────────────────┘  │
│   │ SQLite           │ │ ntfy            │                       │
│   │ (applications.db)│ │ Telegram        │  ┌── Cold Email ───┐ │
│   └──────────────────┘ └─────────────────┘  │ Apollo scraper  │ │
│                                             │ SMTP sender     │ │
│                                             └─────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

---

## Job Discovery Pipeline

### Supported Scrapers

| Scraper | Source | Auth Required | Method |
|---------|--------|---------------|--------|
| Jobright | GitHub repo | No | Parse markdown table |
| Simplify | GitHub repo | No | Parse JSON feed |
| CVRVE | GitHub repo | No | Parse JSON feed |
| Greenhouse Jobs | Greenhouse API | No | REST API |
| Glassdoor | Glassdoor.com | Cookies optional | HTML scraping |
| Levels.fyi | Levels.fyi | No | HTML scraping |
| Careerjet | Careerjet.com | No | HTML scraping |
| Google Jobs | Google | No | SerpAPI alternative |
| YC Jobs | Y Combinator | No | HTML scraping |
| WeWorkRemotely | weworkremotely.com | No | HTML scraping |

### Pipeline Flow

```
Scrapers → Job Filter → Link Validator → ATS Detector → Database
```

1. **Scrapers** fetch raw listings from each source
2. **Job Filter** removes senior/lead roles, keeps entry-level positions
3. **Link Validator** checks for dead links, phishing, suspicious domains
4. **ATS Detector** identifies the application platform (Greenhouse, Lever, etc.)
5. Results are bulk-inserted into SQLite with deduplication

### Adding a New Scraper

Create a file in `backend/src/scrapers/` extending `BaseScraper`:

```python
from src.scrapers.base_scraper import BaseScraper

class MyScraper(BaseScraper):
    SOURCE_NAME = "my_source"

    async def scrape(self, limit: int = 100) -> list[Job]:
        # Fetch and return Job objects
        ...
```

Register it in `backend/src/scrapers/aggregator.py`.

---

## Application Filling System

### Supported ATS Platforms

| Platform | Filler | Status |
|----------|--------|--------|
| Greenhouse | `greenhouse_filler.py` | ✅ Full |
| Lever | `lever_filler.py` | ✅ Full |
| Ashby | `ashby_filler.py` | ✅ Full |
| Workday | `workday_filler.py` | 🔨 Basic |
| AI Agent | `ai_agent_filler.py` | ✅ Full |
| Universal | `universal_filler.py` | ✅ Full |
| Redirect | `redirect_filler.py` | ✅ Full |

### How Filling Works

1. **Orchestrator** picks a pending job and determines its `ApplicationType`
2. **BaseFiller** launches a Playwright browser, navigates to the application
3. **Platform-specific filler** fills fields using your profile data
4. **Field Mapper** maps profile fields → form fields (name, email, phone, etc.)
5. **LLM Client** handles free-text questions (cover letter prompts, "Why this role?", etc.)
6. **Answer Validator** checks LLM responses before submission
7. If stuck → sends notification via Discord/ntfy

### Adding a New Filler

Extend `BaseFiller`:

```python
from src.fillers.base_filler import BaseFiller

class MyFiller(BaseFiller):
    async def fill(self, page, job, applicant):
        # Use Playwright page to fill the form
        ...
```

---

## Frontend Dashboard

The dashboard is a **Next.js** app with a gamified UI. Key components:

| Component | File | Purpose |
|-----------|------|---------|
| Dashboard | `app/page.tsx` | Main page — stats, history, actions |
| Sidebar | `components/Sidebar.tsx` | Navigation + agent selector |
| StatsCards | `components/StatsCards.tsx` | Job count summaries |
| CombatHistory | `components/CombatHistoryEnhanced.tsx` | Recent application log |
| QuickActions | `components/QuickActions.tsx` | Scrape/Apply buttons |
| ActivityFeed | `components/ActivityFeed.tsx` | Live log stream |
| JobDetails | `components/JobDetails.tsx` | Job detail modal |

### API Client

All API calls go through `frontend/lib/api.ts`. The base URL is configured via:

```
NEXT_PUBLIC_API_URL=http://localhost:8080   # development
NEXT_PUBLIC_API_URL=https://api.paperplane.harsh.software  # production
```

---

## Backend API Reference

Base URL: `http://localhost:8080` (dev) / `https://api.paperplane.harsh.software` (prod)

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/stats` | Job statistics with weekly activity |
| `GET` | `/api/jobs` | List jobs (filters: status, source, type, search) |
| `POST` | `/api/jobs` | Create a manual job entry |
| `GET` | `/api/jobs/{id}` | Get single job details |
| `PATCH` | `/api/jobs/{id}` | Update job status/notes |
| `DELETE` | `/api/jobs/{id}` | Soft-delete (mark as rejected) |
| `POST` | `/api/scrape` | Trigger scraping (background task) |
| `GET` | `/api/scrape/progress` | Poll scrape progress |
| `POST` | `/api/apply/{id}` | Trigger application for a job |
| `POST` | `/api/run` | Bulk auto-apply to pending jobs |

### Gamification Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/gamification` | XP, rank, streak data |
| `GET` | `/api/profile` | User profile data |
| `PATCH` | `/api/profile` | Update preferences |
| `GET` | `/api/quests` | Daily/weekly quests |
| `GET` | `/api/combat-history` | Recent apps in game format |

### Utility Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/activity` | Recent log entries |
| `GET` | `/api/llm-usage` | Gemini API usage stats |
| `GET` | `/api/scrapers/status` | Scraper config status |

---

## Database Schema

SQLite database at `data/applications.db`. Key tables:

### `jobs`
| Column | Type | Description |
|--------|------|-------------|
| id | STRING (PK) | UUID |
| title | STRING | Job title |
| company | STRING | Company name |
| location | STRING | Job location |
| url | STRING | Job posting URL |
| apply_url | STRING | Direct application URL |
| status | STRING | `new`, `queued`, `in_progress`, `applied`, `failed`, `needs_review`, `skipped`, `expired`, `rejected` |
| source | STRING | Scraper source (e.g., `jobright`, `simplify`) |
| application_type | STRING | ATS type (e.g., `greenhouse`, `lever`) |
| discovered_at | DATETIME | When discovered |
| applied_at | DATETIME | When applied |
| posted_date | DATETIME | Job posting date |

### `applications`
Tracks detailed application state (screenshots, errors, retry counts).

### `contacts`, `email_templates`, `cold_emails`
Cold email outreach tracking.

### `user_preferences`
Key-value store for UI preferences (e.g., Valorant agent selection).

---

## Configuration Reference

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DISCORD_WEBHOOK_URL` | No | Discord notification webhook |
| `NTFY_TOPIC` | No | ntfy.sh topic for mobile notifications |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token |
| `TELEGRAM_CHAT_ID` | No | Telegram chat ID |
| `HEADLESS` | No | `true`/`false` — show browser (default: `true`) |
| `LINKEDIN_LI_AT` | No | LinkedIn session cookie |
| `GLASSDOOR_COOKIES` | No | Glassdoor session cookies |
| `APOLLO_API_KEY` | No | Apollo.io API key for contact scraping |
| `MAX_APPLICATIONS_PER_RUN` | No | Max applications per run (default: 10) |
| `AUTO_SUBMIT` | No | Auto-submit applications (default: `false`) |

### Frontend Variables (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |

### Profile (`data/profile.json`)

Contains your personal information used for auto-filling:
- Name, email, phone, address
- Work experience, education
- Skills, certifications
- Resume variants

---

## Development Guide

### Prerequisites

- Python 3.10+
- Node.js 18+
- Chrome/Chromium (Playwright installs this)

### Running Locally

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python main.py dashboard --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Project Structure

```
PaperPlane/
├── backend/
│   ├── main.py              # CLI entry point
│   ├── requirements.txt
│   └── src/
│       ├── core/            # Job, Application, Applicant models
│       ├── scrapers/        # Job discovery (15+ sources)
│       ├── classifiers/     # ATS type detection
│       ├── fillers/         # Form auto-fill (7 platforms)
│       ├── llm/             # Gemini client + answer validation
│       ├── notifier/        # Discord, ntfy, Telegram
│       ├── dashboard/       # FastAPI app + legacy HTML dashboard
│       ├── email/           # Cold email system
│       ├── resume/          # PDF resume generation
│       ├── scheduler/       # Automated scraping scheduler
│       └── utils/           # Database, config, logging
├── frontend/
│   ├── app/                 # Next.js pages
│   ├── components/          # React components
│   └── lib/                 # API client
├── data/
│   ├── profile.json         # Your profile
│   └── applications.db      # SQLite database
└── .env                     # Configuration
```

---

## Troubleshooting

### Common Issues

**Backend won't start**
```
ModuleNotFoundError: No module named 'src'
```
→ Run from the `backend/` directory, not the project root.

**Playwright browser errors**
```
playwright._impl._errors.Error: Executable doesn't exist
```
→ Run `playwright install chromium` in your venv.

**Frontend can't connect to backend**
```
Failed to connect to backend. Make sure the API is running on port 8080.
```
→ Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches your backend port.

**LLM rate limits**
→ Gemini free tier has 60 RPM. Use `llm-usage` command to check. Consider adding delays in `.env` via `APPLICATION_DELAY_MIN`.

**Database locked errors**
→ Only one process should write to SQLite at a time. Stop any running scheduler before using CLI commands.
