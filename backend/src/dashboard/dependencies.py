"""Shared FastAPI dependencies — admin authentication.

If ADMIN_TOKEN is unset (the default), the API runs in open "dev mode" with no
auth. When set, write endpoints require a matching Bearer token.
"""
import os
from typing import Optional

from fastapi import Header, HTTPException

# Importing config has the side effect of loading the repo-root .env, so
# ADMIN_TOKEN is populated before we read it here.
from src.utils.config import get_settings  # noqa: F401

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
