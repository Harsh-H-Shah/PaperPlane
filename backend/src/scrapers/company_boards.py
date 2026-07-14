"""
Company Boards Scraper — fetches roles from a curated list of top companies.

The list lives in `config/company_boards.yaml` (one line per company). Each entry
declares which ATS hosts the company's board plus the board token, and this scraper
dispatches to the right adapter. Standard ATS platforms (Greenhouse, Lever, Ashby,
SmartRecruiters) share a simple JSON API; big-tech companies with bespoke career APIs
are handled by named `custom` adapters (amazon, netflix).

Adding a company = adding one entry to the YAML — no code change required.
See docs/JOB_INGESTION_PLAN.md for the broader ingestion roadmap.
"""
import asyncio
import re
from typing import Optional

import httpx
import yaml

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.scraper_utils import parse_date_value, parse_date_string
from src.scrapers.job_filter import is_software_role
from src.core.job import Job, JobSource, ApplicationType
from src.utils import paths
from src.utils.logger import logger


# Maps the `ats` field in the YAML to the ApplicationType used downstream for auto-apply routing.
_APP_TYPE = {
    "greenhouse": ApplicationType.GREENHOUSE,
    "lever": ApplicationType.LEVER,
    "ashby": ApplicationType.ASHBY,
    "smartrecruiters": ApplicationType.SMARTRECRUITERS,
    "workday": ApplicationType.WORKDAY,
}

_HEADERS = {"User-Agent": "PaperPlane/1.0", "Accept": "application/json"}


class CompanyBoardsScraper(BaseScraper):
    SOURCE_NAME = "CompanyBoards"
    SOURCE_TYPE = JobSource.COMPANY_BOARDS

    def __init__(self, config_path=None, entries: list[dict] = None):
        super().__init__()
        self.config_path = config_path or (paths.config_dir() / "company_boards.yaml")
        self.entries = entries if entries is not None else self._load_entries()

    def _load_entries(self) -> list[dict]:
        try:
            with open(self.config_path) as f:
                data = yaml.safe_load(f) or {}
            entries = data.get("companies", [])
            # Skip entries explicitly disabled or without a usable token/adapter.
            return [e for e in entries if e.get("enabled", True)]
        except FileNotFoundError:
            logger.warning(f"CompanyBoards: config not found at {self.config_path}")
            return []
        except Exception as e:
            logger.error(f"CompanyBoards: failed to load config: {e}")
            return []

    # Cap per board so one huge board (e.g. Anduril ~2k roles) can't starve the rest.
    PER_BOARD_CAP = 60

    async def scrape(self, keywords: list[str] = None, location: str = None, limit: int = 50) -> list[Job]:
        keywords = keywords or self.get_search_keywords()
        jobs: list[Job] = []

        # Fetch boards concurrently in batches to avoid hammering any single host.
        batch_size = 8
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for i in range(0, len(self.entries), batch_size):
                if len(jobs) >= limit:
                    break
                batch = self.entries[i:i + batch_size]
                results = await asyncio.gather(
                    *[self._fetch_entry(client, e) for e in batch],
                    return_exceptions=True,
                )
                for entry, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.debug(f"CompanyBoards: {entry.get('company')} failed: {result}")
                        continue
                    kept_this_board = 0
                    for job in result:
                        if self.should_include_job(job):
                            jobs.append(job)
                            kept_this_board += 1
                            if len(jobs) >= limit or kept_this_board >= self.PER_BOARD_CAP:
                                break
                    if len(jobs) >= limit:
                        break
                await asyncio.sleep(0.3)

        self.jobs_found = len(jobs)
        logger.info(f"   🏢 CompanyBoards: Found {len(jobs)} jobs from {len(self.entries)} boards")
        return jobs[:limit]

    async def _fetch_entry(self, client: httpx.AsyncClient, entry: dict) -> list[Job]:
        ats = (entry.get("ats") or "").lower()
        adapter = self._ADAPTERS.get(entry.get("adapter") or ats)
        if not adapter:
            return []
        try:
            raw = await adapter(self, client, entry)
        except httpx.HTTPError:
            return []
        # Software-only gate (broad recall, non-software excluded)
        return [j for j in raw if is_software_role(j.title)]

    def _make_job(self, entry: dict, *, title, url, ats, external_id,
                  location="Remote", description=None, posted_date=None, extra_tags=None) -> Optional[Job]:
        if not title or not url:
            return None
        tags = [ats, entry.get("category", ""), entry.get("company", "")] + (extra_tags or [])
        return Job(
            title=title,
            company=entry.get("company", entry.get("token", "Unknown")),
            location=location or "Remote",
            url=url,
            apply_url=url,
            description=(description[:500] if description else None),
            source=JobSource.COMPANY_BOARDS,
            application_type=_APP_TYPE.get(ats, ApplicationType.CUSTOM),
            posted_date=posted_date,
            job_type="Full-time",
            tags=[t for t in tags if t],
            external_id=str(external_id) if external_id is not None else None,
            raw_data={"board": entry.get("token"), "ats": ats},
        )

    # ---- ATS adapters -----------------------------------------------------

    async def _greenhouse(self, client, entry) -> list[Job]:
        token = entry["token"]
        r = await client.get(
            f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
            params={"content": "true"}, headers=_HEADERS,
        )
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("jobs", []):
            loc = it.get("location") or {}
            out.append(self._make_job(
                entry, title=it.get("title", ""),
                url=it.get("absolute_url", ""), ats="greenhouse",
                external_id=it.get("id"),
                location=loc.get("name", "Remote") if isinstance(loc, dict) else "Remote",
                description=it.get("content"),
                posted_date=parse_date_string(it.get("updated_at", "")),
            ))
        return [j for j in out if j]

    async def _lever(self, client, entry) -> list[Job]:
        token = entry["token"]
        r = await client.get(f"https://api.lever.co/v0/postings/{token}", params={"mode": "json"}, headers=_HEADERS)
        if r.status_code != 200:
            return []
        out = []
        for it in r.json():
            cats = it.get("categories", {}) or {}
            out.append(self._make_job(
                entry, title=it.get("text", ""),
                url=it.get("hostedUrl") or it.get("applyUrl", ""), ats="lever",
                external_id=it.get("id"),
                location=cats.get("location", "Remote"),
                description=it.get("descriptionPlain") or it.get("description"),
                posted_date=parse_date_value(it.get("createdAt")),
                extra_tags=[cats.get("team", ""), cats.get("commitment", "")],
            ))
        return [j for j in out if j]

    async def _ashby(self, client, entry) -> list[Job]:
        token = entry["token"]
        r = await client.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}", headers=_HEADERS)
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("jobs", []):
            out.append(self._make_job(
                entry, title=it.get("title", ""),
                url=it.get("jobUrl") or it.get("applyUrl", ""), ats="ashby",
                external_id=it.get("id"),
                location=it.get("location", "Remote"),
                description=it.get("descriptionPlain") or it.get("description"),
                posted_date=parse_date_string(it.get("publishedAt", "")),
                extra_tags=[it.get("department", ""), it.get("team", "")],
            ))
        return [j for j in out if j]

    async def _smartrecruiters(self, client, entry) -> list[Job]:
        token = entry["token"]
        r = await client.get(
            f"https://api.smartrecruiters.com/v1/companies/{token}/postings",
            params={"limit": 100}, headers=_HEADERS,
        )
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("content", []):
            loc = it.get("location", {}) or {}
            loc_str = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x) or "Remote"
            job_id = it.get("id")
            url = f"https://jobs.smartrecruiters.com/{token}/{job_id}"
            out.append(self._make_job(
                entry, title=it.get("name", ""), url=url, ats="smartrecruiters",
                external_id=job_id, location=loc_str,
                posted_date=parse_date_string(it.get("releasedDate", "")),
            ))
        return [j for j in out if j]

    async def _workable(self, client, entry) -> list[Job]:
        token = entry["token"]
        r = await client.get(
            f"https://apply.workable.com/api/v1/widget/accounts/{token}",
            params={"details": "true"}, headers=_HEADERS,
        )
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("jobs", []):
            loc = it.get("location", {}) or {}
            loc_str = ", ".join(x for x in [loc.get("city"), loc.get("region"), loc.get("country")] if x) or "Remote"
            out.append(self._make_job(
                entry, title=it.get("title", ""),
                url=it.get("url") or it.get("application_url", ""), ats="workable",
                external_id=it.get("shortcode") or it.get("id"),
                location=loc_str, description=it.get("description"),
                posted_date=parse_date_string(it.get("published_on", "") or it.get("created_at", "")),
                extra_tags=[it.get("department", "")],
            ))
        return [j for j in out if j]

    async def _workday(self, client, entry) -> list[Job]:
        # Workday CXS jobs API: POST to entry["endpoint"], paginate in 20s.
        endpoint = entry.get("endpoint")
        if not endpoint:
            return []
        # Derive the public detail-URL base: strip trailing /jobs, then rewrite
        # https://host/wday/cxs/{tenant}/{site}  ->  https://host/en-US/{site}
        base = endpoint.rsplit("/jobs", 1)[0]
        m = re.match(r"(https?://[^/]+)/wday/cxs/[^/]+/(.+)$", base)
        detail_base = f"{m.group(1)}/en-US/{m.group(2)}" if m else None

        out = []
        for offset in (0, 20, 40):
            try:
                r = await client.post(endpoint, headers=_HEADERS, json={
                    "appliedFacets": {}, "limit": 20, "offset": offset, "searchText": "software engineer",
                })
            except httpx.HTTPError:
                break
            if r.status_code != 200:
                break
            posts = r.json().get("jobPostings", [])
            for it in posts:
                path = it.get("externalPath", "")
                out.append(self._make_job(
                    entry, title=it.get("title", ""),
                    url=f"{detail_base}{path}" if (detail_base and path) else endpoint,
                    ats="workday", external_id=path.rsplit("_", 1)[-1] if "_" in path else path,
                    location=it.get("locationsText", ""),
                    posted_date=parse_date_string(it.get("postedOn", "")),
                ))
            if len(posts) < 20:
                break
        return [j for j in out if j]

    # ---- custom big-tech adapters ----------------------------------------

    async def _amazon(self, client, entry) -> list[Job]:
        jobs: list[Job] = []
        for query in (self.get_search_keywords() or ["software engineer"])[:2]:
            r = await client.get(
                "https://www.amazon.jobs/en/search.json",
                params={"base_query": query, "result_limit": 100, "sort": "recent"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code != 200:
                continue
            for it in r.json().get("jobs", []):
                path = it.get("job_path", "")
                jobs.append(self._make_job(
                    entry, title=it.get("title", ""),
                    url=f"https://www.amazon.jobs{path}" if path else it.get("url_next_step", ""),
                    ats="custom", external_id=it.get("id_icims") or it.get("id"),
                    location=it.get("location") or it.get("normalized_location", "Remote"),
                    description=it.get("description_short") or it.get("description"),
                    posted_date=parse_date_string(it.get("posted_date", "")),
                ))
        return [j for j in jobs if j]

    async def _netflix(self, client, entry) -> list[Job]:
        r = await client.get(
            "https://explore.jobs.netflix.net/api/apply/v2/jobs",
            params={"query": "software", "limit": 100, "domain": "netflix.com"},
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("positions", []):
            out.append(self._make_job(
                entry, title=it.get("name", ""),
                url=it.get("canonicalPositionUrl") or it.get("positionUrl", ""),
                ats="custom", external_id=it.get("id"),
                location=", ".join(it.get("locations", [])) or "Remote",
                description=it.get("job_description"),
                posted_date=parse_date_value(it.get("t_create")),
            ))
        return [j for j in out if j]

    _ADAPTERS = {
        "greenhouse": _greenhouse,
        "lever": _lever,
        "ashby": _ashby,
        "smartrecruiters": _smartrecruiters,
        "workable": _workable,
        "workday": _workday,
        "amazon": _amazon,
        "netflix": _netflix,
    }
