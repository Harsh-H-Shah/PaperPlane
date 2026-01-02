"""
Configuration management - loads settings from YAML and environment variables
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BrowserConfig(BaseModel):
    """Browser automation settings"""
    type: str = "chromium"
    headless: bool = True
    slow_mo: int = 0
    viewport: dict = Field(default_factory=lambda: {"width": 1920, "height": 1080})
    user_agent: str = ""


class DelayConfig(BaseModel):
    """Delay configuration"""
    min: int = 30
    max: int = 120


class ApplicationConfig(BaseModel):
    """Application behavior settings"""
    review_mode: bool = True
    max_per_run: int = 10
    delay: DelayConfig = Field(default_factory=DelayConfig)
    save_screenshots: bool = True
    screenshots_dir: str = "data/screenshots"


class SearchConfig(BaseModel):
    """Job search preferences"""
    titles: list[str] = Field(default_factory=lambda: ["Software Engineer"])
    locations: list[str] = Field(default_factory=lambda: ["Remote"])
    experience_levels: list[str] = Field(default_factory=lambda: ["Entry Level", "Mid Level"])
    job_types: list[str] = Field(default_factory=lambda: ["Full-time"])
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    exclude_companies: list[str] = Field(default_factory=list)
    max_days_old: int = 7


class ScraperSourceConfig(BaseModel):
    """Individual scraper configuration"""
    enabled: bool = True
    easy_apply_only: bool = False  # LinkedIn specific
    companies: list[dict] = Field(default_factory=list)  # Career sites specific


class ScrapersConfig(BaseModel):
    """All scrapers configuration"""
    linkedin: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)
    jobright: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)
    simplify: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)
    cvrve: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)
    career_sites: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)


class LLMConfig(BaseModel):
    """LLM settings"""
    provider: str = "gemini"
    model: str = "gemini-pro"
    temperature: float = 0.7
    max_tokens: int = 500
    max_retries: int = 3
    always_review_questions: list[str] = Field(default_factory=lambda: [
        "salary", "compensation", "visa", "sponsorship", "clearance"
    ])


class NotificationEvents(BaseModel):
    """Which events trigger notifications"""
    needs_review: bool = True
    completed: bool = True
    failed: bool = True
    daily_summary: bool = True


class QuietHours(BaseModel):
    """Quiet hours configuration"""
    enabled: bool = False
    start: str = "22:00"
    end: str = "08:00"


class NotificationsConfig(BaseModel):
    """Notification settings"""
    primary: str = "ntfy"
    events: NotificationEvents = Field(default_factory=NotificationEvents)
    quiet_hours: QuietHours = Field(default_factory=QuietHours)


class DatabaseConfig(BaseModel):
    """Database settings"""
    path: str = "data/applications.db"
    echo: bool = False


class LoggingConfig(BaseModel):
    """Logging settings"""
    level: str = "INFO"
    file: str = "logs/autoapplier.log"
    max_size: int = 10
    backup_count: int = 5


class Settings(BaseSettings):
    """
    Main settings class that combines YAML config with environment variables.
    Environment variables take precedence.
    """
    # From environment variables
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    discord_webhook_url: str = Field(default="", alias="DISCORD_WEBHOOK_URL")
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    ntfy_topic: str = Field(default="autoapplier", alias="NTFY_TOPIC")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    notification_email: str = Field(default="", alias="NOTIFICATION_EMAIL")
    linkedin_li_at: str = Field(default="", alias="LINKEDIN_LI_AT")
    linkedin_jsessionid: str = Field(default="", alias="LINKEDIN_JSESSIONID")
    headless: bool = Field(default=True, alias="HEADLESS")
    max_applications_per_run: int = Field(default=10, alias="MAX_APPLICATIONS_PER_RUN")
    auto_submit: bool = Field(default=False, alias="AUTO_SUBMIT")
    
    # From YAML config
    application: ApplicationConfig = Field(default_factory=ApplicationConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    scrapers: ScrapersConfig = Field(default_factory=ScrapersConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @classmethod
    def load(cls, config_path: Optional[str | Path] = None) -> "Settings":
        """
        Load settings from YAML file and merge with environment variables.
        """
        # Default config path
        if config_path is None:
            config_path = Path("config/settings.yaml")
        else:
            config_path = Path(config_path)
        
        # Load YAML if exists
        yaml_config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f) or {}
        
        # Create settings with YAML config
        return cls(**yaml_config)
    
    def get_profile_path(self) -> Path:
        """Get path to user profile"""
        return Path("data/profile.json")
    
    def get_resume_path(self) -> Path:
        """Get path to resume file"""
        return Path("data/resume.pdf")
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist"""
        directories = [
            "data",
            "data/screenshots",
            "logs",
            "config",
        ]
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Call this function to access settings throughout the application.
    """
    settings = Settings.load()
    settings.ensure_directories()
    return settings


# For direct module access
settings = get_settings()
