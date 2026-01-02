"""
Dashboard API - FastAPI backend for the web dashboard
"""

from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.utils.database import get_db
from src.utils.config import get_settings
from src.core.job import JobStatus, ApplicationType

# Create FastAPI app
app = FastAPI(
    title="AutoApplier Dashboard",
    description="Monitor and manage your job applications",
    version="1.0.0"
)

# Static files and templates
DASHBOARD_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")


# ============= API Models =============

class JobUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class StatsResponse(BaseModel):
    total: int
    applied: int
    pending: int
    failed: int
    needs_review: int
    by_platform: dict
    by_source: dict
    recent_applications: list


# ============= API Routes =============

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/stats")
async def get_stats():
    """Get application statistics"""
    db = get_db()
    stats = db.get_job_stats()
    
    # Get additional breakdowns
    from sqlalchemy import func
    from src.utils.database import JobModel
    
    with db.session() as session:
        # Count by platform
        by_platform = {}
        platform_counts = session.query(
            JobModel.application_type, func.count(JobModel.id)
        ).group_by(JobModel.application_type).all()
        for platform, count in platform_counts:
            by_platform[platform or "unknown"] = count
        
        # Count by source
        by_source = {}
        source_counts = session.query(
            JobModel.source, func.count(JobModel.id)
        ).group_by(JobModel.source).all()
        for source, count in source_counts:
            by_source[source or "unknown"] = count
        
        # Get recent applications
        recent = session.query(JobModel).filter(
            JobModel.status == JobStatus.APPLIED.value
        ).order_by(JobModel.applied_at.desc()).limit(10).all()
        
        recent_apps = [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "applied_at": j.applied_at.isoformat() if j.applied_at else None,
            }
            for j in recent
        ]
    
    return {
        **stats,
        "needs_review": 0,  # TODO: Track this separately
        "by_platform": by_platform,
        "by_source": by_source,
        "recent_applications": recent_apps,
    }


@app.get("/api/jobs")
async def list_jobs(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List jobs with optional filters"""
    db = get_db()
    
    from src.utils.database import JobModel
    
    with db.session() as session:
        query = session.query(JobModel)
        
        if status:
            query = query.filter(JobModel.status == status)
        
        if platform:
            query = query.filter(JobModel.application_type == platform)
        
        total = query.count()
        jobs = query.order_by(JobModel.discovered_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "jobs": [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "url": j.url,
                    "status": j.status,
                    "platform": j.application_type,
                    "source": j.source,
                    "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
                    "applied_at": j.applied_at.isoformat() if j.applied_at else None,
                }
                for j in jobs
            ]
        }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job"""
    db = get_db()
    job = db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.model_dump()


@app.patch("/api/jobs/{job_id}")
async def update_job(job_id: str, update: JobUpdate):
    """Update a job's status"""
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


@app.get("/api/llm-usage")
async def get_llm_usage():
    """Get LLM API usage stats"""
    try:
        from src.llm.gemini import GeminiClient
        settings = get_settings()
        
        if not settings.gemini_api_key:
            return {"error": "Gemini API key not configured"}
        
        client = GeminiClient()
        return client.get_usage_stats()
    except Exception as e:
        return {"error": str(e)}


# ============= Run Server =============

def run_dashboard(host: str = "127.0.0.1", port: int = 8080):
    """Run the dashboard server"""
    import uvicorn
    print(f"\n🚀 Starting AutoApplier Dashboard at http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
