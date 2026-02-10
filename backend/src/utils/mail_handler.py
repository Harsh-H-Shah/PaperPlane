import imaplib
import email
import re
from email.header import decode_header

from typing import Optional

from src.utils.config import get_settings

class MailHandler:
    def __init__(self):
        self.settings = get_settings()
        
        # Try specific IMAP credentials first
        self.username = self.settings.email_user
        self.password = self.settings.email_password
        
        # Fallback to SMTP credentials if IMAP ones are missing or placeholders
        if not self.username or "your_email" in self.username:
            if self.settings.smtp_user:
                print(f"📧 MailHandler: Using SMTP credentials for IMAP (User: {self.settings.smtp_user})")
                self.username = self.settings.smtp_user
                self.password = self.settings.smtp_password
        
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993

    def get_verification_code(self, subject_filter: str = "Greenhouse", timeframe_minutes: int = 5) -> Optional[str]:
        """
        Connects to IMAP, searches for recent emails with 'subject_filter' in subject,
        and extracts a 6-digit verification code.
        """
        if not self.username or not self.password:
            print("⚠️ MailHandler: Email credentials (EMAIL_USER) not set.")
            return None

        try:
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.username, self.password)
            mail.select("inbox")

            # Search for emails
            # Since date searching in IMAP is day-based, we'll fetch recent few and filter in python
            status, messages = mail.search(None, "ALL")
            if status != "OK":
                return None

            message_ids = messages[0].split()
            # Look at last 10 messages
            recent_ids = message_ids[-10:] if len(message_ids) > 10 else message_ids
            
            for msg_id in reversed(recent_ids):
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Decode Subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                
                # Check Subject OR Sender Match
                sender = msg.get("From", "")
                if subject_filter.lower() not in subject.lower() and subject_filter.lower() not in sender.lower():
                    continue

                # Check Date Match (Safety check)
                # date_tuple = email.utils.parsedate_tz(msg["Date"])
                # if date_tuple:
                #    date_obj = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                #    if datetime.now(date_obj.tzinfo) - date_obj > timedelta(minutes=timeframe_minutes):
                #        continue

                print(f"📧 MailHandler: Found matching email: '{subject}'")

                # Parse Body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True).decode()
                                break
                            elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                                body = part.get_payload(decode=True).decode()
                        except Exception:
                            pass
                else:
                    body = msg.get_payload(decode=True).decode()

                # Extract Code (assuming 6 digits)
                # Look for patterns like "verification code is 123456" or just isolated 6 digits
                
                # Pattern 1: Explicit "code is" or similar
                # Pattern 2: Just 6 digits isolated
                
                # Pattern 1: Alphanumeric code (Greenhouse often uses mixture of letters/numbers)
                # Context from screenshot: "Copy and paste this code into the security code field..."
                # Value: "ugHJ9pif" (8 chars)
                
                # Robust extraction: Look for the code line in HTML or Text
                # We often see it isolated or after "code:"
                
                # Regex for 6-12 char alphanumeric code that is NOT a common word
                # We'll look for lines that look like codes
                
                # Try specific Greenhouse patterns first
                patterns = [
                    r"<h1>([A-Za-z0-9]{6,12})</h1>", # New HTML pattern
                    r"security code field on your application:\s*<br>\s*<strong>([A-Za-z0-9]{6,12})</strong>", # HTML bold
                    r"security code field on your application:\s*([A-Za-z0-9]{6,12})", # Text
                    r"verification code is:?\s*([A-Za-z0-9]{6,12})", 
                    r"security code:?\s*([A-Za-z0-9]{6,12})",
                    r"code\s*:?\s*([A-Za-z0-9]{6,12})" # Generic fallback
                ]
                
                code = None
                for pattern in patterns:
                    match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
                    if match:
                        code = match.group(1)
                        break
                
                # Fallback: Look for the specific isolated line style if regex fails
                if not code:
                     # Find lines that are just alphanumerics
                     lines = body.replace("<br>", "\n").replace("<div>", "\n").split("\n")
                     for line in lines:
                         cleaned = line.strip()
                         if 6 <= len(cleaned) <= 12 and cleaned.isalnum() and not cleaned.isalpha(): # Mixed numbers/letters usually
                             # Heuristic: Uppercase mixed often indicates code
                             if any(c.isdigit() for c in cleaned):
                                 code = cleaned
                                 break
                
                if code:
                    print(f"✅ MailHandler: Extracted Code: {code}")
                    mail.logout()
                    return code
            
            mail.logout()
            print("⚠️ MailHandler: No code found in recent emails.")
            return None

        except Exception as e:
            print(f"❌ MailHandler Error: {e}")
            return None
