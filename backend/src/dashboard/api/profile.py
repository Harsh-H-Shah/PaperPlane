"""Agent profile: read (profile.json + valorant_agent preference) and update."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from src.utils.database import get_db
from src.utils import paths
from src.dashboard.dependencies import is_admin, require_admin
from src.dashboard.schemas import ProfileUpdate

router = APIRouter()


@router.get("/api/profile")
async def get_profile(authorization: Optional[str] = Header(None)):
    """Get agent profile - combines profile.json with SQLite preferences.
    Non-admin users get redacted profile data."""
    from src.utils.database import UserPreferencesModel

    admin = is_admin(authorization)

    profile_path = paths.profile_path()

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


@router.patch("/api/profile", dependencies=[Depends(require_admin)])
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
