import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from src.core.job import ApplicationType


class ApplicationDetector:
    URL_PATTERNS = {
        ApplicationType.WORKDAY: [r'.*\.myworkdayjobs\.com', r'.*\.wd\d+\.myworkdayjobs\.com', r'workday\.com/.*apply', r'myworkday\.com'],
        ApplicationType.ASHBY: [r'jobs\.ashbyhq\.com', r'app\.ashbyhq\.com'],
        ApplicationType.GREENHOUSE: [r'boards\.greenhouse\.io', r'.*\.greenhouse\.io', r'job-boards\.greenhouse\.io'],
        ApplicationType.LEVER: [r'jobs\.lever\.co', r'.*\.lever\.co'],
        ApplicationType.ORACLE: [r'.*\.taleo\.net', r'.*\.oraclecloud\.com/hcmUI', r'oracle\.com/.*careers'],
        ApplicationType.ADP: [r'.*\.adp\.com', r'workforcenow\.adp\.com'],
        ApplicationType.ICIMS: [r'.*\.icims\.com', r'careers-.*\.icims\.com'],
        ApplicationType.TALEO: [r'.*\.taleo\.net', r'tbe\.taleo\.net'],
        ApplicationType.JOBVITE: [r'.*\.jobvite\.com', r'jobs\.jobvite\.com'],
        ApplicationType.SMARTRECRUITERS: [r'.*\.smartrecruiters\.com', r'careers\.smartrecruiters\.com'],
        ApplicationType.BUILTIN: [r'builtin\.com/job/', r'builtin\.com/jobs/', r'builtinnyc\.com/job/', r'builtinsf\.com/job/', r'builtinboston\.com/job/', r'builtincolorado\.com/job/', r'builtinla\.com/job/', r'builtinseattle\.com/job/', r'builtin Austin\.com/job/', r'builtin Chicago\.com/job/'],
    }
    
    CONTENT_PATTERNS = {
        ApplicationType.WORKDAY: [r'workday', r'wd-apply', r'WDAY_'],
        ApplicationType.ASHBY: [r'ashbyhq', r'ashby-apply'],
        ApplicationType.GREENHOUSE: [r'greenhouse\.io', r'gh-apply', r'greenhouse-application'],
        ApplicationType.LEVER: [r'lever\.co', r'lever-apply'],
        ApplicationType.BUILTIN: [r'Apply on company site', r'>Apply Now<'],
    }
    
    def __init__(self):
        self._compiled_url_patterns = {
            app_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for app_type, patterns in self.URL_PATTERNS.items()
        }
        self._compiled_content_patterns = {
            app_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for app_type, patterns in self.CONTENT_PATTERNS.items()
        }
    
    def detect_from_url(self, url: str) -> Tuple[ApplicationType, float]:
        if not url:
            return ApplicationType.UNKNOWN, 0.0
        
        parsed = urlparse(url.lower())
        full_url = f"{parsed.netloc}{parsed.path}"
        
        for app_type, patterns in self._compiled_url_patterns.items():
            for pattern in patterns:
                if pattern.search(full_url):
                    return app_type, 0.9
        
        return ApplicationType.UNKNOWN, 0.0
    
    def detect_from_content(self, html_content: str) -> Tuple[ApplicationType, float]:
        if not html_content:
            return ApplicationType.UNKNOWN, 0.0
        
        for app_type, patterns in self._compiled_content_patterns.items():
            matches = 0
            for pattern in patterns:
                if pattern.search(html_content):
                    matches += 1
            
            if matches > 0:
                confidence = min(0.5 + (matches * 0.2), 0.85)
                return app_type, confidence
        
        return ApplicationType.UNKNOWN, 0.0
    
    def detect(self, url: str, html_content: str = "") -> Tuple[ApplicationType, float]:
        url_type, url_conf = self.detect_from_url(url)
        if url_conf >= 0.9:
            return url_type, url_conf
        
        if html_content:
            content_type, content_conf = self.detect_from_content(html_content)
            if content_conf > url_conf:
                return content_type, content_conf
        
        if url_conf > 0:
            return url_type, url_conf
        
        return ApplicationType.CUSTOM, 0.3
    
    
    def get_platform_info(self, app_type: ApplicationType) -> dict:
        info = {
            ApplicationType.WORKDAY: {"name": "Workday", "difficulty": "medium", "multi_step": True, "requires_account": True},
            ApplicationType.ASHBY: {"name": "Ashby", "difficulty": "easy", "multi_step": False, "requires_account": False},
            ApplicationType.GREENHOUSE: {"name": "Greenhouse", "difficulty": "easy", "multi_step": False, "requires_account": False},
            ApplicationType.LEVER: {"name": "Lever", "difficulty": "easy", "multi_step": False, "requires_account": False},
            ApplicationType.ORACLE: {"name": "Oracle/Taleo", "difficulty": "hard", "multi_step": True, "requires_account": True},
            ApplicationType.ADP: {"name": "ADP Workforce", "difficulty": "hard", "multi_step": True, "requires_account": True},
        }
        return info.get(app_type, {"name": "Unknown", "difficulty": "unknown", "multi_step": False, "requires_account": False})


_detector: Optional[ApplicationDetector] = None


def get_detector() -> ApplicationDetector:
    global _detector
    if _detector is None:
        _detector = ApplicationDetector()
    return _detector


def detect_application_type(url: str, html_content: str = "") -> Tuple[ApplicationType, float]:
    return get_detector().detect(url, html_content)
