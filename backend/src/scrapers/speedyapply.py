"""
SpeedyApply Scraper — parses the speedyapply/*-College-Jobs GitHub markdown tables.

These repos publish new-grad / internship SWE roles as markdown tables (no JSON feed).
Each row is:
  | <a href="COMPANY_SITE"><strong>COMPANY</strong></a> | POSITION | LOCATION | SALARY |
  <a href="APPLY_URL"><img .../></a> | AGE |
The last <a href> in a row is the real application link.
"""
import re

import httpx

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.job_filter import is_software_role
from src.core.job import Job, JobSource
from src.classifiers.detector import detect_application_type
from src.utils.logger import logger


_HREF_RE = re.compile(r'href="([^"]+)"')
_STRONG_RE = re.compile(r'<strong>(.*?)</strong>', re.I | re.S)
_TAG_RE = re.compile(r'<[^>]+>')
_AGE_RE = re.compile(r'(\d+)\s*(d|mo|h|w|m|y)', re.I)


class SpeedyApplyScraper(BaseScraper):
    SOURCE_NAME = "SpeedyApply"
    SOURCE_TYPE = JobSource.SPEEDYAPPLY

    RAW_BASE = "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main"
    # US new-grad by default; add NEW_GRAD_INTL.md / INTERN_INTL.md for wider coverage.
    FILES = ["NEW_GRAD_USA.md"]

    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for fname in self.FILES:
                if len(jobs) >= limit:
                    break
                try:
                    r = await client.get(f"{self.RAW_BASE}/{fname}", headers={"User-Agent": "PaperPlane/1.0"})
                    if r.status_code != 200:
                        continue
                    for job in self._parse_markdown(r.text):
                        if job.url in seen:
                            continue
                        seen.add(job.url)
                        if is_software_role(job.title) and self.should_include_job(job):
                            jobs.append(job)
                            if len(jobs) >= limit:
                                break
                except Exception as e:
                    logger.error(f"SpeedyApply: error fetching {fname}: {e}")

        self.jobs_found = len(jobs)
        logger.info(f"   ⚡ SpeedyApply: Found {len(jobs)} software jobs")
        return jobs[:limit]

    def _parse_markdown(self, text: str) -> list[Job]:
        jobs = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("|") or "href" not in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue

            company_cell, position, loc_cell, salary_cell = cells[0], cells[1], cells[2], cells[3]
            age_cell = cells[5] if len(cells) > 5 else (cells[-1] if len(cells) > 4 else "")

            # Company site is the first <a href>; the application link is the last.
            hrefs = _HREF_RE.findall(line)
            if len(hrefs) < 2:
                continue  # only a company link (no application link) → skip
            apply_url = hrefs[-1]
            if not apply_url.startswith("http"):
                continue

            title = _TAG_RE.sub("", position).strip()
            if not title:
                continue

            company_m = _STRONG_RE.search(company_cell)
            company = (company_m.group(1) if company_m else _TAG_RE.sub("", company_cell)).strip() or "Unknown"
            location = _TAG_RE.sub("", loc_cell).strip() or "Remote"
            salary = _TAG_RE.sub("", salary_cell).strip() or None

            app_type, _ = detect_application_type(apply_url)
            jobs.append(Job(
                title=title,
                company=company,
                location=location,
                url=apply_url,
                apply_url=apply_url,
                salary_range=salary if salary and "$" in salary else None,
                source=JobSource.SPEEDYAPPLY,
                application_type=app_type,
                posted_date=self._age_to_date(age_cell),
                job_type="Full-time",
                tags=["speedyapply", "new-grad"],
            ))
        return jobs

    @staticmethod
    def _age_to_date(age: str):
        from datetime import datetime, timedelta
        m = _AGE_RE.search(age or "")
        if not m:
            return None
        n = int(m.group(1))
        unit = m.group(2).lower()
        days = {"h": 0, "d": 1, "w": 7, "mo": 30, "m": 30, "y": 365}.get(unit, 1) * n
        return datetime.now() - timedelta(days=days)
