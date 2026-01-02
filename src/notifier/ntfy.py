"""
ntfy.sh notifier - FREE push notifications, no signup required!
https://ntfy.sh
"""

import httpx
from src.notifier.base_notifier import BaseNotifier, Notification, NotificationPriority
from src.utils.config import get_settings


class NtfyNotifier(BaseNotifier):
    """
    Send notifications via ntfy.sh - completely free, no signup!
    
    Usage:
    1. Pick a unique topic name (random string recommended)
    2. Set NTFY_TOPIC in .env
    3. Subscribe to your topic at: https://ntfy.sh/YOUR_TOPIC
       Or install the ntfy app on your phone
    """
    
    SERVICE_NAME = "ntfy.sh"
    BASE_URL = "https://ntfy.sh"
    
    def __init__(self, topic: str = None):
        super().__init__()
        settings = get_settings()
        self.topic = topic or settings.ntfy_topic
        
        if not self.topic:
            raise ValueError(
                "ntfy topic not set. Add NTFY_TOPIC to .env file.\n"
                "Pick a unique name like: autoapplier-yourname-12345"
            )
    
    def _priority_to_ntfy(self, priority: NotificationPriority) -> int:
        """Convert our priority to ntfy priority (1-5)"""
        mapping = {
            NotificationPriority.LOW: 2,
            NotificationPriority.NORMAL: 3,
            NotificationPriority.HIGH: 4,
            NotificationPriority.URGENT: 5,
        }
        return mapping.get(priority, 3)
    
    async def send(self, notification: Notification) -> bool:
        """Send notification via ntfy.sh"""
        try:
            headers = {
                "Title": notification.title,
                "Priority": str(self._priority_to_ntfy(notification.priority)),
                "Tags": ",".join(notification.tags) if notification.tags else "",
            }
            
            if notification.url:
                headers["Click"] = notification.url
                headers["Actions"] = f"view, Open, {notification.url}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/{self.topic}",
                    content=notification.message,
                    headers=headers,
                    timeout=10
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"ntfy notification failed: {e}")
            return False
    
    def get_subscribe_url(self) -> str:
        """Get the URL to subscribe to notifications"""
        return f"{self.BASE_URL}/{self.topic}"
    
    def get_subscribe_instructions(self) -> str:
        """Get instructions for subscribing"""
        return f"""
📱 Subscribe to AutoApplier notifications:

1. Install ntfy app on your phone:
   - Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy
   - iOS: https://apps.apple.com/app/ntfy/id1625396347

2. Subscribe to topic: {self.topic}
   Or open: {self.get_subscribe_url()}

3. Done! You'll get notifications when applications need your attention.
"""
