import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class BrowserConfig(BaseModel):
    type: str = "chromium"
    headless: bool = True
    slow_mo: int = 0
    viewport: dict = Field(default_factory=lambda: {"width": 1920, "height": 1080})
    user_agent: str = ""


class DelayConfig(BaseModel):
    min: int = 30
    max: int = 120


class ApplicationConfig(BaseModel):
    review_mode: bool = True
    max_per_run: int = 10
    delay: DelayConfig = Field(default_factory=DelayConfig)
    save_screenshots: bool = True
    screenshots_dir: str = "data/screenshots"


class SearchConfig(BaseModel):
    titles: list[str] = Field(default_factory=lambda: ["Software Engineer"])
    locations: list[str] = Field(default_factory=lambda: ["Remote"])
    experience_levels: list[str] = Field(default_factory=lambda: ["Entry Level", "Mid Level"])
    job_types: list[str] = Field(default_factory=lambda: ["Full-time"])
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    exclude_companies: list[str] = Field(default_factory=list)
    max_days_old: int = 7


class ScraperSourceConfig(BaseModel):
    enabled: bool = True
    easy_apply_only: bool = False
    companies: list[dict] = Field(default_factory=list)


class ScrapersConfig(BaseModel):
    jobright: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)
    simplify: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)
    cvrve: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)
    career_sites: ScraperSourceConfig = Field(default_factory=ScraperSourceConfig)


class LLMConfig(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    temperature: float = 0.7
    max_tokens: int = 500
    max_retries: int = 3
    always_review_questions: list[str] = Field(default_factory=lambda: [
        "salary", "compensation", "visa", "sponsorship", "clearance"
    ])


class NotificationEvents(BaseModel):
    needs_review: bool = True
    completed: bool = True
    failed: bool = True
    daily_summary: bool = True


class QuietHours(BaseModel):
    enabled: bool = False
    start: str = "22:00"
    end: str = "08:00"


class NotificationsConfig(BaseModel):
    primary: str = "ntfy"
    events: NotificationEvents = Field(default_factory=NotificationEvents)
    quiet_hours: QuietHours = Field(default_factory=QuietHours)


class DatabaseConfig(BaseModel):
    path: str = str(Path(__file__).parents[3] / "data" / "applications.db")
    echo: bool = False


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/autoapplier.log"
    max_size: int = 10
    backup_count: int = 5


class Settings(BaseSettings):
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
    
    # Email Automation
    email_user: str = Field(default="", alias="EMAIL_USER")
    email_password: str = Field(default="", alias="EMAIL_PASSWORD")
    
    # BuiltIn Session Cookies (get from browser after logging in)
    # To get these: Log into builtin.com, open DevTools > Application > Cookies
    # Copy ALL of these cookie values:
    builtin_session_name: str = Field(default="", alias="BUILTIN_SESSION_NAME")  # e.g., "SSESSf025deca82..."
    builtin_session: str = Field(default="", alias="BUILTIN_SESSION")  # Value of SSESSxxx cookie
    builtin_bix_auth: str = Field(default="", alias="BUILTIN_BIX_AUTH")  # Value of BIX_AUTH (e.g., "chunks-2")
    builtin_bix_authc1: str = Field(default="", alias="BUILTIN_BIX_AUTHC1")  # Value of BIX_AUTHC1
    builtin_bix_authc2: str = Field(default="", alias="BUILTIN_BIX_AUTHC2")  # Value of BIX_AUTHC2
    
    # LinkedIn Session Cookies (optional - for LinkedIn Easy Apply)
    linkedin_li_at: str = Field(default="", alias="LINKEDIN_LI_AT")
    linkedin_jsessionid: str = Field(default="", alias="LINKEDIN_JSESSIONID")
    
    headless: bool = Field(default=True, alias="HEADLESS")
    max_applications_per_run: int = Field(default=10, alias="MAX_APPLICATIONS_PER_RUN")
    auto_submit: bool = Field(default=False, alias="AUTO_SUBMIT")
    
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
        if config_path is None:
            # Try root config, then parent dirs (up to 3 levels)
            config_path = Path("config/settings.yaml")
            current = Path.cwd()
            for _ in range(3):
                candidate = current / "config/settings.yaml"
                if candidate.exists():
                    config_path = candidate
                    break
                current = current.parent
        else:
            config_path = Path(config_path)
        
        yaml_config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f) or {}
                
        return cls(**yaml_config)
    
    def get_profile_path(self) -> Path:
        return Path("data/profile.json")
    
    def get_resume_path(self) -> Path:
        return Path("data/resume.pdf")
    
    def ensure_directories(self) -> None:
        directories = ["data", "data/screenshots", "logs", "config"]
        for dir_path in directories:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    settings = Settings.load()
    settings.ensure_directories()
    return settings


settings = get_settings()
