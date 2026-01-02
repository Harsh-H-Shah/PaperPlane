"""
Discord webhook notifier
"""

import httpx
from src.notifier.base_notifier import BaseNotifier, Notification, NotificationPriority
from src.utils.config import get_settings


class DiscordNotifier(BaseNotifier):
    """
    Send notifications via Discord webhook.
    
    Setup:
    1. Create a Discord server (or use existing)
    2. Go to Server Settings > Integrations > Webhooks
    3. Create a webhook and copy the URL
    4. Add DISCORD_WEBHOOK_URL to .env
    """
    
    SERVICE_NAME = "Discord"
    
    def __init__(self, webhook_url: str = None):
        super().__init__()
        settings = get_settings()
        self.webhook_url = webhook_url or settings.discord_webhook_url
        
        if not self.webhook_url:
            raise ValueError(
                "Discord webhook URL not set. Add DISCORD_WEBHOOK_URL to .env file."
            )
    
    def _priority_to_color(self, priority: NotificationPriority) -> int:
        """Convert priority to Discord embed color"""
        colors = {
            NotificationPriority.LOW: 0x808080,      # Gray
            NotificationPriority.NORMAL: 0x3498db,   # Blue
            NotificationPriority.HIGH: 0xf39c12,     # Orange
            NotificationPriority.URGENT: 0xe74c3c,   # Red
        }
        return colors.get(priority, 0x3498db)
    
    async def send(self, notification: Notification) -> bool:
        """Send notification via Discord webhook"""
        try:
            embed = {
                "title": notification.title,
                "description": notification.message,
                "color": self._priority_to_color(notification.priority),
            }
            
            if notification.url:
                embed["url"] = notification.url
            
            if notification.tags:
                embed["footer"] = {"text": " | ".join(notification.tags)}
            
            payload = {
                "username": "AutoApplier",
                "embeds": [embed]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )
                
                return response.status_code in [200, 204]
                
        except Exception as e:
            print(f"Discord notification failed: {e}")
            return False
