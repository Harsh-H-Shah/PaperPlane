# Job Ingestion & Real-Time Sourcing Plan

Status: living document. Phase 1 (top-company board list + fetcher) is being built now;
later phases are the roadmap.

## 1. Goals

1. **Maximize coverage** of fresh postings across many sources.
2. **Near-real-time detection** of new roles at top companies (Amazon, Microsoft, etc. post
   throughout the day and fill quickly) so we can auto-apply within minutes.
3. A **maintainable, growing list** of top-company boards — adding a company is a one-line change.
4. Feed clean, deduplicated `Job` records into the existing pipeline for auto-apply.

## 2. Source tiers

We organize sources into tiers by value and polling cadence.

| Tier | Sources | Why | Cadence (target) |
|------|---------|-----|------------------|
| **A — Top-company boards** | Curated list in `config/company_boards.yaml` (Greenhouse/Lever/Ashby/SmartRecruiters tokens + custom big-tech APIs) | Highest-value roles, fill fast, deterministic apply flow per ATS | 2–5 min |
| **B — ATS platform sweeps** | Broad Greenhouse/Lever/Ashby board lists (beyond the curated top companies) | Volume across thousands of companies | 15–30 min |
| **C — Aggregator APIs** | RemoteOK, Remotive, Arbeitnow, The Muse, Adzuna*, USAJobs*, Jobicy, Himalayas | Wide net, free, no captcha (`*` = needs free API key) | hourly |
| **D — Curated feeds** | Simplify (New-Grad + Summer2026 JSON), SpeedyApply (2027 college markdown), Jobright, BuiltIn, GreenhouseJobs | New-grad / intern focused | hourly–daily |

### Public boards — BUILT (`PublicBoardsScraper`)

`public_boards.py` fetches all of these no-auth sources concurrently (one adapter each) and runs them
through the software + seniority + recency gates. Note: the remote aggregators skew senior, so junior
yield per source is modest — We Work Remotely (RSS) and Himalayas (paginated) contribute the most.

| Board | Endpoint | Status |
|-------|----------|--------|
| **We Work Remotely** | 4 programming-category RSS feeds | ✅ live (best junior yield) |
| **Himalayas** | `himalayas.app/jobs/api` (offset-paginated 8×20) | ✅ live |
| **Jobicy** | `jobicy.com/api/v2/remote-jobs?tag=engineering` | ✅ live |
| **RemoteOK** | `remoteok.com/api` | ✅ live |
| **Remotive** | `remotive.com/api/remote-jobs?category=software-dev` | ✅ live |
| **4 Day Week** | `4dayweek.io/api/jobs` (paginated) | ✅ live |
| **Working Nomads** | `workingnomads.com/api/exposed_jobs/` | ✅ live |
| **USAJOBS** | `data.usajobs.gov/api/search` | ⚙️ built, inactive until `USAJOBS_API_KEY`+`USAJOBS_EMAIL` set (free key) |

Not adopted: EU-only (Arbeitnow, Landing.jobs, DevITjobs); client-rendered / no feed
(**entryleveljobs.me**, entrylevel.careers, usdevjobs.com); bot-walled (foundrole, startup.jobs).

### Seniority gate

The user is a junior / new grad, so `job_filter.is_senior_role()` drops senior/lead/staff/principal/
distinguished/fellow/manager/director/VP/architect, roman numerals III+, L4+, and 5+ years roles.
"II" and "L3" (entry/mid) are kept. Enforced in `should_include_job` alongside the software gate.

### Software-only gate

Every scraper runs each title through `job_filter.is_software_role()` before keeping it, and
`BaseScraper.should_include_job()` enforces the same gate as a hard backstop — so only software
engineering roles are ingested regardless of source. It has broad recall (SWE, backend/frontend,
mobile/iOS/Android, DevOps/SRE, ML/AI/data engineer, security, embedded, QA/SDET, etc.) and excludes
non-software families (sales, marketing, recruiting, PM, analysts, hardware/ASIC/EE, designers…).
On the Simplify feed this widened coverage ~2.4× vs the old 5-keyword substring match.

### Sources that need a browser + login (deferred)

- **Wellfound** (AngelList): Cloudflare + captcha wall on all endpoints — same wall that killed
  Careerjet. Needs the project's Playwright browser with stealth, not an HTTP scraper.
- **Work at a Startup** (YC): jobs live behind an Algolia index whose public key is locked
  (`tagFilters=[["none"]]`) — it returns nothing without a logged-in session. Needs an authenticated
  session/cookie. Note: many YC startups (OpenAI, Ramp, Vanta, Retool…) are already covered via
  `company_boards.yaml`.

## 3. The company list mechanism (Phase 1 — this change)

A declarative YAML file is the single source of truth. Adding a company = adding one line.

```yaml
# config/company_boards.yaml
companies:
  - company: Stripe
    category: fintech
    ats: greenhouse          # greenhouse | lever | ashby | smartrecruiters | workday | custom
    token: stripe            # board slug used by the ATS API
    priority: 1              # 1 = poll most often (Tier A), 2/3 = less often
  - company: Amazon
    category: big_tech
    ats: custom
    adapter: amazon          # named custom adapter (for non-ATS career APIs)
    priority: 1
```

`CompanyBoardsScraper` reads this file and dispatches each entry to the right adapter. The list is
verified periodically by the `verify-company-boards` workflow (see §9), which re-checks that every
token still returns live jobs (companies do migrate between ATS platforms).

## 4. Fetching architecture

```
config/company_boards.yaml
        │
        ▼
CompanyBoardsScraper (BaseScraper)
        │  dispatch by `ats`
        ├── greenhouse   → boards-api.greenhouse.io/v1/boards/{token}/jobs
        ├── lever        → api.lever.co/v0/postings/{token}?mode=json
        ├── ashby        → api.ashbyhq.com/posting-api/job-board/{token}
        ├── smartrecruiters → api.smartrecruiters.com/v1/companies/{token}/postings
        ├── workable    → apply.workable.com/api/v1/widget/accounts/{token}
        ├── workday      → POST {tenant}.wdN.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
        │                  (Nvidia, Salesforce, Mastercard, Adobe, Intel, PayPal, Snap)
        └── custom       → named adapter: amazon, netflix (now); microsoft/google/apple/meta (Phase 4)
        │
        ▼
normalize → Job model  →  should_include_job() filter  →  dedup  →  DB
```

Design notes:
- **Per-host rate limiting + concurrency cap** (reuse `scraper_utils.get_rate_limiter`).
- **Keyword/title + freshness filtering** reuses `BaseScraper.should_include_job`.
- Each adapter is a small pure function `(entry) -> list[Job]`, independently testable.
- Custom adapters isolate the fiddly big-tech APIs so ATS adapters stay simple.

## 5. Near-real-time / "webhook" reality

**Important:** Greenhouse, Lever, Ashby, SmartRecruiters and the big-tech career APIs **do not
offer public webhooks** to third parties. Their webhooks are for the *employer's* own integrations,
not job seekers. So "real-time" for us = **high-frequency polling + delta detection**, plus an
**internal** event that fires when our poller sees something new.

Mechanism:
1. **High-frequency poll** of Tier-A boards (every 2–5 min).
2. **Delta detection**: keep a per-board set of seen job IDs (persisted). Emit only IDs not seen
   before. This is cheap and reliable — most ATS APIs return the full board each call.
3. **Conditional requests**: send `If-None-Modified` / `ETag` where supported to skip unchanged
   boards (Greenhouse supports `updated_after`; use it to shrink payloads).
4. **Internal webhook / event bus**: when a new Tier-A job is detected → publish an internal event
   → immediately trigger the auto-apply flow for that job (bypass the normal batch cadence). This is
   the "webhook that triggers on a new posting" you asked for — we generate it ourselves from the
   poller rather than receiving it from the ATS.
5. **RSS/Atom where available**: some Workday tenants and Lever boards expose RSS; subscribe where
   present (lighter than full polling).
6. **Inbound email triggers**: LinkedIn/Indeed/company job-alert emails → parse with the existing
   email infra → treat as a new-job signal. Good complement for sources we can't poll.

## 6. Scheduling

There is currently **no persistent scheduler** — scraping runs on demand (CLI `scrape`, or the
orchestrator's `_scrape_jobs`). Add a tiered scheduler (APScheduler or an asyncio loop):

| Job | Cadence | Notes |
|-----|---------|-------|
| Tier A poll (priority 1 companies) | 2–5 min | delta detection → instant auto-apply trigger |
| Tier B ATS sweep | 15–30 min | rotating slices of the big board list |
| Tier C aggregators | hourly | |
| Tier D feeds | hourly–daily | Simplify/Jobright/BuiltIn/Greenhouse |
| Board re-verification workflow | weekly | detects ATS/token drift |

Add jitter and per-host backoff to avoid thundering-herd / bans.

## 7. Dedup & state

- Reuse existing dedup: URL normalization + content-hash (`check_content_duplicates`).
- Add a lightweight **per-source cursor/state** (seen-ID set or `last_seen_at`) for delta detection —
  either a small table or a JSON blob per board.

## 8. Auto-apply handoff

New job → detect `application_type` (Workday / Greenhouse / Lever / Ashby) → route to the matching
auto-apply filler. **ATS-based sources are ideal**: the application form is standardized per ATS, so
one filler per ATS covers every company on it. This is the strategic reason Tier A/B are prioritized.

## 9. Phased rollout

- **Phase 1 (now):** `config/company_boards.yaml` + `CompanyBoardsScraper` with adapters for
  Greenhouse, Lever, Ashby, SmartRecruiters, plus custom `amazon` and `netflix`. Verified via the
  `verify-company-boards` workflow. Wired into the aggregator behind a config flag.
- **Phase 2:** Aggregator-API scrapers (RemoteOK, Remotive, Arbeitnow, The Muse; Adzuna/USAJobs with keys).
- **Phase 3:** Tiered scheduler + delta-detection state table.
- **Phase 4:** Custom big-tech adapters (Microsoft, Google, Apple, Meta). (Workday adapter ✅ done —
  Nvidia/Salesforce/Mastercard/Adobe/Intel/PayPal/Snap; CompanyBoards also has a per-board cap so one
  huge board can't starve the rest.)
- **Phase 5:** Internal event bus → instant auto-apply on a new Tier-A job (the self-generated webhook).
- **Phase 6:** Inbound email/RSS triggers.

## 10. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Anti-bot / Cloudflare (killed Careerjet) | Prefer JSON APIs over HTML; realistic headers; backoff; skip captcha-walled sites |
| Token drift (company switches ATS) | Weekly `verify-company-boards` workflow re-checks every token |
| Rate limits / IP bans | Per-host limiter, jitter, conditional requests, caching |
| Big-tech API churn | Isolate in custom adapters; monitor; each is independently swappable |
| Duplicate roles across sources | Existing URL + content-hash dedup |

## Appendix A — Verified ATS endpoint recipes

```
Greenhouse:      GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs        → {"jobs":[...]}
                 (incremental: ?updated_after=ISO8601)
Lever:           GET https://api.lever.co/v0/postings/{token}?mode=json             → [ ...postings ]
Ashby:           GET https://api.ashbyhq.com/posting-api/job-board/{token}          → {"jobs":[...]}
SmartRecruiters: GET https://api.smartrecruiters.com/v1/companies/{token}/postings  → {"content":[...],"totalFound":N}
Amazon (custom): GET https://www.amazon.jobs/en/search.json?base_query=...&result_limit=N → {"jobs":[...],"hits":N}
Netflix (custom, Eightfold):
                 GET https://explore.jobs.netflix.net/api/apply/v2/jobs?query=...&limit=N → {"positions":[...],"count":N}
```

Big-tech needing bespoke adapters (Phase 4): Microsoft (`gcsservices.careers.microsoft.com` search
API), Google (careers SPA API), Apple (`jobs.apple.com` search API — token/anti-bot headers), Meta
(`metacareers.com` GraphQL with rotating `doc_id`).

## Appendix B — The verified company list

See `config/company_boards.yaml` (generated and periodically re-verified by the
`verify-company-boards` workflow). Companies are grouped by category and ATS; each entry has been
confirmed to return live postings at build time.
