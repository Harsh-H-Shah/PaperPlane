"""Job CRUD endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_

from src.utils.database import get_db
from src.utils.logger import logger
from src.core.job import JobStatus, ApplicationType
from src.dashboard.dependencies import require_admin
from src.dashboard.schemas import JobCreate, JobUpdate

router = APIRouter()


@router.post("/api/jobs", dependencies=[Depends(require_admin)])
@router.post("/api/jobs/", dependencies=[Depends(require_admin)])
async def create_job(job_in: JobCreate):
    db = get_db()
    from src.core.job import Job, JobSource
    import uuid

    logger.info(f"Manual job creation request for: {job_in.title} at {job_in.company}")

    job = Job(
        title=job_in.title,
        company=job_in.company,
        url=job_in.url,
        id=str(uuid.uuid4()),  # Assign new ID for manual entries
        location=job_in.location or "",
        source=JobSource.MANUAL,
        application_type=ApplicationType(job_in.application_type) if job_in.application_type else ApplicationType.UNKNOWN
    )

    try:
        job_id = db.add_job(job)
        job.id = job_id  # Sync ID with database
        logger.info(f"   ✅ Job created/reset with ID: {job_id}")
        return {"id": job_id, "success": True, "job": job.model_dump()}
    except Exception as e:
        logger.error(f"   ❌ Error creating job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jobs")
async def list_jobs(
    status: Optional[str] = None,
    source: Optional[str] = None,
    app_type: Optional[str] = Query(None, alias="type"),
    search: Optional[str] = None,
    sort: Optional[str] = "newest",
    page: int = 1,
    per_page: int = 50
):
    db = get_db()
    from src.utils.database import JobModel

    with db.session() as session:
        query = session.query(JobModel)

        if status and status != 'all':
            query = query.filter(JobModel.status == status)
        elif not search:
            query = query.filter(JobModel.status != JobStatus.REJECTED.value)

        # 2. Source Filter
        if source and source != 'all':
            query = query.filter(JobModel.source == source)

        if app_type and app_type != 'all':
            query = query.filter(JobModel.application_type == app_type)

        if search:
            search_term = f"%{search}%"
            query = query.filter(or_(
                JobModel.title.ilike(search_term),
                JobModel.company.ilike(search_term)
            ))

        total = query.count()
        offset = (page - 1) * per_page

        # Apply Sorting
        order_attr = JobModel.discovered_at.desc()  # Default
        if sort == "oldest":
            order_attr = JobModel.discovered_at.asc()
        elif sort == "company":
            order_attr = JobModel.company.asc()
        elif sort == "title":
            order_attr = JobModel.title.asc()

        jobs = query.order_by(order_attr).offset(offset).limit(per_page).all()

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
            "has_more": offset + len(jobs) < total,
            "jobs": [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "url": j.url,
                    "status": j.status,
                    "source": j.source,
                    "application_type": j.application_type,
                    "apply_url": j.apply_url,
                    "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
                    "posted_date": j.posted_date.isoformat() if j.posted_date else None,
                }
                for j in jobs
            ]
        }


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    db = get_db()
    job = db.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.model_dump()


@router.patch("/api/jobs/{job_id}", dependencies=[Depends(require_admin)])
async def update_job(job_id: str, update: JobUpdate):
    db = get_db()
    from src.utils.database import JobModel

    with db.session() as session:
        job = session.query(JobModel).filter(JobModel.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if update.status:
            try:
                new_status = JobStatus(update.status)
                job.status = new_status.value
                if new_status == JobStatus.APPLIED:
                    job.applied_at = datetime.now()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status")

    return {"success": True}


@router.delete("/api/jobs/{job_id}", dependencies=[Depends(require_admin)])
async def delete_job(job_id: str):
    """Soft delete a job by marking it as REJECTED"""
    db = get_db()
    from src.utils.database import JobModel

    with db.session() as session:
        job = session.query(JobModel).filter(JobModel.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        job.status = JobStatus.REJECTED.value

    return {"success": True}
