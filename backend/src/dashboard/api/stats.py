"""Read-only dashboard data: stats, gamification, quests, combat history,
activity log and LLM usage."""
from datetime import datetime, timedelta

from fastapi import APIRouter

from src.utils.database import get_db
from src.utils.config import get_settings
from src.utils.logger import logger  # noqa: F401  (kept for parity / future use)
from src.utils import paths
from src.core.job import JobStatus
from src.dashboard.services.gamification import (
    XP_REWARDS,
    get_rank_info,
    calculate_streak,
    get_applications_today,
)

router = APIRouter()


@router.get("/api/stats")
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


@router.get("/api/gamification")
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
        "level": rank_info["tier_index"],  # Use tier index as level
        "level_title": rank_info["rank_title"],
        "current_xp_in_level": rank_info["current_rr"],  # Use RR as XP in level
        "xp_for_next_level": rank_info["rr_for_next_rank"],
        "rank_icon": rank_info["rank_icon"],  # New field
        "streak": streak,
        "applications_today": get_applications_today(db),
    }


@router.get("/api/quests")
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


@router.get("/api/combat-history")
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


@router.get("/api/activity")
async def get_activity_log(lines: int = 50):
    """Get recent activity logs from in-memory buffer or log file"""
    # Primary: read from in-memory ring buffer (always works)
    from src.utils.logger import memory_handler
    mem_logs = memory_handler.get_logs(lines)
    if mem_logs:
        return {"logs": mem_logs}

    # Fallback: try reading from log file
    log_path = paths.activity_log()

    if not log_path.exists():
        return {"logs": []}

    try:
        with open(log_path, "r") as f:
            all_lines = f.readlines()
            all_lines = [line.strip() for line in all_lines if line.strip()]
            return {"logs": all_lines[-lines:]}
    except Exception as e:
        return {"logs": [f"Error reading log: {str(e)}"]}


@router.get("/api/llm-usage")
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
