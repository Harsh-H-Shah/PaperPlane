import asyncio
from datetime import datetime
from typing import Optional

from src.scrapers.aggregator import JobAggregator
from src.utils.config import get_settings
from src.utils.database import get_db


class JobScheduler:
    def __init__(self, interval_hours: float = 3.0):
        self.interval_hours = interval_hours
        self.settings = get_settings()
        self.db = get_db()
        self.aggregator = JobAggregator()
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.total_jobs_found = 0
        self.total_jobs_new = 0
    
    async def start(self):
        if self.running:
            print("⚠️ Scheduler already running")
            return
        
        self.running = True
        print(f"🚀 Starting job scheduler (interval: {self.interval_hours}h)")
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("⏹️ Scheduler stopped")
    
    async def _run_loop(self):
        while self.running:
            try:
                await self._run_once()
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
            
            await asyncio.sleep(self.interval_hours * 3600)
    
    async def _run_once(self):
        self.run_count += 1
        self.last_run = datetime.now()
        
        print(f"\n{'='*50}")
        print(f"🔍 Scheduler run #{self.run_count} at {self.last_run.strftime('%H:%M:%S')}")
        print(f"{'='*50}")
        
        try:
            result = await self.aggregator.scrape_all(limit_per_source=100)
            stats = result["stats"]
            
            self.total_jobs_found += stats["total_found"]
            self.total_jobs_new += stats["total_new"]
            
            print(f"\n📊 Run #{self.run_count} Results:")
            print(f"   Found: {stats['total_found']} jobs")
            print(f"   New: {stats['total_new']} jobs")
            print(f"   Duplicates: {stats['duplicates_removed']}")
            
            for source in stats["sources"]:
                status = "✅" if not source.get("error") else "❌"
                print(f"   {status} {source['name']}: {source['found']} found")
            
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
    
    async def run_once(self):
        await self._run_once()
    
    def get_stats(self) -> dict:
        return {
            "running": self.running,
            "interval_hours": self.interval_hours,
            "run_count": self.run_count,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "total_jobs_found": self.total_jobs_found,
            "total_jobs_new": self.total_jobs_new,
        }


_scheduler: Optional[JobScheduler] = None


def get_scheduler(interval_hours: float = 3.0) -> JobScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler(interval_hours)
    return _scheduler


async def run_scrape_once(limit: int = 100) -> dict:
    scheduler = get_scheduler()
    await scheduler.run_once()
    return scheduler.get_stats()


async def start_scheduler(interval_hours: float = 3.0):
    scheduler = get_scheduler(interval_hours)
    await scheduler.start()
    
    try:
        while scheduler.running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await scheduler.stop()
