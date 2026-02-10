from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import asyncio
import json
import logging
import os

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Query, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sqlalchemy import or_
from src.utils.database import get_db
from src.utils.config import get_settings
from src.core.job import JobStatus, ApplicationType

logger = logging.getLogger(__name__)

# ============ Admin Auth ============
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")


def get_token_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


def require_admin(authorization: Optional[str] = Header(None)):
    """Dependency that blocks unauthenticated users from write endpoints."""
    if not ADMIN_TOKEN:
        return  # No token configured = no auth required (dev mode)
    token = get_token_from_header(authorization)
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin access required")


def is_admin(authorization: Optional[str] = Header(None)) -> bool:
    """Check if current request is from admin (non-blocking)."""
    if not ADMIN_TOKEN:
        return True
    token = get_token_from_header(authorization)
    return token == ADMIN_TOKEN

app = FastAPI(title="PaperPlane API", version="2.0.0")

# Track running application tasks for abort functionality
running_applications: Dict[str, dict] = {}  # job_id -> {"cancelled": bool, "started_at": datetime}

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://paperplane.harsh.software"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Auth Endpoints ============

@app.post("/api/auth/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify if the provided token is valid."""
    if not ADMIN_TOKEN:
        return {"authenticated": True, "message": "No auth configured"}
    token = get_token_from_header(authorization)
    if token == ADMIN_TOKEN:
        return {"authenticated": True}
    raise HTTPException(status_code=403, detail="Invalid token")


@app.get("/api/auth/status")
async def auth_status():
    """Check if auth is enabled (no token needed)."""
    return {"auth_required": bool(ADMIN_TOKEN)}

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
                
            # expected = today - timedelta(days=i)
            
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


@app.post("/api/jobs", dependencies=[Depends(require_admin)])
@app.post("/api/jobs/", dependencies=[Depends(require_admin)])
async def create_job(job_in: JobCreate):
    db = get_db()
    from src.core.job import Job, JobSource
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


@app.patch("/api/jobs/{job_id}", dependencies=[Depends(require_admin)])
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


@app.delete("/api/jobs/{job_id}", dependencies=[Depends(require_admin)])
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
    "last_updated": None,
    "errors": [],
}

@app.get("/api/scrape/progress")
async def get_scrape_progress():
    return SCRAPE_STATUS

@app.post("/api/scrape", dependencies=[Depends(require_admin)])
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    if SCRAPE_STATUS["is_running"]:
        return {"status": "error", "message": "Scrape already in progress"}
        
    async def run_scrape_wrapper():
        global SCRAPE_STATUS
        SCRAPE_STATUS["is_running"] = True
        SCRAPE_STATUS["jobs_found"] = 0
        SCRAPE_STATUS["jobs_new"] = 0
        SCRAPE_STATUS["errors"] = []
        SCRAPE_STATUS["last_updated"] = datetime.now()
        
        try:
            from src.scrapers.aggregator import JobAggregator
            import traceback
            # Run manually to update progress
            agg = JobAggregator(validate_links=True)
            
            sources = request.sources or [s.SOURCE_NAME.lower() for s in agg.scrapers]
            print(f"DEBUG SCRAPE: Starting scrape for sources: {sources}")
            
            for source in sources:
                SCRAPE_STATUS["current_source"] = source
                SCRAPE_STATUS["last_updated"] = datetime.now()
                print(f"DEBUG SCRAPE: Scraping source: {source}")
                
                try:
                    jobs, raw_count = await agg.scrape_source(source, limit=request.limit)
                    SCRAPE_STATUS["jobs_found"] += raw_count
                    SCRAPE_STATUS["jobs_new"] += len(jobs)
                    print(f"DEBUG SCRAPE: {source} -> found={raw_count}, new={len(jobs)}")
                except Exception as e:
                    error_msg = f"{source}: {str(e)}"
                    tb = traceback.format_exc()
                    print(f"Scrape error {error_msg}\n{tb}")
                    SCRAPE_STATUS["errors"].append(error_msg)
            
            SCRAPE_STATUS["current_source"] = "Done"
            
        except Exception as e:
            import traceback
            print(f"CRITICAL SCRAPE ERROR: {e}\n{traceback.format_exc()}")
            SCRAPE_STATUS["errors"].append(f"CRITICAL: {str(e)}")
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
            all_lines = [line.strip() for line in all_lines if line.strip()]
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
async def get_profile(authorization: Optional[str] = Header(None)):
    """Get agent profile - combines profile.json with SQLite preferences.
    Non-admin users get redacted profile data."""
    from src.utils.database import UserPreferencesModel
    
    admin = is_admin(authorization)
    
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
        
        first_name = personal.get("first_name", "Agent")
        last_name = personal.get("last_name", "")
        
        if admin:
            return {
                "agent_name": first_name.upper(),
                "first_name": first_name,
                "last_name": last_name,
                "full_name": personal.get("full_name", "Agent"),
                "email": personal.get("email", ""),
                "github": personal.get("github", ""),
                "avatar": None,
                "valorant_agent": valorant_agent,
            }
        else:
            # Redacted profile for public visitors
            return {
                "agent_name": first_name.upper(),
                "first_name": first_name,
                "last_name": last_name[0] + "." if last_name else "",
                "full_name": f"{first_name} {last_name[0]}." if last_name else first_name,
                "email": "",
                "github": "",
                "avatar": None,
                "valorant_agent": valorant_agent,
            }
    except Exception as e:
        return {"error": str(e)}


class ProfileUpdate(BaseModel):
    valorant_agent: Optional[str] = None


@app.patch("/api/profile", dependencies=[Depends(require_admin)])
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


@app.post("/api/apply/{job_id}", dependencies=[Depends(require_admin)])
async def trigger_apply(job_id: str, background_tasks: BackgroundTasks):
    """Trigger application for a specific job"""
    global running_applications
    
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
        
        # Check if cancelled before starting
        if running_applications.get(job_id, {}).get("cancelled"):
            print(f"   🛑 Application {job_id} was cancelled before starting")
            running_applications.pop(job_id, None)
            return
        
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
                 print(f"   🛑 Application {job_id} cancelled during setup")
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
                 print(f"   🛑 Application {job_id} cancelled before filling")
                 db.update_job_status(job_id, JobStatus.NEW)
                 return
             
             success = await orchestrator._fill_application(job, application, filler_class)
             
             # Check cancellation after fill
             if running_applications.get(job_id, {}).get("cancelled"):
                 print(f"   🛑 Application {job_id} cancelled - not updating status")
                 db.update_job_status(job_id, JobStatus.NEW)
                 return
             
             if success:
                 db.update_job_status(job_id, JobStatus.APPLIED)
             else:
                 # If it failed but wasn't marked rejected, mark failed
                 if job.status != JobStatus.REJECTED.value:
                     db.update_job_status(job_id, JobStatus.FAILED)
                     
        except asyncio.CancelledError:
            print(f"   🛑 Application {job_id} task was cancelled")
            db.update_job_status(job_id, JobStatus.NEW)
        except Exception as e:
            print(f"Single apply error: {e}")
            if not running_applications.get(job_id, {}).get("cancelled"):
                db.update_job_status(job_id, JobStatus.FAILED)
        finally:
            await orchestrator.teardown()
            running_applications.pop(job_id, None)

    background_tasks.add_task(run_single_apply)
    return {"status": "started", "job_id": job_id, "message": "Application process started"}


@app.post("/api/apply/{job_id}/abort", dependencies=[Depends(require_admin)])
async def abort_apply(job_id: str):
    """Abort an in-progress application"""
    global running_applications
    
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
    print(f"   🛑 Abort requested for job {job_id}")
    
    # Reset job status
    db.update_job_status(job_id, JobStatus.NEW)
    
    return {"status": "aborted", "job_id": job_id, "message": "Application abort requested"}


@app.get("/api/apply/{job_id}/status")
async def get_apply_status(job_id: str):
    """Get the status of an application process"""
    global running_applications
    
    is_running = job_id in running_applications and not running_applications[job_id].get("cancelled")
    started_at = running_applications.get(job_id, {}).get("started_at")
    
    return {
        "job_id": job_id,
        "is_running": is_running,
        "started_at": started_at.isoformat() if started_at else None
    }


@app.post("/api/run", dependencies=[Depends(require_admin)])
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


# ============ Cold Email API ============

class ContactCreate(BaseModel):
    name: str
    email: str
    title: Optional[str] = ""
    company: str
    linkedin_url: Optional[str] = None
    persona: Optional[str] = "unknown"
    job_id: Optional[str] = None
    notes: Optional[str] = None

class EmailCreate(BaseModel):
    contact_id: str
    job_id: Optional[str] = None
    template_id: Optional[str] = None
    subject: str
    body: str

class CampaignCreate(BaseModel):
    job_id: str
    max_contacts: int = 5
    personas: Optional[list[str]] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    persona: Optional[str] = None
    job_id: Optional[str] = None
    notes: Optional[str] = None


class EmailUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[str] = None


class RenderEmail(BaseModel):
    contact_id: str
    job_id: Optional[str] = None
    template_id: Optional[str] = None


@app.get("/api/contacts")
async def list_contacts(
    company: Optional[str] = None,
    search: Optional[str] = None,
    persona: Optional[str] = None,
    job_id: Optional[str] = None,
    limit: int = 100
):
    """Get all contacts with optional search and filters"""
    db = get_db()
    
    if search or job_id or persona:
        contacts = db.search_contacts(query=search, job_id=job_id, persona=persona, limit=limit)
    elif company:
        contacts = db.get_contacts_for_company(company, limit)
    else:
        contacts = db.get_all_contacts(limit)
    
    return {
        "total": len(contacts),
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "title": c.title,
                "company": c.company,
                "linkedin_url": c.linkedin_url,
                "persona": c.persona.value if hasattr(c.persona, 'value') else c.persona,
                "source": c.source.value if hasattr(c.source, 'value') else c.source,
                "job_id": c.job_id,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contacts
        ]
    }


@app.post("/api/contacts", dependencies=[Depends(require_admin)])
async def create_contact(contact_in: ContactCreate):
    """Add a new contact manually"""
    from src.core.cold_email_models import Contact, ContactPersona, ContactSource
    
    db = get_db()
    
    contact = Contact(
        name=contact_in.name,
        email=contact_in.email,
        title=contact_in.title or "",
        company=contact_in.company,
        linkedin_url=contact_in.linkedin_url,
        persona=ContactPersona(contact_in.persona) if contact_in.persona else ContactPersona.UNKNOWN,
        source=ContactSource.MANUAL,
        job_id=contact_in.job_id,
        notes=contact_in.notes,
    )
    
    contact_id = db.add_contact(contact)
    return {"id": contact_id, "success": True}


@app.patch("/api/contacts/{contact_id}", dependencies=[Depends(require_admin)])
async def update_contact(contact_id: str, update: ContactUpdate):
    """Update a contact"""
    db = get_db()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = db.update_contact_fields(contact_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"success": True}


@app.delete("/api/contacts/{contact_id}", dependencies=[Depends(require_admin)])
async def delete_contact(contact_id: str):
    """Delete a contact"""
    db = get_db()
    success = db.delete_contact(contact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"success": True}


@app.post("/api/contacts/scrape", dependencies=[Depends(require_admin)])
async def scrape_contacts(
    company: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    limit: int = Query(10),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Scrape contacts from Apollo for a company or job"""
    if not company and not job_id:
        raise HTTPException(status_code=400, detail="Either company or job_id must be provided")
    
    async def run_scrape():
        try:
            from src.scrapers.apollo_scraper import ApolloScraper
            
            db = get_db()
            target_company = company
            
            # If job_id provided, get company from job
            if job_id and not target_company:
                job = db.get_job(job_id)
                if not job:
                    print(f"   ❌ Job {job_id} not found")
                    return
                target_company = job.company
            
            if not target_company:
                print("   ❌ No company found to scrape")
                return
            
            scraper = ApolloScraper()
            contacts = await scraper.search_contacts(company=target_company, limit=limit)
            
            # Link contacts to job if job_id provided
            if job_id:
                for contact in contacts:
                    contact.job_id = job_id
            
            count = db.add_contacts_bulk(contacts)
            print(f"   ✅ Scraped {count} contacts for {target_company}" + (f" (linked to job {job_id})" if job_id else ""))
        except Exception as e:
            print(f"   ❌ Contact scrape error: {e}")
    
    background_tasks.add_task(run_scrape)
    return {"status": "started", "message": f"Scraping contacts for {company or 'job'}"}


@app.get("/api/emails")
async def list_emails(
    status: Optional[str] = None,
    search: Optional[str] = None,
    job_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    limit: int = 100
):
    """Get all cold emails with enriched contact info"""
    from src.core.cold_email_models import EmailStatus as ES
    
    db = get_db()
    
    if search or job_id or contact_id:
        emails = db.search_cold_emails(query=search, status=status, job_id=job_id, contact_id=contact_id, limit=limit)
    elif status:
        emails = db.get_cold_emails_by_status(ES(status), limit)
    else:
        emails = db.get_all_cold_emails(limit)
    
    # Enrich with contact info
    contact_cache: dict = {}
    enriched = []
    for e in emails:
        if e.contact_id and e.contact_id not in contact_cache:
            contact_cache[e.contact_id] = db.get_contact(e.contact_id)
        contact = contact_cache.get(e.contact_id)
        enriched.append({
            "id": e.id,
            "contact_id": e.contact_id,
            "contact_name": contact.name if contact else "Unknown",
            "contact_email": contact.email if contact else "",
            "contact_company": contact.company if contact else "",
            "job_id": e.job_id,
            "template_id": e.template_id,
            "subject": e.subject,
            "body": e.body,
            "status": e.status.value if hasattr(e.status, 'value') else e.status,
            "scheduled_at": e.scheduled_at.isoformat() if e.scheduled_at else None,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "followup_number": e.followup_number,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "error_message": e.error_message,
        })
    
    return {"total": len(enriched), "emails": enriched}


@app.post("/api/emails", dependencies=[Depends(require_admin)])
async def create_email(email_in: EmailCreate):
    """Create a new cold email"""
    from src.core.cold_email_models import ColdEmail, EmailStatus
    
    db = get_db()
    
    email = ColdEmail(
        contact_id=email_in.contact_id,
        job_id=email_in.job_id,
        template_id=email_in.template_id,
        subject=email_in.subject,
        body=email_in.body,
        status=EmailStatus.DRAFT,
    )
    
    email_id = db.add_cold_email(email)
    return {"id": email_id, "success": True}


@app.post("/api/emails/render", dependencies=[Depends(require_admin)])
async def render_email_preview(data: RenderEmail):
    """Render an email from template for preview (without saving)"""
    try:
        db = get_db()
        contact = db.get_contact(data.contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        if not data.template_id:
            return {"subject": "", "body": "", "template_name": None}
        
        from src.email.email_templates import TemplateManager, get_template_variables
        from src.email.email_personalizer import EmailPersonalizer
        
        manager = TemplateManager()
        template = manager.get_template(data.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        job = db.get_job(data.job_id) if data.job_id else None
        
        applicant = None
        try:
            from src.core.applicant import Applicant
            root_dir = Path(__file__).parent.parent.parent.parent
            profile_path = root_dir / "data" / "profile.json"
            if not profile_path.exists():
                profile_path = Path("data/profile.json")
            if profile_path.exists():
                applicant = Applicant.from_file(profile_path)
        except Exception as e:
            logger.warning(f"Could not load applicant profile: {e}")
            pass
        
        variables = get_template_variables(contact, job, applicant)
        personalizer = EmailPersonalizer()
        variables["personalized_hook"] = personalizer._get_fallback_hook(contact)
        
        subject, body = manager.render_template(template, variables)
        
        return {"subject": subject, "body": body, "template_name": template.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering email template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to render template: {str(e)}")


@app.get("/api/emails/{email_id}")
async def get_email(email_id: str):
    """Get a specific email"""
    db = get_db()
    email = db.get_cold_email(email_id)
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {
        "id": email.id,
        "contact_id": email.contact_id,
        "job_id": email.job_id,
        "subject": email.subject,
        "body": email.body,
        "status": email.status.value if hasattr(email.status, 'value') else email.status,
        "scheduled_at": email.scheduled_at.isoformat() if email.scheduled_at else None,
        "sent_at": email.sent_at.isoformat() if email.sent_at else None,
        "personalization_data": email.personalization_data,
    }


@app.patch("/api/emails/{email_id}", dependencies=[Depends(require_admin)])
async def update_email(email_id: str, update: EmailUpdate):
    """Update email fields (subject, body, status, scheduled_at)"""
    db = get_db()
    update_data: dict = {}
    if update.subject is not None:
        update_data["subject"] = update.subject
    if update.body is not None:
        update_data["body"] = update.body
    if update.status is not None:
        update_data["status"] = update.status
    if update.scheduled_at is not None:
        try:
            update_data["scheduled_at"] = datetime.fromisoformat(update.scheduled_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = db.update_cold_email_fields(email_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"success": True}


@app.delete("/api/emails/{email_id}", dependencies=[Depends(require_admin)])
async def delete_email(email_id: str):
    """Delete a cold email"""
    db = get_db()
    success = db.delete_cold_email(email_id)
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"success": True}


@app.post("/api/emails/{email_id}/send", dependencies=[Depends(require_admin)])
async def send_email_now(email_id: str, background_tasks: BackgroundTasks):
    """Send a specific email immediately"""
    
    async def run_send():
        try:
            from src.email.cold_email_service import get_cold_email_service
            service = get_cold_email_service()
            success = await service.send_email_now(email_id)
            print(f"   {'✅' if success else '❌'} Send email {email_id}: {'success' if success else 'failed'}")
        except Exception as e:
            print(f"   ❌ Send error: {e}")
    
    background_tasks.add_task(run_send)
    return {"status": "sending", "email_id": email_id}


@app.post("/api/emails/{email_id}/schedule", dependencies=[Depends(require_admin)])
async def schedule_email(email_id: str):
    """Schedule an email for optimal delivery time"""
    from src.email.email_scheduler import EmailScheduler
    from src.core.cold_email_models import EmailStatus
    
    db = get_db()
    email = db.get_cold_email(email_id)
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    scheduler = EmailScheduler()
    scheduled_time = scheduler.schedule_email(email)
    
    db.update_cold_email_status(email_id, EmailStatus.SCHEDULED)
    
    return {
        "success": True,
        "email_id": email_id,
        "scheduled_at": scheduled_time.isoformat()
    }


@app.get("/api/templates")
async def list_templates():
    """Get all email templates"""
    from src.email.email_templates import TemplateManager
    
    manager = TemplateManager()
    templates = manager.get_all_templates()
    
    return {
        "total": len(templates),
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "subject": t.subject,
                "persona_type": t.persona_type.value if t.persona_type else None,
                "is_followup": t.is_followup,
                "followup_day": t.followup_day,
            }
            for t in templates
        ]
    }


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template with full body"""
    from src.email.email_templates import TemplateManager
    
    manager = TemplateManager()
    template = manager.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "subject": template.subject,
        "body": template.body,
        "persona_type": template.persona_type.value if template.persona_type else None,
        "is_followup": template.is_followup,
        "followup_day": template.followup_day,
    }


@app.post("/api/campaigns", dependencies=[Depends(require_admin)])
async def create_campaign(campaign_in: CampaignCreate, background_tasks: BackgroundTasks):
    """Create a cold email campaign for a job"""
    
    async def run_campaign():
        try:
            from src.email.cold_email_service import get_cold_email_service
            from src.core.cold_email_models import ContactPersona
            
            db = get_db()
            job = db.get_job(campaign_in.job_id)
            
            if not job:
                print(f"   ❌ Job {campaign_in.job_id} not found")
                return
            
            personas = None
            if campaign_in.personas:
                personas = [ContactPersona(p) for p in campaign_in.personas]
            
            service = get_cold_email_service()
            result = await service.create_campaign_for_job(
                job=job,
                max_contacts=campaign_in.max_contacts,
                personas=personas
            )
            print(f"   ✅ Campaign created: {result}")
        except Exception as e:
            print(f"   ❌ Campaign error: {e}")
    
    background_tasks.add_task(run_campaign)
    return {"status": "started", "job_id": campaign_in.job_id}


@app.get("/api/email-stats")
async def get_email_stats():
    """Get cold email statistics"""
    db = get_db()
    stats = db.get_email_stats()
    
    return {
        "total_emails": stats["total"],
        "sent": stats["sent"],
        "opened": stats["opened"],
        "replied": stats["replied"],
        "scheduled": stats["scheduled"],
        "open_rate": round(stats["open_rate"], 1),
        "reply_rate": round(stats["reply_rate"], 1),
    }


@app.post("/api/emails/process", dependencies=[Depends(require_admin)])
async def process_scheduled_emails(background_tasks: BackgroundTasks):
    """Process all scheduled emails that are due"""
    
    async def run_process():
        try:
            from src.email.cold_email_service import get_cold_email_service
            service = get_cold_email_service()
            result = await service.process_scheduled()
            print(f"   ✅ Processed emails: {result}")
        except Exception as e:
            print(f"   ❌ Process error: {e}")
    
    background_tasks.add_task(run_process)
    return {"status": "started", "message": "Processing scheduled emails"}


# ============ Emails Page ============

@app.get("/emails", response_class=HTMLResponse)
async def emails_page(request: Request):
    return templates.TemplateResponse("emails.html", {"request": request, "page": "emails"})


def run_dashboard(host: str = "127.0.0.1", port: int = 8080):
    import uvicorn
    print(f"\n🚀 Starting PaperPlane API at http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
