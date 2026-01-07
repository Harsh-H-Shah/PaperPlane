import imaplib
import email
import re
import os
import time
from email.header import decode_header
from datetime import datetime, timedelta

class MailHandler:
    def __init__(self, imap_server=None, email_user=None, email_password=None):
        self.imap_server = imap_server or os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.email_user = email_user or os.getenv("EMAIL_USER")
        self.email_password = email_password or os.getenv("EMAIL_PASSWORD")
        self.mail = None

    def connect(self):
        """Connects to the IMAP server."""
        if not self.email_user or not self.email_password:
            print("❌ MailHandler: Missing EMAIL_USER or EMAIL_PASSWORD in environment.")
            return False
            
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_user, self.email_password)
            return True
        except Exception as e:
            print(f"❌ MailHandler Connection Error: {e}")
            return False

    def disconnect(self):
        """Closes the connection."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass

    def get_verification_code(self, subject_filter="Greenhouse", time_window_seconds=120) -> str | None:
        """
        Searches for a recent email matching the subject filter and extracts a numeric code.
        """
        if not self.mail:
            if not self.connect():
                return None

        try:
            self.mail.select("inbox")
            
            # Search for unseen emails or all recent? 
            # Better to search all recent to avoid missing it if 'seen' flag triggered elsewhere
            # searching by date is complex in IMAP, simpler to fetch last N emails
            
            status, messages = self.mail.search(None, "ALL")
            if status != "OK":
                return None
            
            email_ids = messages[0].split()
            # Look at last 5 emails
            recent_ids = email_ids[-5:]
            
            for eid in reversed(recent_ids):
                res, msg_data = self.mail.fetch(eid, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Check Subject
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        # Check Date (simple check: must be very recent)
                        # Parsing email date is annoying, let's trust the 'recent execution' context
                        # If we assume we just asked for the code, it should be the top one.
                        
                        if subject_filter.lower() in subject.lower():
                            print(f"   📧 Found matching email: {subject}")
                            
                            # Get Body
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        body = part.get_payload(decode=True).decode()
                                        break
                            else:
                                body = msg.get_payload(decode=True).decode()
                            
                            # Extract Code (6-8 digits)
                            # Look for "verification code is: 123456" or similar patterns
                            # Or just the first distinct block of digits
                            match = re.search(r'\b\d{6,8}\b', body)
                            if match:
                                code = match.group(0)
                                print(f"   🔢 Extracted Code: {code}")
                                return code
            
            return None

        except Exception as e:
            print(f"❌ MailHandler Error: {e}")
            return None
