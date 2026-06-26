"""Auth endpoints: token verification + whether auth is enabled."""
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from src.dashboard.dependencies import ADMIN_TOKEN, get_token_from_header

router = APIRouter()


@router.post("/api/auth/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify if the provided token is valid."""
    if not ADMIN_TOKEN:
        return {"authenticated": True, "message": "No auth configured"}
    token = get_token_from_header(authorization)
    if token == ADMIN_TOKEN:
        return {"authenticated": True}
    raise HTTPException(status_code=403, detail="Invalid token")


@router.get("/api/auth/status")
async def auth_status():
    """Check if auth is enabled (no token needed)."""
    return {"auth_required": bool(ADMIN_TOKEN)}
