# AutoApplier 🚀

> An intelligent, automated job application system for tech positions

AutoApplier is a free, open-source tool that automates the job application process for software engineering and tech positions. It discovers job postings from multiple sources, categorizes application types, auto-fills forms using your personal information, and leverages LLMs for handling complex questions.

## ✨ Features

- **Multi-Source Job Discovery**: Aggregates jobs from LinkedIn, Jobright, Simplify, CVRVE, BuiltIn, Dice, Y Combinator, and more
- **Smart Application Categorization**: Recognizes Workday, Ashby, ADP, Oracle, Greenhouse, Lever, and custom forms
- **Intelligent Form Filling**: Auto-fills applications using your profile data
- **LLM-Powered Responses**: Uses Gemini Pro (or other LLMs) for open-ended questions
- **Human-in-the-Loop**: Notifies you via Discord/ntfy when manual input is required
- **Resume Generation**: Creates tailored PDF resumes for specific job types
- **Completely Free**: No paid services required

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            AutoApplier                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐             │
│  │   Scrapers   │ ──▶ │   Filters    │ ──▶ │  Classifiers │             │
│  │  (Job Disc.) │     │ (Entry-level)│     │  (ATS Type)  │             │
│  └──────────────┘     └──────────────┘     └──────────────┘             │
│         │                                          │                     │
│         ▼                                          ▼                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐             │
│  │   Database   │ ◀─▶ │ Orchestrator │ ──▶ │   Fillers    │             │
│  │   (SQLite)   │     │  (Workflow)  │     │ (Form Auto)  │             │
│  └──────────────┘     └──────────────┘     └──────────────┘             │
│                              │                     │                     │
│                              ▼                     ▼                     │
│                       ┌──────────────┐     ┌──────────────┐             │
│                       │   Notifier   │     │  LLM Client  │             │
│                       │(Discord/ntfy)│     │ (Gemini Pro) │             │
│                       └──────────────┘     └──────────────┘             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🔄 How It Works

1. **Job Discovery**: Scrapers aggregate job listings from multiple sources (LinkedIn, CVRVE, Simplify, etc.)
2. **Filtering**: The JobFilter removes senior/lead roles and keeps entry-level/junior positions
3. **Link Validation**: Dead links, phishing attempts, and suspicious domains are filtered out
4. **Classification**: The detector identifies the ATS type (Greenhouse, Lever, Workday, etc.)
5. **Form Filling**: Platform-specific fillers auto-populate application forms using your profile
6. **LLM Assistance**: Open-ended questions are answered using Gemini Pro with your context
7. **Notifications**: When human input is needed, you're notified via Discord or ntfy

## 🧠 Technical Principles

### Modular Plugin Architecture
Each component (scrapers, fillers, classifiers) follows a base class pattern, making it easy to add new job sources or ATS platforms without modifying core logic.

### Async-First Design
All I/O-bound operations (web scraping, API calls, form interactions) use Python's `asyncio` for efficient parallel processing. The `JobAggregator` scrapes multiple sources concurrently.

### Human-in-the-Loop (HITL)
The system prioritizes automation but recognizes its limits. When encountering CAPTCHAs, complex questions, or unfamiliar forms, it pauses and notifies you rather than guessing.

### Incremental Processing
The `IncrementalScraper` tracks seen URLs to avoid reprocessing. Jobs are stored in SQLite with status tracking, ensuring no duplicate applications.

### LLM-Powered Intelligence
Context-aware prompts feed your profile, resume, and job description to Gemini Pro. The `AnswerValidator` ensures responses are appropriate before submission.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/AutoApplier.git
cd AutoApplier

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your profile
cp data/profile.example.json data/profile.json
# Edit profile.json with your information

# Configure settings
cp .env.example .env
# Add your Gemini API key and notification webhook

# Run the dashboard
python main.py dashboard

# Or scrape jobs manually
python main.py scrape --limit 50

# Apply to jobs
python main.py apply --limit 5
```

## 📋 CLI Commands

| Command | Description |
|---------|-------------|
| `status` | Show system status and statistics |
| `scrape` | Discover new jobs from all sources |
| `jobs` | List jobs with optional status filter |
| `apply` | Auto-apply to pending jobs |
| `apply-url` | Apply to a specific job URL |
| `dashboard` | Launch the web dashboard |
| `scheduler` | Start automated scraping scheduler |
| `resume` | Generate a tailored PDF resume |
| `h1b-sponsors` | Fetch H1B sponsor company data |
| `llm-usage` | Show LLM API usage statistics |

## 📋 Requirements

- Python 3.10+
- Chrome/Chromium browser (for Playwright)
- Gemini Pro API key (free tier available)
- Optional: Discord webhook or ntfy topic for notifications

## 🔧 Configuration

All configuration is managed via environment variables (`.env` file):

- `GEMINI_API_KEY`: Your Gemini API key
- `DISCORD_WEBHOOK_URL`: Discord webhook for notifications
- `NTFY_TOPIC`: ntfy.sh topic for mobile notifications
- `EMAIL_USER` / `EMAIL_PASSWORD`: For email verification code extraction

## 📜 License

MIT License - feel free to use and modify!

## ⚠️ Disclaimer

This tool is for educational purposes. Always review applications before submission and comply with each platform's terms of service.
