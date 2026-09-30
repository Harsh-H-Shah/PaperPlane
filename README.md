<div align="center">

<img src="docs/assets/banner.png" alt="PaperPlane — automated job applications" width="100%">

<br>

**Your job hunt, on autopilot.**<br>
PaperPlane finds new tech roles every day, fills the application forms for you, asks an LLM only when it has to,<br>and turns the grind into a game: XP, streaks and Valorant-style ranks.

<br>

[![Live demo](https://img.shields.io/badge/live%20demo-paperplane.harshsh.com-FF4655?style=for-the-badge&logo=googlechrome&logoColor=white)](https://paperplane.harshsh.com)
[![Deploy](https://github.com/Harsh-H-Shah/PaperPlane/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/Harsh-H-Shah/PaperPlane/actions/workflows/deploy.yml)
[![Stars](https://img.shields.io/github/stars/Harsh-H-Shah/PaperPlane?style=for-the-badge&color=00D9FF&logo=github)](https://github.com/Harsh-H-Shah/PaperPlane/stargazers)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?logo=playwright&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-3.5%20Flash--Lite-8E75B2?logo=googlegemini&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
[![License: MIT](https://img.shields.io/github/license/Harsh-H-Shah/PaperPlane?color=FFE500)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-00FFA3)](#-contributing)

[**Live demo**](https://paperplane.harshsh.com) · [**Quick start**](#-quick-start) · [**How it works**](#-how-it-works) · [**Run it for $0**](#-run-it-for-0) · [**Roadmap**](#%EF%B8%8F-roadmap)

<br>

<img src="docs/assets/hero.gif" alt="PaperPlane tour: boot screen, dashboard, job list, career stats and agent profile" width="92%">

</div>

---

## 🎯 Why PaperPlane?

Applying to entry-level tech jobs is a numbers game: the same name, email, links and "why this company?" answers, typed into a different form a hundred times. PaperPlane does the repetitive part and leaves you the judgment calls.

- 🛰️ **It finds the jobs.** Seven scrapers, including 65+ top-company boards, pull fresh software roles and filter out senior, stale and non-tech postings.
- 📝 **It fills the forms.** It recognizes the major applicant tracking systems (Greenhouse, Lever, Ashby, Workday and more) and fills each field from your profile.
- 🧠 **It thinks only when needed.** Simple fields are resolved from your profile with no API call; only open-ended questions go to Gemini (the free tier is enough).
- 🙋 **You stay in control.** Salary, visa, sponsorship and similar questions are always flagged for you, and `AUTO_SUBMIT` is off by default.
- 🎮 **It makes the grind fun.** Every application earns XP, keeps your streak alive and climbs you from Iron to Radiant.

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 🔭 Job discovery
- **Simplify** & **SpeedyApply** new-grad and internship lists
- **65+ company boards** via their public ATS APIs (one line of YAML per company)
- **Jobright**, **Built In**, **Greenhouse** job search
- **Public boards:** Remotive, RemoteOK, Jobicy, Himalayas, We Work Remotely and more
- Deduplication, dead-link checks and seniority/recency filters

</td>
<td width="50%" valign="top">

### ⚙️ Form filling
- ATS detection for **Workday, Greenhouse, Lever, Ashby, iCIMS, Taleo, SmartRecruiters, Jobvite, Oracle, ADP**
- Dedicated fillers for **Greenhouse, Lever, Ashby, Workday**, plus a universal filler and redirect handling
- Resume upload and profile-driven field mapping
- One-click apply from the dashboard, or `apply` from the CLI

</td>
</tr>
<tr>
<td valign="top">

### 🧠 LLM, used sparingly
- **Gemini 3.5 Flash-Lite** by default, which fits in the free tier
- Built-in rate limiting and daily usage tracking (`llm-usage`)
- Answer validation, plus an always-review list for sensitive questions

</td>
<td valign="top">

### 🕹️ Mission control dashboard
- Live activity feed, job targets and one-click **Recon** (scrape) / **Engage** (apply)
- XP, streaks, daily and weekly quests, and **Iron → Radiant** ranks
- Cold-email outreach: contacts, templates, scheduling and follow-ups
- Fully responsive, with a public read-only view and a token-protected admin mode

</td>
</tr>
</table>

## 📸 Take a look

<table>
<tr>
<td width="68%" align="center"><img src="docs/assets/missions.gif" alt="Searching and filtering the job list"><br><sub><b>Active Missions:</b> search, filter and apply across every source</sub></td>
<td width="32%" align="center"><img src="docs/assets/mobile.gif" alt="Mobile layout with slide-out navigation"><br><sub><b>Mobile:</b> the whole dashboard in your pocket</sub></td>
</tr>
</table>

<table>
<tr>
<td align="center"><img src="docs/assets/stats.png" alt="Career stats with rank progression"><br><sub><b>Career stats:</b> rank progression and loadout</sub></td>
<td align="center"><img src="docs/assets/profile.png" alt="Agent profile"><br><sub><b>Agent profile:</b> pick your Valorant agent</sub></td>
<td align="center"><img src="docs/assets/arsenal.png" alt="Arsenal of job sources"><br><sub><b>Arsenal:</b> every intelligence source, one click away</sub></td>
</tr>
</table>

## 🧭 How it works

```mermaid
flowchart TB
    Discover["🔭 Discover<br/>Simplify · SpeedyApply · 65+ company boards<br/>Jobright · Built In · public boards"]

    Discover --> F{{"🧹 Filter: dedupe · dead links · seniority · recency"}}
    F --> DB[("🗄️ SQLite")]
    DB --> O["🎯 Orchestrator"]
    O --> C{"🔍 Detect ATS"}
    C -->|Greenhouse · Lever · Ashby · Workday| DF["⚙️ Dedicated filler"]
    C -->|anything else| UF["🧩 Universal filler"]
    DF --> M["📋 Map fields from your profile"]
    UF --> M
    M -->|open-ended question| LLM["🧠 Gemini"]
    M -->|salary · visa · sponsorship| H["🙋 You review"]
    LLM --> R["✅ Applied  /  👀 Needs review"]
    H --> R
    R --> G["🎮 XP · streaks · rank"]
```

Every job moves through a simple lifecycle, and the dashboard shows each state with its own game-style label:

```mermaid
stateDiagram-v2
    direction LR
    [*] --> new: scraped
    new --> in_progress: Engage
    in_progress --> applied: submitted ✅
    in_progress --> needs_review: human input needed 👀
    in_progress --> failed: form error ❌
    needs_review --> applied: you finish it
    failed --> in_progress: retry
    new --> expired: posting closed
    new --> rejected: dismissed
    applied --> [*]
```

## 🚀 Quick start

**You'll need:** Python 3.11+, Node.js 20+, and a free [Gemini API key](https://aistudio.google.com/apikey).

```bash
git clone https://github.com/Harsh-H-Shah/PaperPlane.git
cd PaperPlane

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python main.py init          # creates .env and data/profile.json from the examples
```

Fill in `.env` (at least `GEMINI_API_KEY`, plus an `ADMIN_TOKEN` of your choice) and your details in `data/profile.json`. Then:

```bash
# Terminal 1: API on :8080
cd backend && source .venv/bin/activate && python main.py dashboard

# Terminal 2: dashboard on :3000
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000**, log in with your `ADMIN_TOKEN`, hit **Recon** to scrape, then **Engage** to start applying.

<details>
<summary><b>🐳 Prefer Docker?</b></summary>

```bash
docker compose up -d --build    # backend on :8080, frontend on :3000
```

Runtime data lives in `data/` and `logs/`, mounted into the container.
</details>

## 🕹️ CLI

Everything the dashboard does is also available from the terminal: `python main.py <command>`.

| Command | What it does |
| --- | --- |
| `init` | Create `.env` and `data/profile.json` from the examples |
| `status` | Show configuration and job statistics |
| `scrape` | Discover new jobs (`--source`, `--limit`) |
| `jobs` | List jobs, optionally filtered by status |
| `add-job` | Add a job manually |
| `apply` | Apply to pending jobs |
| `apply-url` | Apply to a single job URL |
| `dashboard` | Start the API server |
| `job-stats` | Breakdown of jobs by source and status |
| `llm-usage` / `test-llm` | Check Gemini usage, or send a test prompt |
| `h1b-sponsors` | Fetch H1B sponsor company data |
| `config` / `version` | Show the active config, or the version |

## 💸 Run it for $0

The live demo at **[paperplane.harshsh.com](https://paperplane.harshsh.com)** runs on this exact setup, with no servers to rent:

```mermaid
flowchart LR
    GH["🤖 GitHub Actions"] -->|on push to main| P["📄 GitHub Pages<br/>static frontend"]
    U(("👤 You")) -->|HTTPS| P
    U -->|HTTPS API| CF["☁️ Cloudflare"]
    CF <-->|outbound tunnel| T["🔌 cloudflared"]
    subgraph Home["🏠 Your computer (Docker)"]
        T --> B["⚡ FastAPI backend<br/>+ Playwright"]
        B --> D[("🗄️ SQLite")]
    end
    G["🧠 Gemini<br/>free tier"] <--> B
```

| Piece | Service | Cost |
| --- | --- | --- |
| Frontend | GitHub Pages (static export) | $0 |
| Backend | Your own computer, via Docker | $0 |
| HTTPS + public URL | Cloudflare Tunnel (no open ports) | $0 |
| LLM | Gemini API free tier | $0 |
| CI/CD | GitHub Actions | $0 |

Both containers restart on their own after a crash or reboot. Want it running 24/7 instead? [HOSTING.md](HOSTING.md) also covers a Google Cloud VM (about $3.65/month).

## 🧩 Chrome extension (in progress)

A standalone Manifest V3 extension in [`extension/`](extension/) brings the same field mapping and answer prompts to any page you're on, no backend needed. It adds answer learning, a review step for sensitive fields, and an optional local Ollama engine. Some of its source files still need to be committed before it builds ([#10](https://github.com/Harsh-H-Shah/PaperPlane/issues/10)); see [extension/README.md](extension/README.md).

## 🗺️ Roadmap

- [x] Seven job scrapers, including 65+ company boards
- [x] Dedicated fillers for Greenhouse, Lever, Ashby and Workday
- [x] Gamified dashboard with ranks, streaks and quests
- [x] Free hosting: GitHub Pages + Cloudflare Tunnel
- [ ] Fix the remaining apply-pipeline bugs ([#3](https://github.com/Harsh-H-Shah/PaperPlane/issues/3))
- [ ] Remember answered questions and reuse them across applications
- [ ] Scheduled daily scrape and apply runs
- [ ] Commit the extension's core modules ([#10](https://github.com/Harsh-H-Shah/PaperPlane/issues/10))
- [ ] Automated test suite for the backend

## 🤝 Contributing

Contributions are welcome, whether it's a new job source, an ATS filler, or a UI polish.

1. Fork the repo and create a branch.
2. Keep the backend lint clean: `cd backend && ruff check src/`.
3. Open a PR describing what changed and how you tested it.

**Easy first contribution:** add a company to [`config/company_boards.yaml`](config/company_boards.yaml), which is one line per company with no code changes. More background is in [DOCS.md](DOCS.md) and [docs/JOB_INGESTION_PLAN.md](docs/JOB_INGESTION_PLAN.md).

If PaperPlane saves you some typing, a ⭐ helps other job seekers find it.

<a href="https://star-history.com/#Harsh-H-Shah/PaperPlane&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=Harsh-H-Shah/PaperPlane&type=Date&theme=dark">
    <img alt="Star history chart" src="https://api.star-history.com/svg?repos=Harsh-H-Shah/PaperPlane&type=Date" width="600">
  </picture>
</a>

## 📜 License & disclaimer

[MIT License](LICENSE). Feel free to use and modify.

PaperPlane is a personal productivity tool. Review what it fills in before anything is submitted, and follow each job platform's terms of service.

<div align="center"><sub>Built with ☕ and too many job applications · <a href="https://paperplane.harshsh.com">paperplane.harshsh.com</a></sub></div>
