"""
Application type detector - identifies what ATS platform a job uses
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from src.core.job import ApplicationType


class ApplicationDetector:
    """
    Detects the application platform type from URL patterns and page content.
    """
    
    # URL patterns for each platform
    URL_PATTERNS = {
        ApplicationType.WORKDAY: [
            r'.*\.myworkdayjobs\.com',
            r'.*\.wd\d+\.myworkdayjobs\.com',
            r'workday\.com/.*apply',
            r'myworkday\.com',
        ],
        ApplicationType.ASHBY: [
            r'jobs\.ashbyhq\.com',
            r'app\.ashbyhq\.com',
        ],
        ApplicationType.GREENHOUSE: [
            r'boards\.greenhouse\.io',
            r'.*\.greenhouse\.io',
            r'job-boards\.greenhouse\.io',
        ],
        ApplicationType.LEVER: [
            r'jobs\.lever\.co',
            r'.*\.lever\.co',
        ],
        ApplicationType.ORACLE: [
            r'.*\.taleo\.net',
            r'.*\.oraclecloud\.com/hcmUI',
            r'oracle\.com/.*careers',
        ],
        ApplicationType.ADP: [
            r'.*\.adp\.com',
            r'workforcenow\.adp\.com',
        ],
        ApplicationType.ICIMS: [
            r'.*\.icims\.com',
            r'careers-.*\.icims\.com',
        ],
        ApplicationType.TALEO: [
            r'.*\.taleo\.net',
            r'tbe\.taleo\.net',
        ],
        ApplicationType.JOBVITE: [
            r'.*\.jobvite\.com',
            r'jobs\.jobvite\.com',
        ],
        ApplicationType.SMARTRECRUITERS: [
            r'.*\.smartrecruiters\.com',
            r'careers\.smartrecruiters\.com',
        ],
        ApplicationType.LINKEDIN_EASY: [
            r'linkedin\.com/jobs/.*easy.*apply',
            r'linkedin\.com/jobs/view',
        ],
    }
    
    # Page content patterns (for when URL isn't conclusive)
    CONTENT_PATTERNS = {
        ApplicationType.WORKDAY: [
            r'workday',
            r'wd-apply',
            r'WDAY_',
        ],
        ApplicationType.ASHBY: [
            r'ashbyhq',
            r'ashby-apply',
        ],
        ApplicationType.GREENHOUSE: [
            r'greenhouse\.io',
            r'gh-apply',
            r'greenhouse-application',
        ],
        ApplicationType.LEVER: [
            r'lever\.co',
            r'lever-apply',
        ],
        ApplicationType.LINKEDIN_EASY: [
            r'easy-apply-modal',
            r'jobs-apply-button--easy-apply',
        ],
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._compiled_url_patterns = {
            app_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for app_type, patterns in self.URL_PATTERNS.items()
        }
        self._compiled_content_patterns = {
            app_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for app_type, patterns in self.CONTENT_PATTERNS.items()
        }
    
    def detect_from_url(self, url: str) -> Tuple[ApplicationType, float]:
        """
        Detect application type from URL.
        
        Returns:
            (ApplicationType, confidence) - confidence is 0.0 to 1.0
        """
        if not url:
            return ApplicationType.UNKNOWN, 0.0
        
        parsed = urlparse(url.lower())
        full_url = f"{parsed.netloc}{parsed.path}"
        
        for app_type, patterns in self._compiled_url_patterns.items():
            for pattern in patterns:
                if pattern.search(full_url):
                    return app_type, 0.9  # High confidence from URL
        
        return ApplicationType.UNKNOWN, 0.0
    
    def detect_from_content(self, html_content: str) -> Tuple[ApplicationType, float]:
        """
        Detect application type from page HTML content.
        
        Returns:
            (ApplicationType, confidence)
        """
        if not html_content:
            return ApplicationType.UNKNOWN, 0.0
        
        # Check each platform's content patterns
        for app_type, patterns in self._compiled_content_patterns.items():
            matches = 0
            for pattern in patterns:
                if pattern.search(html_content):
                    matches += 1
            
            if matches > 0:
                # More matches = higher confidence
                confidence = min(0.5 + (matches * 0.2), 0.85)
                return app_type, confidence
        
        return ApplicationType.UNKNOWN, 0.0
    
    def detect(
        self, 
        url: str, 
        html_content: str = ""
    ) -> Tuple[ApplicationType, float]:
        """
        Detect application type using both URL and content.
        
        Args:
            url: The application URL
            html_content: Optional HTML content of the page
        
        Returns:
            (ApplicationType, confidence)
        """
        # Try URL first (most reliable)
        url_type, url_conf = self.detect_from_url(url)
        if url_conf >= 0.9:
            return url_type, url_conf
        
        # Fall back to content analysis
        if html_content:
            content_type, content_conf = self.detect_from_content(html_content)
            if content_conf > url_conf:
                return content_type, content_conf
        
        # Return URL result or unknown
        if url_conf > 0:
            return url_type, url_conf
        
        return ApplicationType.CUSTOM, 0.3  # Assume custom if unknown
    
    def is_linkedin_easy_apply(self, url: str, html_content: str = "") -> bool:
        """Check if this is a LinkedIn Easy Apply job"""
        app_type, _ = self.detect(url, html_content)
        return app_type == ApplicationType.LINKEDIN_EASY
    
    def get_platform_info(self, app_type: ApplicationType) -> dict:
        """Get information about a platform"""
        info = {
            ApplicationType.WORKDAY: {
                "name": "Workday",
                "difficulty": "medium",
                "multi_step": True,
                "requires_account": True,
            },
            ApplicationType.ASHBY: {
                "name": "Ashby",
                "difficulty": "easy",
                "multi_step": False,
                "requires_account": False,
            },
            ApplicationType.GREENHOUSE: {
                "name": "Greenhouse",
                "difficulty": "easy",
                "multi_step": False,
                "requires_account": False,
            },
            ApplicationType.LEVER: {
                "name": "Lever",
                "difficulty": "easy",
                "multi_step": False,
                "requires_account": False,
            },
            ApplicationType.LINKEDIN_EASY: {
                "name": "LinkedIn Easy Apply",
                "difficulty": "easy",
                "multi_step": True,
                "requires_account": True,
            },
            ApplicationType.ORACLE: {
                "name": "Oracle/Taleo",
                "difficulty": "hard",
                "multi_step": True,
                "requires_account": True,
            },
            ApplicationType.ADP: {
                "name": "ADP Workforce",
                "difficulty": "hard",
                "multi_step": True,
                "requires_account": True,
            },
        }
        return info.get(app_type, {
            "name": "Unknown",
            "difficulty": "unknown",
            "multi_step": False,
            "requires_account": False,
        })


# Singleton instance
_detector: Optional[ApplicationDetector] = None


def get_detector() -> ApplicationDetector:
    """Get the global detector instance"""
    global _detector
    if _detector is None:
        _detector = ApplicationDetector()
    return _detector


def detect_application_type(url: str, html_content: str = "") -> Tuple[ApplicationType, float]:
    """
    Convenience function to detect application type.
    
    Args:
        url: The application URL
        html_content: Optional HTML content
    
    Returns:
        (ApplicationType, confidence)
    """
    return get_detector().detect(url, html_content)
