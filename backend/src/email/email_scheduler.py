"""
Email Scheduler - Schedules emails for optimal business hours.
Handles timezone awareness and spreading emails throughout the day.
"""
from datetime import datetime, timedelta
from typing import Optional
import random

from src.core.cold_email_models import ColdEmail, Contact, EmailStatus
from src.utils.database import get_db
from src.utils.config import get_settings


class EmailScheduler:
    """Schedules cold emails for optimal delivery times"""
    
    # Optimal sending hours (9-11 AM is peak open rate)
    OPTIMAL_HOURS_START = 9   # 9 AM
    OPTIMAL_HOURS_END = 11    # 11 AM
    
    # Extended hours for spreading load
    EXTENDED_HOURS_START = 8  # 8 AM
    EXTENDED_HOURS_END = 17   # 5 PM
    
    # Business days (Monday=0, Sunday=6)
    BUSINESS_DAYS = (0, 1, 2, 3, 4)  # Mon-Fri
    
    # Follow-up schedules
    FOLLOWUP_DELAYS = {
        1: 3,   # First followup: 3 days
        2: 7,   # Second followup: 7 days (from original)
        3: 14,  # Third followup: 14 days (from original)
    }
    
    def __init__(self):
        self.db = get_db()
        self.settings = get_settings()
        
        # Daily sending limit from config or default
        self.daily_limit = int(getattr(
            self.settings, 'cold_email_daily_limit', 50
        ))
        
        # Minimum delay between emails (seconds)
        self.min_delay = int(getattr(
            self.settings, 'cold_email_delay_seconds', 120
        ))
    
    def schedule_email(
        self,
        email: ColdEmail,
        contact: Contact = None,
        preferred_hour: int = None
    ) -> datetime:
        """
        Schedule an email for optimal delivery time.
        Returns the scheduled datetime.
        """
        now = datetime.now()
        
        # Start with next business day/hour
        scheduled = self._get_next_business_slot(now, preferred_hour)
        
        # Add jitter to spread emails (0-30 min random)
        jitter_minutes = random.randint(0, 30)
        scheduled = scheduled + timedelta(minutes=jitter_minutes)
        
        # Update email status
        email.scheduled_at = scheduled
        email.status = EmailStatus.SCHEDULED
        
        return scheduled
    
    def schedule_followup(
        self,
        original_email_id: str,
        followup_number: int = 1
    ) -> Optional[ColdEmail]:
        """
        Schedule a follow-up email based on the original.
        Returns the new ColdEmail if scheduled, None if already exists.
        """
        original = self.db.get_cold_email(original_email_id)
        if not original:
            return None
        
        # Get delay in days
        delay_days = self.FOLLOWUP_DELAYS.get(followup_number, 7)
        
        # Calculate follow-up time
        base_time = original.sent_at or original.scheduled_at or datetime.now()
        followup_time = base_time + timedelta(days=delay_days)
        
        # Adjust to next business slot
        followup_time = self._get_next_business_slot(followup_time)
        
        # Create follow-up email
        followup = ColdEmail(
            contact_id=original.contact_id,
            job_id=original.job_id,
            template_id=f"followup_{followup_number}",
            subject=f"Re: {original.subject}",
            body="",  # Will be filled by template
            status=EmailStatus.SCHEDULED,
            scheduled_at=followup_time,
            parent_email_id=original_email_id,
            followup_number=followup_number,
            personalization_data=original.personalization_data,
        )
        
        return followup
    
    def _get_next_business_slot(
        self,
        from_time: datetime,
        preferred_hour: int = None
    ) -> datetime:
        """Get the next available business hour slot"""
        
        current = from_time
        
        # If preferred hour specified, try to use it
        target_hour = preferred_hour or random.randint(
            self.OPTIMAL_HOURS_START,
            self.OPTIMAL_HOURS_END
        )
        
        # If current time is past today's window, move to tomorrow
        if current.hour >= self.EXTENDED_HOURS_END:
            current = current + timedelta(days=1)
            current = current.replace(
                hour=target_hour,
                minute=0,
                second=0,
                microsecond=0
            )
        elif current.hour < self.EXTENDED_HOURS_START:
            current = current.replace(
                hour=target_hour,
                minute=0,
                second=0,
                microsecond=0
            )
        
        # Move to next business day if weekend
        while current.weekday() not in self.BUSINESS_DAYS:
            current = current + timedelta(days=1)
        
        # Set to target hour if not already set
        if current.hour < self.EXTENDED_HOURS_START or current.hour >= self.EXTENDED_HOURS_END:
            current = current.replace(hour=target_hour) 
        
        return current
    
    def get_pending_emails(self, limit: int = 50) -> list[ColdEmail]:
        """Get emails that are due to be sent"""
        return self.db.get_pending_emails(limit)
    
    def get_scheduled_count_today(self) -> int:
        """Get number of emails scheduled/sent today"""
        today_start = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        all_emails = self.db.get_cold_emails_by_status(EmailStatus.SCHEDULED)
        all_emails += self.db.get_cold_emails_by_status(EmailStatus.SENT)
        
        return sum(
            1 for e in all_emails 
            if e.scheduled_at and e.scheduled_at >= today_start
        )
    
    def can_send_more_today(self) -> bool:
        """Check if we're under the daily limit"""
        return self.get_scheduled_count_today() < self.daily_limit
    
    def get_next_available_slot(self) -> datetime:
        """Get the next available slot considering limits"""
        now = datetime.now()
        
        if self.can_send_more_today():
            return self._get_next_business_slot(now)
        else:
            # Move to tomorrow
            tomorrow = now + timedelta(days=1)
            return self._get_next_business_slot(tomorrow)
    
    def schedule_batch(
        self,
        emails: list[ColdEmail],
        spread_hours: int = 4
    ) -> list[ColdEmail]:
        """
        Schedule a batch of emails, spreading them over hours.
        Returns list of scheduled emails.
        """
        if not emails:
            return []
        
        scheduled = []
        base_time = self.get_next_available_slot()
        
        # Calculate interval in minutes
        if len(emails) > 1:
            interval_minutes = (spread_hours * 60) // (len(emails) - 1)
        else:
            interval_minutes = 0
        
        for i, email in enumerate(emails):
            # Add time offset
            offset = timedelta(minutes=interval_minutes * i)
            email.scheduled_at = base_time + offset
            email.status = EmailStatus.SCHEDULED
            
            # Adjust if past business hours
            while (email.scheduled_at.hour >= self.EXTENDED_HOURS_END or
                   email.scheduled_at.weekday() not in self.BUSINESS_DAYS):
                email.scheduled_at = self._get_next_business_slot(
                    email.scheduled_at + timedelta(hours=1)
                )
            
            # Save to database
            self.db.add_cold_email(email)
            scheduled.append(email)
        
        return scheduled
