"""
Base notifier class
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class NotificationPriority(str, Enum):
    LOW = "low"      # Daily summaries
    NORMAL = "normal"  # Completed applications
    HIGH = "high"    # Needs review
    URGENT = "urgent"  # Errors/failures


@dataclass
class Notification:
    """Notification data"""
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    url: Optional[str] = None
    tags: list[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class BaseNotifier(ABC):
    """Abstract base class for notification services"""
    
    SERVICE_NAME = "Base"
    
    def __init__(self):
        pass
    
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """
        Send a notification.
        
        Returns:
            True if sent successfully
        """
        pass
    
    async def notify_needs_review(
        self,
        job_title: str,
        company: str,
        reason: str,
        url: str = ""
    ) -> bool:
        """Send a notification that an application needs review"""
        return await self.send(Notification(
            title=f"🔔 Review Needed: {company}",
            message=f"**{job_title}** at **{company}**\n\nReason: {reason}",
            priority=NotificationPriority.HIGH,
            url=url,
            tags=["needs_review", company.lower().replace(" ", "_")]
        ))
    
    async def notify_completed(
        self,
        job_title: str,
        company: str,
        url: str = ""
    ) -> bool:
        """Send a notification that an application was completed"""
        return await self.send(Notification(
            title=f"✅ Applied: {company}",
            message=f"Successfully applied to **{job_title}** at **{company}**",
            priority=NotificationPriority.NORMAL,
            url=url,
            tags=["completed"]
        ))
    
    async def notify_failed(
        self,
        job_title: str,
        company: str,
        error: str
    ) -> bool:
        """Send a notification that an application failed"""
        return await self.send(Notification(
            title=f"❌ Failed: {company}",
            message=f"Failed to apply to **{job_title}** at **{company}**\n\nError: {error}",
            priority=NotificationPriority.HIGH,
            tags=["failed", "error"]
        ))
    
    async def notify_daily_summary(
        self,
        applied: int,
        pending: int,
        failed: int,
        needs_review: int
    ) -> bool:
        """Send daily summary notification"""
        return await self.send(Notification(
            title="📊 Daily Summary",
            message=(
                f"**Today's Results:**\n"
                f"✅ Applied: {applied}\n"
                f"⏳ Pending: {pending}\n"
                f"❌ Failed: {failed}\n"
                f"🔔 Needs Review: {needs_review}"
            ),
            priority=NotificationPriority.LOW,
            tags=["summary", "daily"]
        ))
