# PaperPlane ✈️

> An intelligent, automated job application system for tech positions

PaperPlane is a free, open-source tool that automates the job application process for software engineering and tech positions. It discovers job postings from multiple sources, categorizes application types, auto-fills forms using your personal information, and leverages LLMs for handling complex questions.

## ✨ Features

- **Multi-Source Job Discovery**: Aggregates jobs from Simplify, Jobright, BuiltIn, a curated list of top-company ATS boards (Greenhouse/Lever/Ashby/Workday/SmartRecruiters/Workable), SpeedyApply, and public remote boards (We Work Remotely, Himalayas, RemoteOK, Remotive, Jobicy, USAJOBS, and more)
- **Precision Filtering**: A shared software-role classifier casts a wide net across sources while excluding non-engineering roles, plus a seniority gate that drops senior/lead/staff/principal+ postings for junior/new-grad search
- **Smart Application Categorization**: Recognizes Workday, Ashby, ADP, Oracle, Greenhouse, Lever, and custom forms
- **Intelligent Form Filling**: Auto-fills applications using your profile data
- **Standalone Autofill Extension**: A Chrome (MV3) extension in [`extension/`](extension/) that fills any job application form from your profile independent of the backend, with LLM help for open-ended questions
- **LLM-Powered Responses**: Uses Gemini Pro (or other LLMs) for open-ended questions
- **Human-in-the-Loop**: Notifies you via Discord/ntfy when manual input is required
- **Resume Generation**: Creates tailored PDF resumes for specific job types
- **Gamified Dashboard**: Track your progress with XP, streaks, and rank-ups
- **Completely Free**: No paid services required

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              PaperPlane                                │
├──────────────────────────────┬──────────────────────────────────────────┤
│       Frontend (Next.js)     │         Backend (FastAPI + Python)       │
│                              │                                         │
│  • Dashboard UI              │  ┌──────────────┐     ┌──────────────┐  │
│  • Stats & Charts            │  │   Scrapers   │ ──▶ │   Filters    │  │
│  • Job Management            │  │  (Job Disc.) │     │ (Entry-level)│  │
│  • Gamification System       │  └──────────────┘     └──────────────┘  │
│                              │         │                    │           │
│                              │         ▼                    ▼           │
│                              │  ┌──────────────┐     ┌──────────────┐  │
│                              │  │   Database   │ ◀─▶ │ Orchestrator │  │
│                              │  │   (SQLite)   │     │  (Workflow)  │  │
│                              │  └──────────────┘     └──────────────┘  │
│                              │                              │          │
│                              │         ┌──────────────┐     │          │
│                              │         │   Fillers    │◀────┘          │
│                              │         │ (Form Auto)  │               │
│                              │         └──────┬───────┘               │
│                              │                │                        │
│                              │         ┌──────┴───────┐               │
│                              │         │  LLM Client  │               │
│                              │         │ (Gemini Pro) │               │
│                              │         └──────────────┘               │
└──────────────────────────────┴──────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Harsh-H-Shah/PaperPlane.git
cd PaperPlane

# --- Backend Setup ---
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# --- Frontend Setup ---
cd ../frontend
npm install

# --- Configure ---
cp .env.example .env
# Edit .env with your Gemini API key and notification webhook
cp data/profile.example.json data/profile.json
# Edit profile.json with your information

# --- Run ---
# Terminal 1: Backend API
cd backend && python main.py dashboard

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Browser extension (optional)

A standalone Chrome extension in [`extension/`](extension/) can fill forms without the backend running:

```bash
cd extension
npm install
npm run build   # outputs to dist/
```

Load `extension/dist` as an unpacked extension via `chrome://extensions`. See [extension/README.md](extension/README.md) for setup.

## 📋 CLI Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize configuration files |
| `status` | Show system status and statistics |
| `scrape` | Discover new jobs from all sources |
| `jobs` | List jobs with optional status filter |
| `apply` | Auto-apply to pending jobs |
| `apply-url` | Apply to a specific job URL |
| `dashboard` | Launch the API server |
| `scheduler` | Start automated scraping scheduler |
| `resume` | Generate a tailored PDF resume |
| `h1b-sponsors` | Fetch H1B sponsor company data |
| `llm-usage` | Show LLM API usage statistics |

## 📋 Requirements

- Python 3.10+
- Node.js 18+
- Chrome/Chromium browser (for Playwright)
- Gemini Pro API key (free tier available)
- Optional: Discord webhook or ntfy topic for notifications

## 🔧 Configuration

All configuration is managed via environment variables (`.env` file):

- `GEMINI_API_KEY`: Your Gemini API key
- `DISCORD_WEBHOOK_URL`: Discord webhook for notifications
- `NTFY_TOPIC`: ntfy.sh topic for mobile notifications
- `EMAIL_USER` / `EMAIL_PASSWORD`: For email verification code extraction
- `USAJOBS_API_KEY` / `USAJOBS_EMAIL`: Optional, unlocks the US federal jobs source (free key at [developer.usajobs.gov](https://developer.usajobs.gov/apirequest/))

Top-company ATS boards are curated in [`config/company_boards.yaml`](config/company_boards.yaml) — add a company with one line. See [docs/JOB_INGESTION_PLAN.md](docs/JOB_INGESTION_PLAN.md) for the job-sourcing roadmap.

See [DOCS.md](DOCS.md) for full documentation and [HOSTING.md](HOSTING.md) for deployment guide.

## 📜 License

MIT License - feel free to use and modify!

## ⚠️ Disclaimer

This tool is for educational purposes. Always review applications before submission and comply with each platform's terms of service.
