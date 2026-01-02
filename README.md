# AutoApplier 🚀

> An intelligent, automated job application system for tech positions

AutoApplier is a free, open-source tool that automates the job application process for software engineering and tech positions. It discovers job postings from multiple sources, categorizes application types, auto-fills forms using your personal information, and leverages LLMs for handling complex questions.

## ✨ Features

- **Multi-Source Job Discovery**: Aggregates jobs from LinkedIn, Jobright, Simplify, CVRVE, and company career pages
- **Smart Application Categorization**: Recognizes Workday, Ashby, ADP, Oracle, Greenhouse, Lever, and custom forms
- **Intelligent Form Filling**: Auto-fills applications using your profile data
- **LLM-Powered Responses**: Uses Gemini Pro (or other LLMs) for open-ended questions
- **Human-in-the-Loop**: Notifies you via webhook when manual input is required
- **Completely Free**: No paid services required

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AutoApplier                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Job       │  │  Application│  │   Form      │              │
│  │  Scraper    │──│  Classifier │──│   Filler    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Data      │  │    LLM      │  │  Webhook    │              │
│  │   Store     │  │  Integration│  │  Notifier   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
AutoApplier/
├── src/
│   ├── scrapers/           # Job discovery from various sources
│   │   ├── linkedin.py
│   │   ├── jobright.py
│   │   ├── simplify.py
│   │   ├── cvrve.py
│   │   └── career_sites.py
│   ├── classifiers/        # Application type detection
│   │   ├── workday.py
│   │   ├── ashby.py
│   │   ├── greenhouse.py
│   │   └── detector.py
│   ├── fillers/            # Form automation
│   │   ├── base_filler.py
│   │   ├── workday_filler.py
│   │   ├── ashby_filler.py
│   │   └── generic_filler.py
│   ├── llm/                # LLM integration
│   │   ├── gemini.py
│   │   └── prompts.py
│   ├── notifier/           # Webhook notifications
│   │   └── webhook.py
│   ├── core/               # Core functionality
│   │   ├── applicant.py
│   │   ├── job.py
│   │   └── application.py
│   └── utils/              # Utilities
│       ├── browser.py
│       └── config.py
├── data/
│   ├── profile.json        # Your personal information
│   ├── resume.json         # Parsed resume data
│   └── applications.db     # SQLite database for tracking
├── config/
│   └── settings.yaml       # Configuration file
├── tests/                  # Unit and integration tests
├── requirements.txt
├── .env.example
└── main.py
```

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
# Add your Gemini API key and webhook URL

# Run
python main.py
```

## 📋 Requirements

- Python 3.10+
- Chrome/Chromium browser (for Selenium/Playwright)
- Gemini Pro API key (free tier available)
- Optional: Discord/Telegram webhook for notifications

## 🔧 Configuration

See `config/settings.yaml` for all configuration options.

## 📜 License

MIT License - feel free to use and modify!

## ⚠️ Disclaimer

This tool is for educational purposes. Always review applications before submission and comply with each platform's terms of service.
