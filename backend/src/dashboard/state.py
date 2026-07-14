"""In-process mutable state shared across routers.

These are module-level singletons on purpose: the apply endpoints and the scrape
endpoints track progress here so that separate requests (e.g. trigger vs. poll
vs. abort) see the same state. Import the module and mutate its attributes —
do not copy these dicts into other modules.
"""
from typing import Dict

# job_id -> {"cancelled": bool, "started_at": datetime}
running_applications: Dict[str, dict] = {}

# Progress for the most recent /api/scrape run.
SCRAPE_STATUS = {
    "is_running": False,
    "current_source": "",
    "jobs_found": 0,
    "jobs_new": 0,
    "last_updated": None,
    "errors": [],
}
