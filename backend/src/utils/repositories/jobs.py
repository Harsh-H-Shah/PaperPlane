"""Job query/mutation methods, mixed into Database. Uses self.session()."""
from datetime import datetime
from typing import Optional

from src.core.job import Job, JobStatus, JobSource
from src.utils.models import JobModel


class JobRepositoryMixin:
    def add_job(self, job: Job) -> str:
        job_id = job.id or str(hash(job.url))
        job.id = job_id

        with self.session() as session:
            existing = session.query(JobModel).filter(JobModel.url == job.url).first()
            if existing:
                # If manual, reset status to NEW to ensure visibility
                if job.source == JobSource.MANUAL or job.source == JobSource.MANUAL.value:
                    existing.status = JobStatus.NEW.value
                    existing.source = JobSource.MANUAL.value
                    existing.discovered_at = datetime.now()
                return existing.id

            job_model = JobModel.from_job(job)
            session.add(job_model)
            session.flush()

        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.session() as session:
            job_model = session.query(JobModel).filter(JobModel.id == job_id).first()
            return job_model.to_job() if job_model else None

    def filter_existing_urls(self, urls: list[str]) -> set[str]:
        if not urls:
            return set()

        existing = set()
        # Process in chunks to avoid SQLite limits
        chunk_size = 500
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i:i + chunk_size]
            with self.session() as session:
                results = session.query(JobModel.url).filter(
                    JobModel.url.in_(chunk)
                ).all()
                existing.update(r[0] for r in results)
        return existing

    def add_jobs_bulk(self, jobs: list[Job]) -> int:
        if not jobs:
            return 0

        count = 0
        with self.session() as session:
            job_models = []
            for job in jobs:
                job.id = job.id or str(hash(job.url))
                job.discovered_at = datetime.now()
                job.status = JobStatus.NEW
                job_models.append(JobModel.from_job(job))

            if job_models:
                session.bulk_save_objects(job_models)
                count = len(job_models)

        return count

    def check_content_duplicates(self, candidates: list[Job]) -> set[str]:
        if not candidates:
            return set()

        duplicate_urls = set()

        # Prepare candidates for query
        # We check against jobs from last 7 days to keep query efficient
        # cutoff_date = datetime.now().strftime("%Y-%m-%d")

        # We need to check one by one or construct a complex OR query.
        # A complex OR query is better: (title=t1 AND company=c1) OR (title=t2 AND company=c2)...
        # But SQLite limit is 1000 vars. So batching is needed.

        from sqlalchemy import or_, and_, func

        chunk_size = 50
        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i + chunk_size]

            conditions = []
            for job in chunk:
                # Basic normalization
                t = job.title.lower().strip()
                c = job.company.lower().strip()
                conditions.append(
                    and_(
                        func.lower(JobModel.title) == t,
                        func.lower(JobModel.company) == c
                    )
                )

            if not conditions:
                continue

            with self.session() as session:
                matches = session.query(JobModel.url, JobModel.title, JobModel.company).filter(
                    or_(*conditions)
                ).all()

                # Double check matches in python to map back to candidate URLs
                # because the query returns existing URLs, we need to know which candidate caused it.
                # Actually, if we find a match (title+company), we just need to flag the candidate that has that title+company.

                matched_pairs = set()
                for url, title, company in matches:
                    matched_pairs.add((title.lower().strip(), company.lower().strip()))

                for job in chunk:
                    t = job.title.lower().strip()
                    c = job.company.lower().strip()
                    if (t, c) in matched_pairs:
                        duplicate_urls.add(job.url)

        return duplicate_urls

    def get_jobs_by_status(self, status: JobStatus, limit: int = 100) -> list[Job]:
        with self.session() as session:
            job_models = session.query(JobModel).filter(
                JobModel.status == status.value
            ).limit(limit).all()
            return [jm.to_job() for jm in job_models]

    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        return self.get_jobs_by_status(JobStatus.NEW, limit) + \
               self.get_jobs_by_status(JobStatus.QUEUED, limit)

    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        with self.session() as session:
            job_model = session.query(JobModel).filter(JobModel.id == job_id).first()
            if job_model:
                job_model.status = status.value if hasattr(status, 'value') else status
                if status == JobStatus.APPLIED or status == JobStatus.APPLIED.value:
                    job_model.applied_at = datetime.now()

    def get_job_stats(self) -> dict:
        with self.session() as session:
            total = session.query(JobModel).count()
            applied = session.query(JobModel).filter(
                JobModel.status == JobStatus.APPLIED.value
            ).count()
            pending = session.query(JobModel).filter(
                JobModel.status.in_([JobStatus.NEW.value, JobStatus.QUEUED.value])
            ).count()
            failed = session.query(JobModel).filter(
                JobModel.status == JobStatus.FAILED.value
            ).count()
            needs_review = session.query(JobModel).filter(
                JobModel.status == JobStatus.NEEDS_REVIEW.value
            ).count()
            expired = session.query(JobModel).filter(
                JobModel.status == JobStatus.EXPIRED.value
            ).count()

            return {
                "total": total,
                "applied": applied,
                "pending": pending,
                "failed": failed,
                "needs_review": needs_review,
                "expired": expired,
            }
