from datetime import datetime
from typing import Optional
from pathlib import Path
import asyncio

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.utils.database import get_db
from src.utils.config import get_settings
from src.core.job import JobStatus, ApplicationType

app = FastAPI(title="AutoApplier Dashboard", version="2.0.0")

DASHBOARD_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")


class JobUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class ScrapeRequest(BaseModel):
    sources: Optional[list[str]] = None
    limit: int = 200


# ============ Pages ============

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "page": "dashboard"})


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    return templates.TemplateResponse("jobs.html", {"request": request, "page": "jobs"})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "page": "settings"})


# ============ API ============

@app.get("/api/stats")
async def get_stats():
    db = get_db()
    stats = db.get_job_stats()
    
    from sqlalchemy import func
    from src.utils.database import JobModel
    
    with db.session() as session:
        by_source = {}
        source_counts = session.query(
            JobModel.source, func.count(JobModel.id)
        ).group_by(JobModel.source).all()
        for source, count in source_counts:
            by_source[source or "unknown"] = count
        
        recent = session.query(JobModel).filter(
            JobModel.status == JobStatus.APPLIED.value
        ).order_by(JobModel.applied_at.desc()).limit(5).all()
        
        recent_apps = [
            {"id": j.id, "title": j.title, "company": j.company, "applied_at": j.applied_at.isoformat() if j.applied_at else None}
            for j in recent
        ]
    
    return {
        **stats,
        "by_source": by_source,
        "recent_applications": recent_apps,
    }


@app.get("/api/jobs")
async def list_jobs(
    status: Optional[str] = None, 
    source: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50
):
    db = get_db()
    from src.utils.database import JobModel
    
    with db.session() as session:
        query = session.query(JobModel)
        
        if status:
            query = query.filter(JobModel.status == status)
        
        if source:
            query = query.filter(JobModel.source == source)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (JobModel.title.ilike(search_term)) | 
                (JobModel.company.ilike(search_term))
            )
        
        total = query.count()
        offset = (page - 1) * per_page
        jobs = query.order_by(JobModel.discovered_at.desc()).offset(offset).limit(per_page).all()
        
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
                    "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
                }
                for j in jobs
            ]
        }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    db = get_db()
    job = db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.model_dump()


@app.patch("/api/jobs/{job_id}")
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


@app.get("/api/scrapers/status")
async def get_scraper_status():
    settings = get_settings()
    
    scrapers = [
        {
            "name": "Simplify",
            "enabled": settings.scrapers.simplify.enabled,
            "configured": True,
            "icon": "📦"
        },
        {
            "name": "CVRVE",
            "enabled": settings.scrapers.cvrve.enabled,
            "configured": True,
            "icon": "🎯"
        },
        {
            "name": "LinkedIn",
            "enabled": settings.scrapers.linkedin.enabled,
            "configured": bool(settings.linkedin_li_at),
            "icon": "💼",
            "note": "Requires LINKEDIN_LI_AT cookie" if not settings.linkedin_li_at else None
        },
        {
            "name": "Jobright",
            "enabled": True,
            "configured": True,
            "icon": "🚀"
        },
        {
            "name": "Dice",
            "enabled": True,
            "configured": True,
            "icon": "🎲"
        },
        {
            "name": "WeWorkRemotely",
            "enabled": True,
            "configured": True,
            "icon": "🌍"
        },
    ]
    
    return {"scrapers": scrapers}


# Global state for scrape progress
SCRAPE_STATUS = {
    "is_running": False,
    "current_source": "",
    "jobs_found": 0,
    "jobs_new": 0,
    "last_updated": None
}

@app.get("/api/scrape/progress")
async def get_scrape_progress():
    return SCRAPE_STATUS

@app.post("/api/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    if SCRAPE_STATUS["is_running"]:
        return {"status": "error", "message": "Scrape already in progress"}
        
    async def run_scrape_wrapper():
        global SCRAPE_STATUS
        SCRAPE_STATUS["is_running"] = True
        SCRAPE_STATUS["jobs_found"] = 0
        SCRAPE_STATUS["jobs_new"] = 0
        SCRAPE_STATUS["last_updated"] = datetime.now()
        
        try:
            from src.scrapers.aggregator import JobAggregator
            # Run manually to update progress
            agg = JobAggregator(validate_links=False)
            
            sources = request.sources or [s.SOURCE_NAME.lower() for s in agg.scrapers]
            
            for source in sources:
                SCRAPE_STATUS["current_source"] = source
                SCRAPE_STATUS["last_updated"] = datetime.now()
                
                try:
                    jobs, raw_count = await agg.scrape_source(source, limit=request.limit)
                    SCRAPE_STATUS["jobs_found"] += raw_count
                    SCRAPE_STATUS["jobs_new"] += len(jobs)
                except Exception as e:
                    print(f"Scrape error {source}: {e}")
            
            SCRAPE_STATUS["current_source"] = "Done"
            
        finally:
            SCRAPE_STATUS["is_running"] = False
            SCRAPE_STATUS["current_source"] = ""
            
    background_tasks.add_task(run_scrape_wrapper)
    return {"status": "started", "message": "Scraping started"}


@app.get("/api/llm-usage")
async def get_llm_usage():
    try:
        from src.llm.gemini import GeminiClient
        settings = get_settings()
        
        if not settings.gemini_api_key:
            return {"error": "Gemini API key not configured"}
        
        client = GeminiClient()
        return client.get_usage_stats()
    except Exception as e:
        return {"error": str(e)}


def run_dashboard(host: str = "127.0.0.1", port: int = 8080):
    import uvicorn
    print(f"\n🚀 Starting AutoApplier Dashboard at http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
