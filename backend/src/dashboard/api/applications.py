"""Auto-apply endpoints: trigger a single application, abort it, poll its status,
and kick off the full auto-apply run. In-flight apps are tracked in
state.running_applications so abort/status see the same objects."""
import asyncio
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.utils.database import get_db
from src.utils.logger import logger
from src.utils import paths
from src.core.job import JobStatus
from src.dashboard.dependencies import require_admin
from src.dashboard.state import running_applications

router = APIRouter()


@router.post("/api/apply/{job_id}", dependencies=[Depends(require_admin)])
async def trigger_apply(job_id: str, background_tasks: BackgroundTasks):
    """Trigger application for a specific job"""
    db = get_db()
    job = db.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if already running
    if job_id in running_applications and not running_applications[job_id].get("cancelled"):
        return {"status": "already_running", "job_id": job_id, "message": "Application already in progress"}

    # Register this application
    running_applications[job_id] = {"cancelled": False, "started_at": datetime.now()}

    async def run_single_apply():
        from src.orchestrator import Orchestrator
        from src.core.applicant import Applicant
        from src.core.application import Application

        logger.info(f"🎯 Starting application for: {job.title} at {job.company}")

        # Check if cancelled before starting
        if running_applications.get(job_id, {}).get("cancelled"):
            logger.info(f"   🛑 Application {job_id} was cancelled before starting")
            running_applications.pop(job_id, None)
            return

        # Load profile (repo-root data/, regardless of where we launched from)
        profile_path = paths.profile_path()

        if not profile_path.exists():
            logger.error(f"Profile not found at {profile_path}")
            running_applications.pop(job_id, None)
            return

        applicant = Applicant.from_file(profile_path)
        orchestrator = Orchestrator(applicant)
        await orchestrator.setup()

        try:
             # Initial update
             db.update_job_status(job_id, JobStatus.IN_PROGRESS)

             # Check cancellation
             if running_applications.get(job_id, {}).get("cancelled"):
                 logger.info(f"   🛑 Application {job_id} cancelled during setup")
                 db.update_job_status(job_id, JobStatus.NEW)  # Reset to new
                 return

             application = Application.from_job(job)

             # Determine filler
             filler_class = orchestrator.fillers.get(job.application_type)
             if not filler_class:
                 from src.fillers.universal_filler import UniversalFiller
                 filler_class = UniversalFiller

             # Check cancellation before fill
             if running_applications.get(job_id, {}).get("cancelled"):
                 logger.info(f"   🛑 Application {job_id} cancelled before filling")
                 db.update_job_status(job_id, JobStatus.NEW)
                 return

             success = await orchestrator._fill_application(job, application, filler_class)

             # Check cancellation after fill
             if running_applications.get(job_id, {}).get("cancelled"):
                 logger.info(f"   🛑 Application {job_id} cancelled - not updating status")
                 db.update_job_status(job_id, JobStatus.NEW)
                 return

             if success:
                 db.update_job_status(job_id, JobStatus.APPLIED)
                 logger.info(f"   🚀 SUCCESS - Applied to {job.title} at {job.company}")
             else:
                 # If it failed but wasn't marked rejected, mark failed
                 if job.status != JobStatus.REJECTED.value:
                     db.update_job_status(job_id, JobStatus.FAILED)
                     logger.warning(f"   ❌ FAILED - Could not apply to {job.title} at {job.company}")

        except asyncio.CancelledError:
            logger.info(f"   🛑 Application {job_id} task was cancelled")
            db.update_job_status(job_id, JobStatus.NEW)
        except Exception as e:
            logger.error(f"Single apply error: {e}")
            if not running_applications.get(job_id, {}).get("cancelled"):
                db.update_job_status(job_id, JobStatus.FAILED)
        finally:
            await orchestrator.teardown()
            running_applications.pop(job_id, None)

    background_tasks.add_task(run_single_apply)
    return {"status": "started", "job_id": job_id, "message": "Application process started"}


@router.post("/api/apply/{job_id}/abort", dependencies=[Depends(require_admin)])
async def abort_apply(job_id: str):
    """Abort an in-progress application"""
    db = get_db()
    job = db.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_id not in running_applications:
        # Not running - just reset status if it was in_progress
        if job.status == JobStatus.IN_PROGRESS.value:
            db.update_job_status(job_id, JobStatus.NEW)
        return {"status": "not_running", "job_id": job_id, "message": "No application in progress"}

    # Mark as cancelled
    running_applications[job_id]["cancelled"] = True
    logger.info(f"   🛑 Abort requested for job {job_id}")

    # Reset job status
    db.update_job_status(job_id, JobStatus.NEW)

    return {"status": "aborted", "job_id": job_id, "message": "Application abort requested"}


@router.get("/api/apply/{job_id}/status")
async def get_apply_status(job_id: str):
    """Get the status of an application process"""
    is_running = job_id in running_applications and not running_applications[job_id].get("cancelled")
    started_at = running_applications.get(job_id, {}).get("started_at")

    return {
        "job_id": job_id,
        "is_running": is_running,
        "started_at": started_at.isoformat() if started_at else None
    }


@router.post("/api/run", dependencies=[Depends(require_admin)])
async def trigger_auto_apply_run(background_tasks: BackgroundTasks):
    """Trigger the main auto-apply loop"""

    async def run_wrapper():
        from src.orchestrator import run_auto_apply
        try:
            logger.info("🚀 AUTO-APPLY SEQUENCE INITIATED — targeting 5 applications")
            # Run with default settings (5 applications per run)
            await run_auto_apply(max_applications=5, scrape_first=False)
            logger.info("✅ AUTO-APPLY SEQUENCE COMPLETE")
        except Exception as e:
            logger.error(f"Auto-run error: {e}")

    background_tasks.add_task(run_wrapper)
    return {"status": "started", "message": "Auto-apply sequence initiated"}
