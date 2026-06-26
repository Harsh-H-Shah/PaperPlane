"""Scraper status + triggering a scrape run (progress tracked in state.SCRAPE_STATUS)."""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends

from src.utils.config import get_settings
from src.utils.logger import logger
from src.dashboard.dependencies import require_admin
from src.dashboard.schemas import ScrapeRequest
from src.dashboard.state import SCRAPE_STATUS

router = APIRouter()


@router.get("/api/scrapers/status")
async def get_scraper_status():
    settings = get_settings()

    # Mirrors the scrapers actually registered in JobAggregator._setup_scrapers.
    # Simplify and CVRVE are gated by config flags; the rest are always on.
    scrapers = [
        {"name": "Simplify", "enabled": settings.scrapers.simplify.enabled, "configured": True, "icon": "📦"},
        {"name": "CVRVE", "enabled": settings.scrapers.cvrve.enabled, "configured": True, "icon": "🎯"},
        {"name": "Jobright", "enabled": True, "configured": True, "icon": "🚀"},
        {"name": "BuiltIn", "enabled": True, "configured": True, "icon": "🏗️"},
        {"name": "Careerjet", "enabled": True, "configured": True, "icon": "🔎"},
        {"name": "GreenhouseJobs", "enabled": True, "configured": True, "icon": "🌱"},
    ]

    return {"scrapers": scrapers}


@router.get("/api/scrape/progress")
async def get_scrape_progress():
    return SCRAPE_STATUS


@router.post("/api/scrape", dependencies=[Depends(require_admin)])
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    if SCRAPE_STATUS["is_running"]:
        return {"status": "error", "message": "Scrape already in progress"}

    async def run_scrape_wrapper():
        SCRAPE_STATUS["is_running"] = True
        SCRAPE_STATUS["jobs_found"] = 0
        SCRAPE_STATUS["jobs_new"] = 0
        SCRAPE_STATUS["errors"] = []
        SCRAPE_STATUS["last_updated"] = datetime.now()

        try:
            from src.scrapers.aggregator import JobAggregator

            # Run manually to update progress
            agg = JobAggregator(validate_links=True)

            sources = request.sources or [s.SOURCE_NAME.lower() for s in agg.scrapers]
            logger.info(f"🔍 Starting scrape for sources: {sources}")

            for source in sources:
                SCRAPE_STATUS["current_source"] = source
                SCRAPE_STATUS["last_updated"] = datetime.now()
                logger.info(f"🔍 Scraping source: {source}")

                try:
                    jobs, raw_count = await agg.scrape_source(source, limit=request.limit)
                    SCRAPE_STATUS["jobs_found"] += raw_count
                    SCRAPE_STATUS["jobs_new"] += len(jobs)
                    logger.info(f"✅ {source} -> found={raw_count}, new={len(jobs)}")
                except Exception as e:
                    error_msg = f"{source}: {str(e)}"

                    logger.error(f"Scrape error {error_msg}")
                    SCRAPE_STATUS["errors"].append(error_msg)

            SCRAPE_STATUS["current_source"] = "Done"

        except Exception as e:

            logger.error(f"CRITICAL SCRAPE ERROR: {e}")
            SCRAPE_STATUS["errors"].append(f"CRITICAL: {str(e)}")
        finally:
            SCRAPE_STATUS["is_running"] = False
            SCRAPE_STATUS["current_source"] = ""

    background_tasks.add_task(run_scrape_wrapper)
    return {"status": "started", "message": "Scraping started"}
