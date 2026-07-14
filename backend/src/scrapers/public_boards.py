"""
Public Boards Scraper — pulls from no-auth public job APIs / feeds.

One scraper, one adapter per source, all fetched concurrently. Every source is a
public JSON API or RSS feed that needs no login (verified against awesome-job-boards).
The software-only + seniority + recency gates in should_include_job apply to all of them.

Sources: Remotive, RemoteOK, Jobicy, Himalayas, Working Nomads, 4 Day Week,
We Work Remotely (RSS), and USAJOBS (only if a free API key is configured).
"""
import asyncio
import os
import re
from email.utils import parsedate_to_datetime

import httpx

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_value, parse_date_string
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type
from src.utils.logger import logger


_UA = {"User-Agent": "Mozilla/5.0 (compatible; PaperPlane/1.0)", "Accept": "application/json"}


def _rfc822(s: str):
    try:
        return parsedate_to_datetime(s) if s else None
    except (TypeError, ValueError):
        return None


class PublicBoardsScraper(BaseScraper):
    SOURCE_NAME = "PublicBoards"
    SOURCE_TYPE = JobSource.OTHER

    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        adapters = [
            self._remotive, self._remoteok, self._jobicy, self._himalayas,
            self._workingnomads, self._fourdayweek, self._weworkremotely, self._usajobs,
        ]
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            results = await asyncio.gather(*[a(client) for a in adapters], return_exceptions=True)

        jobs: list[Job] = []
        seen: set[str] = set()
        for adapter, res in zip(adapters, results):
            if isinstance(res, Exception):
                logger.debug(f"PublicBoards: {adapter.__name__} failed: {res}")
                continue
            kept = 0
            for job in res:
                if not job or job.url in seen:
                    continue
                seen.add(job.url)
                if self.should_include_job(job):
                    jobs.append(job)
                    kept += 1
                    if len(jobs) >= limit:
                        break
            logger.info(f"      {adapter.__name__[1:]}: {kept} kept ({len(res)} fetched)")
            if len(jobs) >= limit:
                break

        self.jobs_found = len(jobs)
        logger.info(f"   🌐 PublicBoards: Found {len(jobs)} software jobs")
        return jobs[:limit]

    def _job(self, *, title, company, url, source, location="Remote", description=None,
             salary=None, posted_date=None, apply_url=None) -> Job:
        if not url:
            return None
        # Normalize to naive datetimes (some feeds are tz-aware) to match the rest of the pipeline.
        if posted_date is not None and posted_date.tzinfo is not None:
            posted_date = posted_date.replace(tzinfo=None)
        app_type, _ = detect_application_type(apply_url or url)
        return Job(
            title=(title or "").strip(),
            company=(company or "Unknown").strip(),
            location=(location or "Remote").strip() or "Remote",
            url=url,
            apply_url=apply_url or url,
            description=(description[:500] if description else None),
            salary_range=salary,
            source=source,
            application_type=app_type,
            posted_date=posted_date,
            job_type="Full-time",
            tags=[source.value],
        )

    # ---- adapters (each returns list[Job]; gating happens in scrape()) -------

    async def _remotive(self, client) -> list[Job]:
        r = await client.get("https://remotive.com/api/remote-jobs",
                             params={"category": "software-dev", "limit": 200}, headers=_UA)
        out = []
        for it in (r.json().get("jobs", []) if r.status_code == 200 else []):
            out.append(self._job(
                title=it.get("title"), company=it.get("company_name"), url=it.get("url"),
                source=JobSource.REMOTIVE, location=it.get("candidate_required_location", "Remote"),
                description=it.get("description"), salary=it.get("salary") or None,
                posted_date=parse_date_string(it.get("publication_date", "")),
            ))
        return out

    async def _remoteok(self, client) -> list[Job]:
        r = await client.get("https://remoteok.com/api", headers=_UA)
        out = []
        for it in (r.json() if r.status_code == 200 else []):
            if not isinstance(it, dict) or not it.get("position"):
                continue  # first element is metadata
            sal = None
            if it.get("salary_min"):
                sal = f"${it['salary_min']}-${it.get('salary_max', '')}"
            out.append(self._job(
                title=it.get("position"), company=it.get("company"),
                url=it.get("url") or it.get("apply_url"), apply_url=it.get("apply_url"),
                source=JobSource.REMOTEOK, location=it.get("location") or "Remote",
                description=it.get("description"), salary=sal,
                posted_date=parse_date_value(it.get("epoch")) or parse_date_string(it.get("date", "")),
            ))
        return out

    async def _jobicy(self, client) -> list[Job]:
        r = await client.get("https://jobicy.com/api/v2/remote-jobs",
                             params={"count": 100, "tag": "engineering"}, headers=_UA)
        out = []
        for it in (r.json().get("jobs", []) if r.status_code == 200 else []):
            sal = None
            if it.get("salaryMin"):
                sal = f"{it.get('salaryCurrency', '')}{it['salaryMin']}-{it.get('salaryMax', '')}".strip()
            out.append(self._job(
                title=it.get("jobTitle"), company=it.get("companyName"), url=it.get("url"),
                source=JobSource.JOBICY, location=it.get("jobGeo", "Remote"),
                description=it.get("jobExcerpt"), salary=sal,
                posted_date=parse_date_value(it.get("pubDate")) or parse_date_string(it.get("pubDate", "")),
            ))
        return out

    async def _himalayas(self, client) -> list[Job]:
        # API caps at 20/request but supports offset pagination — page a few in parallel.
        async def page(off):
            r = await client.get("https://himalayas.app/jobs/api",
                                 params={"limit": 20, "offset": off, "experience": "entry-level"}, headers=_UA)
            return r.json().get("jobs", []) if r.status_code == 200 else []
        pages = await asyncio.gather(*[page(o) for o in range(0, 160, 20)], return_exceptions=True)
        out = []
        for it in [j for p in pages if isinstance(p, list) for j in p]:
            locs = it.get("locationRestrictions") or []
            sal = None
            if it.get("minSalary"):
                sal = f"{it.get('currency', '')}{it['minSalary']}-{it.get('maxSalary', '')}".strip()
            out.append(self._job(
                title=it.get("title"), company=it.get("companyName"),
                url=it.get("applicationLink") or it.get("guid"), apply_url=it.get("applicationLink"),
                source=JobSource.HIMALAYAS,
                location=", ".join(locs) if isinstance(locs, list) and locs else "Remote",
                description=it.get("excerpt"), salary=sal,
                posted_date=parse_date_value(it.get("pubDate")),
            ))
        return out

    async def _workingnomads(self, client) -> list[Job]:
        r = await client.get("https://www.workingnomads.com/api/exposed_jobs/", headers=_UA)
        out = []
        for it in (r.json() if r.status_code == 200 else []):
            cat = (it.get("category_name") or "").lower()
            if not any(k in cat for k in ("develop", "engineer", "program", "software", "devops", "data")):
                continue  # cheap category prefilter; software gate still applies
            out.append(self._job(
                title=it.get("title"), company=it.get("company_name"), url=it.get("url"),
                source=JobSource.WORKINGNOMADS, location=it.get("location") or "Remote",
                description=it.get("description"),
                posted_date=parse_date_string(it.get("pub_date", "")),
            ))
        return out

    async def _fourdayweek(self, client) -> list[Job]:
        out = []
        for page in (1, 2):
            r = await client.get("https://4dayweek.io/api/jobs", params={"page": page}, headers=_UA)
            if r.status_code != 200:
                break
            data = r.json()
            for it in data.get("jobs", []):
                if it.get("is_expired"):
                    continue
                locs = it.get("locations") or []
                loc = "Remote"
                if isinstance(locs, list) and locs and isinstance(locs[0], dict):
                    loc = ", ".join(x for x in [locs[0].get("city"), locs[0].get("country")] if x) or "Remote"
                out.append(self._job(
                    title=it.get("title"), company=it.get("company_name"),
                    url=f"https://4dayweek.io/jobs/{it.get('slug')}",
                    source=JobSource.FOURDAYWEEK, location=loc,
                    posted_date=parse_date_value(it.get("posted")),
                ))
            if not data.get("has_more"):
                break
        return out

    async def _weworkremotely(self, client) -> list[Job]:
        # RSS (the .json endpoint is Cloudflare-walled)
        cats = ["remote-programming-jobs", "remote-full-stack-programming-jobs",
                "remote-back-end-programming-jobs", "remote-front-end-programming-jobs"]
        out = []
        for cat in cats:
            r = await client.get(f"https://weworkremotely.com/categories/{cat}.rss",
                                 headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                continue
            for m in re.finditer(r"<item>(.*?)</item>", r.text, re.S):
                block = m.group(1)
                def tag(t):
                    mm = re.search(rf"<{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", block, re.S)
                    return (mm.group(1).strip() if mm else "")
                raw_title = tag("title")
                link = tag("link")
                if not raw_title or not link:
                    continue
                # RSS title is "Company: Role"
                company, _, title = raw_title.partition(":")
                if not title:
                    company, title = "Unknown", raw_title
                out.append(self._job(
                    title=title.strip(), company=company.strip(), url=link,
                    source=JobSource.WEWORKREMOTELY, location=tag("region") or "Remote",
                    posted_date=_rfc822(tag("pubDate")),
                ))
        return out

    async def _usajobs(self, client) -> list[Job]:
        api_key = os.getenv("USAJOBS_API_KEY")
        email = os.getenv("USAJOBS_EMAIL")
        if not api_key or not email:
            return []  # inactive until a free key is configured
        out = []
        headers = {"Authorization-Key": api_key, "User-Agent": email, "Host": "data.usajobs.gov"}
        r = await client.get("https://data.usajobs.gov/api/search",
                             params={"Keyword": "software engineer", "ResultsPerPage": 100},
                             headers=headers)
        if r.status_code != 200:
            return []
        items = r.json().get("SearchResult", {}).get("SearchResultItems", [])
        for it in items:
            d = it.get("MatchedObjectDescriptor", {})
            locs = d.get("PositionLocationDisplay") or "USA"
            out.append(self._job(
                title=d.get("PositionTitle"), company=d.get("OrganizationName"),
                url=d.get("PositionURI"), apply_url=(d.get("ApplyURI") or [None])[0],
                source=JobSource.USAJOBS, location=locs,
                description=(d.get("UserArea", {}).get("Details", {}) or {}).get("JobSummary"),
                posted_date=parse_date_string(d.get("PublicationStartDate", "")),
            ))
        return out
