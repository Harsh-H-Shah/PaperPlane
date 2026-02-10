import re
from typing import Optional
from datetime import datetime
from src.core.job import Job


class JobFilter:
    EXCLUDE_TITLE_PATTERNS = [
        r'\bsenior\b', r'\bsr\.?\b', r'\blead\b', r'\bprincipal\b',
        r'\bstaff\b', r'\bmanager\b', r'\bdirector\b', r'\bhead\b',
        r'\bvp\b', r'\bexecutive\b', r'\barchitect\b', r'\b10\+?\s*years?\b',
        r'\b8\+?\s*years?\b', r'\b7\+?\s*years?\b', r'\b6\+?\s*years?\b',
        r'\b5\+?\s*years?\b', r'\biii\b', r'\biv\b', r'\blevel\s*[345]\b',
    ]
    
    INCLUDE_TITLE_PATTERNS = [
        r'\bsoftware\b', r'\bengineer\b', r'\bdeveloper\b', r'\bprogrammer\b',
        r'\bfrontend\b', r'\bbackend\b', r'\bfull\s*stack\b', r'\bfullstack\b',
        r'\bweb\b', r'\bmobile\b', r'\bdata\b', r'\bml\b', r'\bai\b',
        r'\bmachine\s*learning\b', r'\bdevops\b', r'\bsre\b', r'\bcloud\b',
        r'\bplatform\b', r'\binfra\b', r'\bsecurity\b', r'\btest\b',
        r'\bqa\b', r'\bquality\b', r'\bautomation\b',
    ]
    
    ENTRY_LEVEL_PATTERNS = [
        r'\bjunior\b', r'\bjr\.?\b', r'\bentry\s*level\b', r'\bentry-level\b',
        r'\bnew\s*grad\b', r'\bgraduate\b', r'\bfresher\b', r'\bintern\b',
        r'\binternship\b', r'\bassociate\b', r'\bi\b', r'\bii\b',
        r'\blevel\s*[12]\b', r'\b0-[12]\s*years?\b', r'\b[01]-[23]\s*years?\b',
        r'\bearly\s*career\b', r'\brecent\s*grad\b',
    ]
    
    YEARS_EXPERIENCE_PATTERN = r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?(?:exp|experience)?'
    
    def __init__(self, max_years_experience: int = 3, exclude_companies: list[str] = None, max_days_old: int = 14):
        self.max_years_experience = max_years_experience
        self.exclude_companies = [c.lower() for c in (exclude_companies or [])]
        self.max_days_old = max_days_old
        
        self._exclude_patterns = [re.compile(p, re.IGNORECASE) for p in self.EXCLUDE_TITLE_PATTERNS]
        self._include_patterns = [re.compile(p, re.IGNORECASE) for p in self.INCLUDE_TITLE_PATTERNS]
        self._entry_patterns = [re.compile(p, re.IGNORECASE) for p in self.ENTRY_LEVEL_PATTERNS]
        self._years_pattern = re.compile(self.YEARS_EXPERIENCE_PATTERN, re.IGNORECASE)
    
    def should_include(self, job: Job) -> tuple[bool, str]:
        title = job.title.lower()
        company = job.company.lower()
        description = (job.description or "").lower()
        
        for excluded in self.exclude_companies:
            if excluded in company:
                return False, f"Excluded company: {excluded}"
        
        for pattern in self._exclude_patterns:
            if pattern.search(title):
                return False, "Senior/lead role detected in title"
        
        is_technical = False
        for pattern in self._include_patterns:
            if pattern.search(title):
                is_technical = True
                break
        
        if not is_technical:
            return False, "Not a technical/software role"
        
        # is_entry_level = False
        for pattern in self._entry_patterns:
            if pattern.search(title):
                # is_entry_level = True
                break
        
        years_required = self._extract_years_experience(description)
        if years_required is not None and years_required > self.max_years_experience:
            return False, f"Requires {years_required}+ years experience"
        
        if job.posted_date:
            days_ago = (datetime.now() - job.posted_date).days
            if days_ago > self.max_days_old:
                return False, f"Posted {days_ago} days ago (max: {self.max_days_old})"
        
        return True, "Passes all filters"
    
    def _extract_years_experience(self, text: str) -> Optional[int]:
        if not text:
            return None
        
        matches = self._years_pattern.findall(text[:2000])
        if not matches:
            return None
        
        years = []
        for match in matches:
            try:
                years.append(int(match))
            except ValueError:
                continue
        
        if years:
            return min(years)
        return None
    
    def filter_jobs(self, jobs: list[Job]) -> tuple[list[Job], list[dict]]:
        accepted = []
        rejected = []
        
        for job in jobs:
            should_include, reason = self.should_include(job)
            if should_include:
                accepted.append(job)
            else:
                rejected.append({"job": job, "reason": reason})
        
        return accepted, rejected
    
    def get_stats(self, jobs: list[Job]) -> dict:
        accepted, rejected = self.filter_jobs(jobs)
        
        rejection_reasons = {}
        for item in rejected:
            reason = item["reason"]
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        return {
            "total": len(jobs),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "acceptance_rate": len(accepted) / len(jobs) if jobs else 0,
            "rejection_reasons": rejection_reasons,
        }
