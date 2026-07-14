import re
from typing import Optional
from datetime import datetime
from src.core.job import Job


# --- Shared software-role classifier -----------------------------------------
# Used by every scraper as the "is this a software job?" gate so we cast a wide
# net (max recall) while still excluding clearly non-software roles (precision).

# Core software titles: if any match, it's software even if a "non-software"
# word also appears (e.g. "Software Engineer, Marketing Platform").
_CORE_SOFTWARE = [
    r'\bsoftware\s+(\w+\s+)?(engineer|develop\w*)\b', r'\bswe\b', r'\bsde\b', r'\bsdet\b',
    r'\b(back|front)[\s-]*end\s+(engineer|developer)\b', r'\bfull[\s-]*stack\b',
    r'\bweb\s+(developer|engineer)\b', r'\bmobile\s+(engineer|developer)\b',
    r'\b(ios|android)\s+(engineer|developer)\b',
    r'\bdevops\b', r'\bsite\s+reliability\b', r'\bsre\b', r'\bplatform\s+engineer\b',
    r'\binfrastructure\s+engineer\b', r'\bcloud\s+engineer\b',
    r'\b(machine\s+learning|ml|ai)\s+engineer\b', r'\bdata\s+engineer\b',
    r'\bsecurity\s+engineer\b', r'\bembedded\s+software\b', r'\bfirmware\b',
    r'\bapplication\s+(engineer|developer)\b', r'\bgame(play)?\s+(engineer|developer|programmer)\b',
    r'\bprogrammer\b', r'\bcompiler\b', r'\bkernel\b', r'\bdistributed\s+systems\b',
    r'\bforward\s+deployed\s+(software\s+)?engineer\b', r'\bqa\s+(engineer|automation)\b',
    r'\bsdet\b', r'\bautomation\s+engineer\b', r'\bsolutions?\s+developer\b',
]

# Non-software families: reject unless a core-software pattern above matched.
_NON_SOFTWARE = [
    r'\bsales\b', r'\baccount\s+(executive|manager)\b', r'\bbusiness\s+develop', r'\bpartnerships?\b',
    r'\bmarketing\b', r'\bseo\b', r'\brecruit', r'\btalent\b', r'\bhuman\s+resources?\b', r'\bhr\b',
    r'\bpeople\s+(operations|partner)\b', r'\bfinanc', r'\baccount(ant|ing)\b', r'\bcontroller\b',
    r'\blegal\b', r'\bcounsel\b', r'\battorney\b', r'\bparalegal\b',
    r'\b(graphic|ux|ui|visual|product|industrial)\s+design', r'\bdesigner\b',
    r'\bproduct\s+manager\b', r'\bprogram\s+manager\b', r'\bproject\s+manager\b', r'\bscrum\s+master\b',
    r'\bcustomer\s+(success|support|service|experience)\b', r'\btechnical\s+support\b', r'\bsupport\s+(engineer|specialist)\b',
    r'\b(business|financial|data|marketing|operations?)\s+analyst\b', r'\bbizops\b',
    r'\boperations\s+(manager|associate|specialist)\b', r'\badministrative\b', r'\bexecutive\s+assistant\b', r'\boffice\s+manager\b',
    r'\bwarehouse\b', r'\bdriver\b', r'\bdelivery\b', r'\bnurse\b', r'\bphysician\b', r'\bteacher\b', r'\bprofessor\b',
    r'\b(mechanical|electrical|civil|industrial|chemical|biomedical|manufacturing|hardware|field|process)\s+engineer\b',
    r'\bfield\s+service\b', r'\bdesign\s+engineer\b',
    r'\b(asic|vlsi|rtl|fpga|pcb|analog|rf|circuit|semiconductor|silicon|cad|soc)\b',
    r'\bphysical\s+design\b', r'\bdesign\s+verification\b',
    r'\bsales\s+engineer\b', r'\bsolutions?\s+(engineer|architect|consultant)\b', r'\bimplementation\b',
    r'\bwriter\b', r'\bcontent\b', r'\bcommunications?\b', r'\bpublic\s+relations\b',
    # physical / defense / aerospace / EE / ME engineering disciplines
    r'\bantenna\b', r'\baerospace\b', r'\baerodynamic', r'\bavionics\b', r'\bpropulsion\b',
    r'\bstructural\b', r'\bthermal\b', r'\belectro.?mechanical\b', r'\bmechatronic',
    r'\bexplosives?\b', r'\bmunitions?\b', r'\bmissile', r'\bweapons?\b', r'\bradar\b',
    r'\bmicrowave\b', r'\bphotonic', r'\boptical\b', r'\bfluid\b', r'\bcryogenic\b',
    r'\bmaterials\b', r'\bfacilities\b', r'\binstrumentation\b', r'\bcalibration\b',
    r'\bpower\s+electronics\b', r'\breal\s+estate\b',
    r'\b(electrical|mechanical|systems?|test|integration|quality|reliability|controls?|hardware)\s+(test\s+)?engineer\b',
]

# Weak positives: generic technical signals — count as software only if no
# non-software family matched.
# NOTE: bare "engineer" is deliberately NOT here — it matches every engineering
# discipline (antenna, aerospace, electrical, test…). Real software titles carry a
# software-specific keyword (in _CORE or below) or the word "software"/"developer".
_WEAK_SOFTWARE = [
    r'\bdeveloper\b', r'\bsoftware\b',
    r'\b(back|front)[\s-]?end\b', r'\bfull[\s-]*stack\b', r'\bcoding\b',
    r'\bdata\s+scientist\b', r'\bmachine\s+learning\b', r'\bcomputer\s+scien',
]

_CORE_RE = [re.compile(p, re.I) for p in _CORE_SOFTWARE]
_NON_RE = [re.compile(p, re.I) for p in _NON_SOFTWARE]
_WEAK_RE = [re.compile(p, re.I) for p in _WEAK_SOFTWARE]


def is_software_role(title: str) -> bool:
    """Broad software-engineering classifier. Wide recall, excludes non-software families."""
    if not title:
        return False
    t = f" {title.lower()} "
    if any(p.search(t) for p in _CORE_RE):
        return True
    if any(p.search(t) for p in _NON_RE):
        return False
    return any(p.search(t) for p in _WEAK_RE)


# --- Seniority classifier ----------------------------------------------------
# Titles above entry/mid level. Used to exclude roles the user (a junior/new grad)
# can't apply to. "II" and "L3" are intentionally kept (entry/mid).
_SENIOR_PATTERNS = [
    r'\bsenior\b', r'\bsr\.?\b', r'\bsnr\b', r'\blead\b', r'\bprincipal\b',
    r'\bstaff\b', r'\bdistinguished\b', r'\bfellow\b', r'\bexpert\b', r'\bveteran\b',
    r'\bmanager\b', r'\bdirector\b', r'\bhead\s+of\b', r'\bvp\b', r'\bvice\s+president\b',
    r'\bchief\b', r'\bc[te]o\b', r'\bexecutive\b', r'\barchitect\b',
    r'\b(iii|iv|v|vi|vii)\b', r'\bl[4-9]\b', r'\blevel\s*[4-9]\b',
    r'\b(?:5|6|7|8|9|10|1[0-9])\+?\s*years?\b',
]
_SENIOR_RE = [re.compile(p, re.I) for p in _SENIOR_PATTERNS]


def is_senior_role(title: str) -> bool:
    """True for senior/lead/staff/principal/manager+ roles a junior shouldn't apply to."""
    if not title:
        return False
    return any(p.search(f" {title.lower()} ") for p in _SENIOR_RE)


class JobFilter:
    YEARS_EXPERIENCE_PATTERN = r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?(?:exp|experience)?'

    def __init__(self, max_years_experience: int = 3, exclude_companies: list[str] = None, max_days_old: int = 14):
        self.max_years_experience = max_years_experience
        self.exclude_companies = [c.lower() for c in (exclude_companies or [])]
        self.max_days_old = max_days_old

        self._years_pattern = re.compile(self.YEARS_EXPERIENCE_PATTERN, re.IGNORECASE)

    def should_include(self, job: Job) -> tuple[bool, str]:
        company = job.company.lower()
        description = (job.description or "").lower()

        for excluded in self.exclude_companies:
            if excluded in company:
                return False, f"Excluded company: {excluded}"

        if is_senior_role(job.title):
            return False, "Senior/lead role detected in title"

        if not is_software_role(job.title):
            return False, "Not a software role"

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
