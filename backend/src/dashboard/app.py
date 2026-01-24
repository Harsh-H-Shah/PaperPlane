from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import asyncio
import json

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sqlalchemy import or_
from src.utils.database import get_db
from src.utils.config import get_settings
from src.core.job import JobStatus, ApplicationType

app = FastAPI(title="AutoApplier Dashboard", version="2.0.0")

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHBOARD_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")

# Gamification constants
# Gamification constants
XP_REWARDS = {
    "application_submitted": 25,
    "callback_received": 50,
    "interview_scheduled": 100,
    "offer_received": 500,
    "daily_streak_bonus": 10,
    "quest_completed": 75,
}

# Valorant Ranks: 3=Iron 1 ... 27=Radiant
VALORANT_RANKS = {
    3: "Iron 1", 4: "Iron 2", 5: "Iron 3",
    6: "Bronze 1", 7: "Bronze 2", 8: "Bronze 3",
    9: "Silver 1", 10: "Silver 2", 11: "Silver 3",
    12: "Gold 1", 13: "Gold 2", 14: "Gold 3",
    15: "Platinum 1", 16: "Platinum 2", 17: "Platinum 3",
    18: "Diamond 1", 19: "Diamond 2", 20: "Diamond 3",
    21: "Ascendant 1", 22: "Ascendant 2", 23: "Ascendant 3",
    24: "Immortal 1", 25: "Immortal 2", 26: "Immortal 3",
    27: "Radiant"
}

TIER_UUID = "03621f52-342b-cf4e-4f86-9350a49c6d04"


class JobUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class JobCreate(BaseModel):
    title: str
    company: str
    url: str
    location: Optional[str] = ""
    source: Optional[str] = "manual"
    application_type: Optional[str] = "unknown"


class ScrapeRequest(BaseModel):
    sources: Optional[list[str]] = None
    limit: int = 100

def get_rank_info(xp: int) -> dict:
    """Calculate rank info from XP using Valorant system (100 RR per rank)"""
    # Start at Iron 1 (Tier 3)
    # Each 100 XP is one tier
    tier_offset = int(xp / 100)
    tier_index = 3 + tier_offset
    
    # Cap at Radiant (27)
    if tier_index > 27:
        tier_index = 27
    
    rank_title = VALORANT_RANKS.get(tier_index, "Unranked")
    current_rr = xp % 100
    
    # Radiant accumulates RR indefinitely
    if tier_index == 27:
        current_rr = xp - ((27 - 3) * 100)
    
    return {
        "rank_title": rank_title,
        "tier_index": tier_index,
        "current_rr": current_rr,
        "rr_for_next_rank": 100,
        "rank_icon": f"https://media.valorant-api.com/competitivetiers/{TIER_UUID}/{tier_index}/largeicon.png"
    }


def calculate_streak(db) -> int:
    """Calculate current application streak (consecutive days with applications)"""
    from src.utils.database import JobModel
    from sqlalchemy import func
    
    with db.session() as session:
        # Get dates with applications - convert to string YYYY-MM-DD
        dates = session.query(
            func.date(JobModel.applied_at)
        ).filter(
            JobModel.status == JobStatus.APPLIED.value,
            JobModel.applied_at.isnot(None)
        ).distinct().order_by(func.date(JobModel.applied_at).desc()).limit(30).all()
        
        if not dates:
            return 0
        
        streak = 0
        today = datetime.now().date()
        
        for i, (date_str,) in enumerate(dates):
            if not date_str:
                continue
            
            # SQLite returns string YYYY-MM-DD
            try:
                date_obj = datetime.strptime(str(date_str), "%Y-%m-%d").date()
            except ValueError:
                continue
                
            expected = today - timedelta(days=i)
            
            # If the most recent application was NOT today, check if it was yesterday
            # If i==0 and date is yesterday, streak is kept (but not incremented for today if we haven't applied today)
            # Actually, standard streak logic:
            # If applied today: streak includes today.
            # If not applied today but applied yesterday: streak is valid but doesn't include today? 
            # Usually streak = consecutive days counting back from today (if applied today) or yesterday.
            
            # Let's simplify: Count backwards from most recent application.
            # If most recent application is today or yesterday, streak is alive.
            # If older, streak is broken (0).
            
            if i == 0:
                if date_obj == today:
                    streak = 1
                    current_check_date = today
                elif date_obj == today - timedelta(days=1):
                    streak = 1
                    current_check_date = today - timedelta(days=1)
                else:
                    return 0 # Streak broken
            else:
                expected_next = current_check_date - timedelta(days=1)
                if date_obj == expected_next:
                    streak += 1
                    current_check_date = expected_next
                else:
                    break
        
        return streak

@app.get("/api/gamification")
async def get_gamification():
    """Get gamification data: XP, level, streak"""
    db = get_db()
    stats = db.get_job_stats()
    
    # Calculate XP from applications
    applied = stats.get("applied", 0)
    total_xp = applied * XP_REWARDS["application_submitted"]
    
    # Add streak bonus
    streak = calculate_streak(db)
    total_xp += streak * XP_REWARDS["daily_streak_bonus"]
    
    rank_info = get_rank_info(total_xp)
    
    return {
        "total_xp": total_xp,
        "level": rank_info["tier_index"], # Use tier index as level
        "level_title": rank_info["rank_title"],
        "current_xp_in_level": rank_info["current_rr"], # Use RR as XP in level
        "xp_for_next_level": rank_info["rr_for_next_rank"],
        "rank_icon": rank_info["rank_icon"], # New field
        "streak": streak,
        "applications_today": get_applications_today(db),
    }


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

        # Weekly Activity
        today = datetime.now().date()
        start_date = today - timedelta(days=6)
        
        daily_counts = session.query(
            func.date(JobModel.applied_at), func.count(JobModel.id)
        ).filter(
            JobModel.status == JobStatus.APPLIED.value,
            JobModel.applied_at >= start_date
        ).group_by(func.date(JobModel.applied_at)).all()
        
        activity_map = {str(day): count for day, count in daily_counts}
        weekly_activity = []
        for i in range(7):
            d = start_date + timedelta(days=i)
            day_str = d.strftime("%Y-%m-%d")
            day_name = d.strftime("%a")
            count = activity_map.get(day_str, 0)
            weekly_activity.append({"day": day_name, "applications": count})
            
    return {
        **stats,
        "by_source": by_source,
        "recent_applications": recent_apps,
        "weekly_activity": weekly_activity,
    }


@app.post("/api/jobs")
@app.post("/api/jobs/")
async def create_job(job_in: JobCreate):
    db = get_db()
    from src.core.job import Job, JobSource, ApplicationType
    import uuid
    
    print(f"DEBUG: Manual job creation request for: {job_in.title} at {job_in.company}")
    
    job = Job(
        title=job_in.title,
        company=job_in.company,
        url=job_in.url,
        id=str(uuid.uuid4()), # Assign new ID for manual entries
        location=job_in.location or "",
        source=JobSource.MANUAL,
        application_type=ApplicationType(job_in.application_type) if job_in.application_type else ApplicationType.UNKNOWN
    )
    
    try:
        job_id = db.add_job(job)
        job.id = job_id # Sync ID with database 
        print(f"   ✅ Job created/reset with ID: {job_id}")
        return {"id": job_id, "success": True, "job": job.model_dump()}
    except Exception as e:
        print(f"   ❌ Error creating job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs")
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
        order_attr = JobModel.discovered_at.desc() # Default
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


@app.delete("/api/jobs/{job_id}")
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
            "name": "Jobright",
            "enabled": True,
            "configured": True,
            "icon": "🚀"
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
            agg = JobAggregator(validate_links=True)
            
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


@app.get("/api/activity")
async def get_activity_log(lines: int = 50):
    print(f"accessing activity log path: {Path(__file__).parent.parent.parent / 'logs' / 'activity.log'}")
    """Get recent activity logs"""
    log_path = Path(__file__).parent.parent.parent / "logs" / "activity.log"
    
    if not log_path.exists():
        return {"logs": []}
        
    try:
        # Simple tail implementation
        with open(log_path, "r") as f:
            all_lines = f.readlines()
            # Filter empty lines
            all_lines = [l.strip() for l in all_lines if l.strip()]
            return {"logs": all_lines[-lines:]}
    except Exception as e:
        return {"logs": [f"Error reading log: {str(e)}"]}

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


# ============ Gamification API ============




@app.get("/api/profile")
async def get_profile():
    """Get agent profile - combines profile.json with SQLite preferences"""
    from src.utils.database import UserPreferencesModel
    
    profile_path = Path(__file__).parent.parent.parent.parent / "data" / "profile.json"
    
    # Get valorant_agent from SQLite database
    db = get_db()
    valorant_agent = "jett"  # Default
    try:
        with db.session() as session:
            pref = session.query(UserPreferencesModel).filter(
                UserPreferencesModel.key == "valorant_agent"
            ).first()
            if pref:
                valorant_agent = pref.value
    except Exception:
        pass  # Use default if DB query fails
    
    if not profile_path.exists():
        return {
            "agent_name": "UNKNOWN",
            "first_name": "Agent",
            "last_name": "Unknown",
            "full_name": "Unknown Agent",
            "avatar": None,
            "level": 1,
            "level_title": "RECRUIT",
            "valorant_agent": valorant_agent,
        }
    
    try:
        with open(profile_path) as f:
            profile = json.load(f)
        
        personal = profile.get("personal", {})
        
        return {
            "agent_name": personal.get("first_name", "Agent").upper(),
            "first_name": personal.get("first_name", "Agent"),
            "last_name": personal.get("last_name", ""),
            "full_name": personal.get("full_name", "Agent"),
            "email": personal.get("email", ""),
            "github": personal.get("github", ""),
            "avatar": None,
            "valorant_agent": valorant_agent,  # From SQLite
        }
    except Exception as e:
        return {"error": str(e)}


class ProfileUpdate(BaseModel):
    valorant_agent: Optional[str] = None


@app.patch("/api/profile")
async def update_profile(update: ProfileUpdate):
    """Update profile settings (valorant_agent) - stores in SQLite database"""
    from src.utils.database import UserPreferencesModel
    
    db = get_db()
    
    try:
        with db.session() as session:
            if update.valorant_agent:
                # Update or insert preference
                pref = session.query(UserPreferencesModel).filter(
                    UserPreferencesModel.key == "valorant_agent"
                ).first()
                
                if pref:
                    pref.value = update.valorant_agent
                else:
                    pref = UserPreferencesModel(key="valorant_agent", value=update.valorant_agent)
                    session.add(pref)
        
        return {"success": True, "valorant_agent": update.valorant_agent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))







def get_applications_today(db) -> int:
    """Get number of applications submitted today"""
    from src.utils.database import JobModel
    from sqlalchemy import func
    
    today = datetime.now().date()
    
    with db.session() as session:
        count = session.query(func.count(JobModel.id)).filter(
            JobModel.status == JobStatus.APPLIED.value,
            func.date(JobModel.applied_at) == today
        ).scalar()
        return count or 0


@app.get("/api/quests")
async def get_quests():
    """Get daily/weekly quests"""
    db = get_db()
    stats = db.get_job_stats()
    apps_today = get_applications_today(db)
    
    quests = [
        {
            "id": "daily_rapid",
            "name": "RAPID RECRUITMENT",
            "description": "Infiltrate and apply to 5 high-priority roles. High yield rewards upon completion.",
            "type": "daily",
            "target": 5,
            "progress": min(apps_today, 5),
            "xp_reward": 75,
            "completed": apps_today >= 5,
            "priority": True,
        },
        {
            "id": "weekly_grind",
            "name": "WEEKLY GRIND",
            "description": "Submit 25 applications this week.",
            "type": "weekly",
            "target": 25,
            "progress": min(stats.get("applied", 0) % 25, 25),  # Simplified
            "xp_reward": 250,
            "completed": False,
            "priority": False,
        },
        {
            "id": "streak_master",
            "name": "STREAK MASTER",
            "description": "Maintain a 7-day application streak.",
            "type": "achievement",
            "target": 7,
            "progress": calculate_streak(db),
            "xp_reward": 200,
            "completed": calculate_streak(db) >= 7,
            "priority": False,
        },
    ]
    
    return {"quests": quests}


@app.get("/api/combat-history")
async def get_combat_history():
    """Get recent job applications with game-style status labels"""
    db = get_db()
    from src.utils.database import JobModel
    
    STATUS_LABELS = {
        "in_progress": {"label": "IN FILTRATION", "xp": 25, "color": "yellow"},
        "applied": {"label": "DEPLOYED", "xp": 25, "color": "green"},
        "needs_review": {"label": "INTEL REQUIRED", "xp": 0, "color": "orange"},
        "failed": {"label": "MISSION FAILED", "xp": 0, "color": "red"},
        "skipped": {"label": "ABORTED", "xp": 0, "color": "gray"},
    }
    
    with db.session() as session:
        recent = session.query(JobModel).filter(
            JobModel.status.in_([
                JobStatus.APPLIED.value,
                JobStatus.IN_PROGRESS.value,
                JobStatus.NEEDS_REVIEW.value,
                JobStatus.FAILED.value,
            ])
        ).order_by(JobModel.discovered_at.desc()).limit(10).all()
        
        history = []
        for job in recent:
            status_info = STATUS_LABELS.get(job.status, {"label": "UNKNOWN", "xp": 0, "color": "gray"})
            
            # Determine icon based on job title
            icon = "💼"
            title_lower = job.title.lower() if job.title else ""
            if "design" in title_lower:
                icon = "🎨"
            elif "engineer" in title_lower or "developer" in title_lower:
                icon = "⚙️"
            elif "product" in title_lower:
                icon = "📦"
            elif "data" in title_lower:
                icon = "📊"
            elif "manager" in title_lower or "lead" in title_lower:
                icon = "👑"
            
            history.append({
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "source": job.source,
                "status": job.status,
                "status_label": status_info["label"],
                "status_color": status_info["color"],
                "xp_reward": status_info["xp"],
                "icon": icon,
                "applied_at": job.applied_at.isoformat() if job.applied_at else None,
                "discovered_at": job.discovered_at.isoformat() if job.discovered_at else None,
            })
        
        return {"history": history}


@app.post("/api/apply/{job_id}")
async def trigger_apply(job_id: str, background_tasks: BackgroundTasks):
    """Trigger application for a specific job"""
    db = get_db()
    job = db.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    async def run_single_apply():
        from src.orchestrator import Orchestrator
        from src.core.applicant import Applicant
        from src.core.application import Application
        
        # Load profile
        # Since we run from backend/ directory, data/ is in parent
        root_dir = Path(__file__).parent.parent.parent.parent
        profile_path = root_dir / "data" / "profile.json"
        
        # Fallback for dev environment path differences
        if not profile_path.exists():
             # Try just "data/profile.json" in case CWD is root
             profile_path = Path("data/profile.json")

        if not profile_path.exists():
            print(f"Profile not found at {profile_path} or data/profile.json")
            return
            
        applicant = Applicant.from_file(profile_path)
        orchestrator = Orchestrator(applicant)
        await orchestrator.setup()
        
        try:
             # Initial update
             db.update_job_status(job_id, JobStatus.IN_PROGRESS)
             
             application = Application.from_job(job)
             
             # Determine filler
             filler_class = orchestrator.fillers.get(job.application_type)
             if not filler_class:
                 from src.fillers.universal_filler import UniversalFiller
                 filler_class = UniversalFiller
             
             success = await orchestrator._fill_application(job, application, filler_class)
             
             if success:
                 db.update_job_status(job_id, JobStatus.APPLIED)
             else:
                 # If it failed but wasn't marked rejected, mark failed
                 if job.status != JobStatus.REJECTED.value:
                     db.update_job_status(job_id, JobStatus.FAILED)
                     
        except Exception as e:
            print(f"Single apply error: {e}")
            db.update_job_status(job_id, JobStatus.FAILED)
        finally:
            await orchestrator.teardown()

    background_tasks.add_task(run_single_apply)
    return {"status": "started", "job_id": job_id, "message": "Application process started"}


@app.post("/api/run")
async def trigger_auto_apply_run(background_tasks: BackgroundTasks):
    """Trigger the main auto-apply loop"""
    
    async def run_wrapper():
        from src.orchestrator import run_auto_apply
        try:
            # Run with default settings (5 applications per run)
            await run_auto_apply(max_applications=5, scrape_first=False)
        except Exception as e:
            print(f"Auto-run error: {e}")
            
    background_tasks.add_task(run_wrapper)
    return {"status": "started", "message": "Auto-apply sequence initiated"}



def run_dashboard(host: str = "127.0.0.1", port: int = 8080):
    import uvicorn
    print(f"\n🚀 Starting AutoApplier Dashboard at http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
