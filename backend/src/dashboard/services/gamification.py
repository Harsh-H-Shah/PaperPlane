"""Gamification logic: XP, Valorant-style ranks, streaks, daily counts.

Pure helpers used by the stats endpoints. The numbers are user-visible and have
no spec beyond this code, so keep the math here as the single source of truth.
"""
from datetime import datetime, timedelta

from src.core.job import JobStatus

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
                    return 0  # Streak broken
            else:
                expected_next = current_check_date - timedelta(days=1)
                if date_obj == expected_next:
                    streak += 1
                    current_check_date = expected_next
                else:
                    break

        return streak


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
