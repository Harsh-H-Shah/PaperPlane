"""
Email Sender - Sends cold emails via SMTP.
Uses existing SMTP configuration and handles rate limiting.
"""
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime
from typing import Optional

from src.core.cold_email_models import ColdEmail, Contact, EmailStatus
from src.utils.database import get_db
from src.utils.config import get_settings


class EmailSender:
    """Sends cold emails via SMTP"""
    
    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()
        
        # SMTP configuration
        self.smtp_host = self.settings.smtp_host or "smtp.gmail.com"
        self.smtp_port = self.settings.smtp_port or 587
        self.smtp_user = self.settings.smtp_user
        self.smtp_password = self.settings.smtp_password
        
        # Sender info
        self.sender_name = getattr(self.settings, 'sender_name', self.smtp_user)
        self.sender_email = self.smtp_user
        
        self.enabled = bool(self.smtp_user and self.smtp_password)
        
        if not self.enabled:
            print("   ⚠️ EmailSender: SMTP not configured. Set SMTP_USER and SMTP_PASSWORD in .env")
    
    async def send(
        self,
        email: ColdEmail,
        contact: Contact = None
    ) -> bool:
        """
        Send a single cold email.
        Returns True if sent successfully.
        """
        if not self.enabled:
            print("   ❌ EmailSender: SMTP not configured")
            return False
        
        # Get contact if not provided
        if not contact:
            contact = self.db.get_contact(email.contact_id)
            if not contact:
                self.db.update_cold_email_status(
                    email.id, 
                    EmailStatus.FAILED,
                    "Contact not found"
                )
                return False
        
        try:
            # Build email
            msg = self._build_message(email, contact)
            
            # Send via SMTP
            await self._send_smtp(msg, contact.email)
            
            # Update status
            self.db.update_cold_email_status(email.id, EmailStatus.SENT)
            
            print(f"   ✉️ Sent email to {contact.email}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Failed to send to {contact.email}: {error_msg}")
            self.db.update_cold_email_status(
                email.id, 
                EmailStatus.FAILED,
                error_msg
            )
            return False
    
    def _build_message(
        self,
        email: ColdEmail,
        contact: Contact
    ) -> MIMEMultipart:
        """Build the email message"""
        
        msg = MIMEMultipart("alternative")
        
        # Headers
        msg["Subject"] = email.subject
        msg["From"] = formataddr((self.sender_name, self.sender_email))
        msg["To"] = formataddr((contact.name, contact.email))
        msg["Reply-To"] = self.sender_email
        
        # Add tracking header (could be expanded)
        msg["X-Cold-Email-ID"] = email.id
        
        # Body - both plain text and HTML
        text_part = MIMEText(email.body, "plain", "utf-8")
        html_body = self._text_to_html(email.body)
        html_part = MIMEText(html_body, "html", "utf-8")
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        return msg
    
    def _text_to_html(self, text: str) -> str:
        """Convert plain text to basic HTML"""
        # Escape HTML characters
        html = text.replace("&", "&amp;")
        html = html.replace("<", "&lt;")
        html = html.replace(">", "&gt;")
        
        # Convert newlines to breaks
        html = html.replace("\n\n", "</p><p>")
        html = html.replace("\n", "<br>")
        
        # Wrap in HTML
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; }}
        p {{ margin: 0 0 1em 0; }}
    </style>
</head>
<body>
    <p>{html}</p>
</body>
</html>"""
    
    async def _send_smtp(self, msg: MIMEMultipart, to_email: str):
        """Send email via SMTP"""
        # Run in thread pool since smtplib is blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._send_smtp_sync,
            msg,
            to_email
        )
    
    def _send_smtp_sync(self, msg: MIMEMultipart, to_email: str):
        """Synchronous SMTP send"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(
                self.sender_email,
                to_email,
                msg.as_string()
            )
    
    async def send_batch(
        self,
        emails: list[ColdEmail],
        delay_seconds: int = 120
    ) -> dict:
        """
        Send a batch of emails with delays between them.
        Returns stats dict.
        """
        stats = {
            "total": len(emails),
            "sent": 0,
            "failed": 0,
        }
        
        for email in emails:
            success = await self.send(email)
            
            if success:
                stats["sent"] += 1
            else:
                stats["failed"] += 1
            
            # Delay between emails (except for last one)
            if email != emails[-1]:
                await asyncio.sleep(delay_seconds)
        
        return stats
    
    async def process_pending(self) -> dict:
        """Process all pending scheduled emails"""
        pending = self.db.get_pending_emails()
        
        if not pending:
            return {"total": 0, "sent": 0, "failed": 0}
        
        print(f"   📬 Processing {len(pending)} pending emails...")
        
        return await self.send_batch(pending)
    
    def test_connection(self) -> bool:
        """Test SMTP connection"""
        if not self.enabled:
            return False
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                return True
        except Exception as e:
            print(f"   ❌ SMTP test failed: {e}")
            return False
