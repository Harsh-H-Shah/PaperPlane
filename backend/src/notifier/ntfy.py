import httpx
from src.notifier.base_notifier import BaseNotifier, Notification, NotificationPriority
from src.utils.config import get_settings


class NtfyNotifier(BaseNotifier):
    SERVICE_NAME = "ntfy.sh"
    BASE_URL = "https://ntfy.sh"
    
    def __init__(self, topic: str = None):
        super().__init__()
        settings = get_settings()
        self.topic = topic or settings.ntfy_topic
        
        if not self.topic:
            raise ValueError("ntfy topic not set. Add NTFY_TOPIC to .env file.")
    
    def _priority_to_ntfy(self, priority: NotificationPriority) -> int:
        mapping = {
            NotificationPriority.LOW: 2,
            NotificationPriority.NORMAL: 3,
            NotificationPriority.HIGH: 4,
            NotificationPriority.URGENT: 5,
        }
        return mapping.get(priority, 3)
    
    async def send(self, notification: Notification) -> bool:
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
        return f"{self.BASE_URL}/{self.topic}"
    
    def get_subscribe_instructions(self) -> str:
        return f"""
📱 Subscribe to PaperPlane notifications:

1. Install ntfy app on your phone
2. Subscribe to topic: {self.topic}
   Or open: {self.get_subscribe_url()}

3. Done! You'll get notifications when applications need your attention.
"""
