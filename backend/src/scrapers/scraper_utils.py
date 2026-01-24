
import asyncio
import httpx
import random
import re
from datetime import datetime, timedelta
from typing import Optional, TypeVar, Callable, Any
from dataclasses import dataclass, field


T = TypeVar('T')


def parse_date_string(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # 1. Try generic ISO formats
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            return datetime.strptime(date_str.split('+')[0], fmt)
        except ValueError:
            continue
            
    # 2. Try Relative Dates ("2 days ago", "1 month ago")
    now = datetime.now()
    try:
        if "ago" in date_str.lower():
            value_match = re.search(r'(\d+)', date_str)
            if not value_match:
                return None
            
            value = int(value_match.group(1))
            date_low = date_str.lower()
            
            if "minute" in date_low:
                return now - timedelta(minutes=value)
            elif "hour" in date_low:
                return now - timedelta(hours=value)
            elif "day" in date_low:
                return now - timedelta(days=value)
            elif "week" in date_low:
                return now - timedelta(weeks=value)
            elif "month" in date_low:
                return now - timedelta(days=value * 30)
            elif "year" in date_low:
                return now - timedelta(days=value * 365)
                
    except Exception:
        pass
        
    return None

@dataclass
class ScrapeResult:
    success: bool
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_filtered: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    retries: int = 0


@dataclass
class ScraperMetrics:
    source: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_jobs_found: int = 0
    total_jobs_saved: int = 0
    avg_duration: float = 0.0
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    run_history: list[dict] = field(default_factory=list)
    
    def record_run(self, result: ScrapeResult):
        self.total_runs += 1
        self.last_run = datetime.now()
        
        if result.success:
            self.successful_runs += 1
            self.total_jobs_found += result.jobs_found
            self.total_jobs_saved += result.jobs_new
        else:
            self.failed_runs += 1
            self.last_error = result.error
        
        durations = [r["duration"] for r in self.run_history[-10:]] + [result.duration_seconds]
        self.avg_duration = sum(durations) / len(durations)
        
        self.run_history.append({
            "timestamp": self.last_run.isoformat(),
            "success": result.success,
            "jobs_found": result.jobs_found,
            "jobs_new": result.jobs_new,
            "duration": result.duration_seconds,
            "error": result.error
        })
        
        self.run_history = self.run_history[-50:]
    
    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs
    
    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": f"{self.success_rate:.1%}",
            "total_jobs_found": self.total_jobs_found,
            "total_jobs_saved": self.total_jobs_saved,
            "avg_duration": f"{self.avg_duration:.2f}s",
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_error": self.last_error,
        }


class RetryConfig:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0, exponential: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential
    
    def get_delay(self, attempt: int) -> float:
        if self.exponential:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay * (attempt + 1)
        
        jitter = random.uniform(0, delay * 0.1)
        return min(delay + jitter, self.max_delay)


async def retry_async(func: Callable[..., T], config: RetryConfig = None, *args, **kwargs) -> tuple[T, int]:
    config = config or RetryConfig()
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            return result, attempt
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
            last_exception = e
            if attempt < config.max_retries:
                delay = config.get_delay(attempt)
                await asyncio.sleep(delay)
    
    raise last_exception


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30, requests_per_hour: int = 200):
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.minute_requests: list[datetime] = []
        self.hour_requests: list[datetime] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        async with self._lock:
            now = datetime.now()
            
            self.minute_requests = [t for t in self.minute_requests if (now - t).seconds < 60]
            self.hour_requests = [t for t in self.hour_requests if (now - t).seconds < 3600]
            
            if len(self.minute_requests) >= self.rpm:
                wait_time = 60 - (now - self.minute_requests[0]).seconds
                await asyncio.sleep(wait_time + 0.1)
            
            if len(self.hour_requests) >= self.rph:
                wait_time = 3600 - (now - self.hour_requests[0]).seconds
                await asyncio.sleep(min(wait_time + 0.1, 300))
            
            self.minute_requests.append(now)
            self.hour_requests.append(now)
    
    def get_stats(self) -> dict:
        now = datetime.now()
        minute_requests = len([t for t in self.minute_requests if (now - t).seconds < 60])
        hour_requests = len([t for t in self.hour_requests if (now - t).seconds < 3600])
        
        return {
            "minute_requests": minute_requests,
            "minute_limit": self.rpm,
            "hour_requests": hour_requests,
            "hour_limit": self.rph,
        }


_metrics: dict[str, ScraperMetrics] = {}
_rate_limiters: dict[str, RateLimiter] = {}


def get_metrics(source: str) -> ScraperMetrics:
    if source not in _metrics:
        _metrics[source] = ScraperMetrics(source=source)
    return _metrics[source]


def get_rate_limiter(source: str) -> RateLimiter:
    if source not in _rate_limiters:
        _rate_limiters[source] = RateLimiter()
    return _rate_limiters[source]


def get_all_metrics() -> dict:
    return {source: m.to_dict() for source, m in _metrics.items()}
