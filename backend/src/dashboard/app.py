"""FastAPI application assembly.

This module wires the app together; the actual endpoints live in domain routers
under src/dashboard/api/. To add an endpoint, edit (or add) a router there and
include it below — keep this file thin.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from src.dashboard.api import (
    auth,
    stats,
    jobs,
    scraping,
    applications,
    profile,
    email,
)

app = FastAPI(title="PaperPlane API", version="2.0.0")

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://paperplane.harsh.software"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ API routers ============
app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(jobs.router)
app.include_router(scraping.router)
app.include_router(applications.router)
app.include_router(profile.router)
app.include_router(email.router)


# ============ Legacy server-rendered pages (Jinja) ============
# The primary UI is the Next.js frontend; these template pages predate it.
DASHBOARD_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "page": "dashboard"})


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request):
    return templates.TemplateResponse("jobs.html", {"request": request, "page": "jobs"})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "page": "settings"})


@app.get("/emails", response_class=HTMLResponse)
async def emails_page(request: Request):
    return templates.TemplateResponse("emails.html", {"request": request, "page": "emails"})


def run_dashboard(host: str = "127.0.0.1", port: int = 8080):
    import uvicorn
    print(f"\n🚀 Starting PaperPlane API at http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
