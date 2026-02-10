import re
import asyncio
from typing import Optional, Any
from src.core.applicant import Applicant


class FieldMapper:
    FIELD_MAPPINGS = {
        "first_name": ["personal.first_name", "first_name"],
        "first name": ["personal.first_name", "first_name"],
        "given name": ["personal.first_name", "first_name"],
        "fname": ["personal.first_name", "first_name"],
        "last_name": ["personal.last_name", "last_name"],
        "last name": ["personal.last_name", "last_name"],
        "surname": ["personal.last_name", "last_name"],
        "family name": ["personal.last_name", "last_name"],
        "lname": ["personal.last_name", "last_name"],
        "full_name": ["personal.full_name", "full_name"],
        "full name": ["personal.full_name", "full_name"],
        "name": ["personal.full_name", "full_name"],
        "email": ["personal.email", "email"],
        "email address": ["personal.email", "email"],
        "e-mail": ["personal.email", "email"],
        "phone": ["personal.phone", "phone"],
        "phone number": ["personal.phone", "phone"],
        "telephone": ["personal.phone", "phone"],
        "mobile": ["personal.phone", "phone"],
        "cell": ["personal.phone", "phone"],
        "address": ["personal.address.street", "address.street"],
        "street": ["personal.address.street", "address.street"],
        "street address": ["personal.address.street", "address.street"],
        "city": ["personal.address.city", "address.city"],
        "state": ["personal.address.state", "address.state"],
        "province": ["personal.address.state", "address.state"],
        "zip": ["personal.address.zip", "address.zip"],
        "zip code": ["personal.address.zip", "address.zip"],
        "postal code": ["personal.address.zip", "address.zip"],
        "zipcode": ["personal.address.zip", "address.zip"],
        "country": ["personal.address.country", "address.country"],
        "linkedin": ["personal.linkedin", "linkedin"],
        "linkedin url": ["personal.linkedin", "linkedin"],
        "linkedin profile": ["personal.linkedin", "linkedin"],
        "github": ["personal.github", "github"],
        "github url": ["personal.github", "github"],
        "github profile": ["personal.github", "github"],
        "portfolio": ["personal.portfolio", "portfolio"],
        "website": ["personal.website", "website"],
        "personal website": ["personal.website", "website"],
        "authorized to work": ["work_authorization.authorized_us"],
        "work authorization": ["work_authorization.authorized_us"],
        "legally authorized": ["work_authorization.authorized_us"],
        "sponsorship": ["work_authorization.requires_sponsorship"],
        "require sponsorship": ["work_authorization.requires_sponsorship"],
        "visa sponsorship": ["work_authorization.requires_sponsorship"],
        "need sponsorship": ["work_authorization.requires_sponsorship"],
        "gender": ["demographics.gender"],
        "veteran": ["demographics.veteran_status"],
        "veteran status": ["demographics.veteran_status"],
        "disability": ["demographics.disability_status"],
        "disability status": ["demographics.disability_status"],
        "ethnicity": ["demographics.ethnicity"],
        "race": ["demographics.ethnicity"],
    }
    
    BOOLEAN_PATTERNS = {
        "yes": [
            r"authorized.*work", r"legally.*work", r"eligible.*work", 
            r"18.*years", r"over.*18",
            r"willing", r"able", r"can you", r"start.*date", r"commute", r"relocate",
            r"open.*to", r"familiar.*with"
        ],
        "no": [r"require.*sponsorship", r"need.*sponsorship", r"visa.*sponsorship"],
    }
    
    def __init__(self, applicant: Applicant, llm_client=None):
        self.applicant = applicant
        self.llm_client = llm_client
        self._cache = {}
    
    async def get_value(self, field_label: str) -> Optional[Any]:
        normalized = self._normalize(field_label)
        
        if normalized in self._cache:
            return self._cache[normalized]
        
        # 1. Direct Mapping
        value = self._try_direct_mapping(normalized)
        if value is not None:
            self._cache[normalized] = value
            return value
        
        # 2. Fuzzy Mapping
        value = self._try_fuzzy_mapping(normalized)
        if value is not None:
            self._cache[normalized] = value
            return value
            
        # 3. LLM Fallback
        if self.llm_client:
            print(f"   🤖 Invoking LLM for field: '{field_label}'...")
            context = self._get_applicant_context()
            
            # STRATEGY: maximizing acceptance chances.
            prompt = f"""Field Label: "{field_label}"
User Profile:
{context}

Goal: Select the option (or provide the text) that MAXIMIZES the user's chance of getting the job. 
- If asked about "Start Date" or "End Date" (Year/Month), infer logically from the Education or Experience history related to the context (e.g., if asking about "School", use the dates for that school).
- If asked about relocation/locations, prefer "Yes" or the most flexible option unless explicitly restricted by profile.
- If asked about authorization, be truthful but opt for "Yes" if "Authorized" is in profile.
- If unsure, choose the positive/affirming option ("Yes", "Agree").

What is the single best value for this field for this user?
Return ONLY the value. If not found/applicable, return "None"."""
            
            for attempt in range(2):
                response = await self.llm_client.generate(prompt, max_tokens=50, temperature=0.1)
                
                if response:
                    if "None" not in response and len(response) < 100:
                         print(f"      -> LLM suggested: {response}")
                         self._cache[normalized] = response
                         return response
                    break # returned None/valid response, don't retry same non-error result
                
                # If response is None (rate limit), retry
                if attempt < 1:
                     print(f"     ⏳ LLM empty response (Attempt {attempt+1}/2), waiting briefly...")
                     await asyncio.sleep(1)
        
        return None
        
        return None
    
    def _get_applicant_context(self) -> str:
        # Helper to build a summary for LLM
        edu_str = "\n".join([f"- {e.degree} in {e.field} from {e.institution} ({e.start_date} to {e.end_date})" for e in self.applicant.education])
        exp_str = "\n".join([f"- {e.title} at {e.company} ({e.start_date} to {e.end_date})" for e in self.applicant.experience])
        
        achievements_str = "\n".join([f"- {a.name} ({a.year}): {a.description}" for a in self.applicant.achievements])
        projects_str = "\n".join([f"- {p.name} ({p.date_range}): {p.highlights[0]}" for p in self.applicant.projects[:3]])
        
        return f"""
Name: {self.applicant.full_name}
Email: {self.applicant.email}
Phone: {self.applicant.phone}
Address: {self.applicant.address.street}, {self.applicant.address.city}, {self.applicant.address.state} {self.applicant.address.zip}, {self.applicant.address.country}
LinkedIn: {self.applicant.linkedin}
Website: {self.applicant.website}
Work Auth: Authorized in US? {self.applicant.work_authorization.authorized_us}. Sponsorship needed? {self.applicant.work_authorization.requires_sponsorship}

Education History:
{edu_str}

Experience History:
{exp_str}

Projects:
{projects_str}

Achievements:
{achievements_str}

Skills: {self.applicant.get_skills_string(30)}
"""

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[*:\(\)]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _try_direct_mapping(self, label: str) -> Optional[Any]:
        if label in self.FIELD_MAPPINGS:
            paths = self.FIELD_MAPPINGS[label]
            return self._get_from_path(paths)
        return None
    
    def _try_fuzzy_mapping(self, label: str) -> Optional[Any]:
        # Avoid mapping long questions or irrelevant context to personal data
        # Especially "mobile" for "mobile app / mobile role"
        label_lower = label.lower()
        is_long_question = len(label_lower) > 30
        
        for key, paths in self.FIELD_MAPPINGS.items():
            if key in label_lower:
                # SPECIAL CASE: "mobile" usually means phone, but not in "mobile app" or "mobile role"
                if key == "mobile":
                    if any(x in label_lower for x in ["app", "role", "feature", "experience", "role", "position", "project", "contribut"]):
                        continue
                
                # SPECIAL CASE: Don't map personal data (like name/phone) to long questions via fuzzy match
                # Questions like "Tell us about your proudest achievement..." shouldn't be filled with "Harsh"
                if is_long_question and key in ["name", "first name", "last name", "phone", "mobile", "cell", "email"]:
                    continue

                value = self._get_from_path(paths)
                if value:
                    return value
        return None
    
    def _get_from_path(self, paths: list) -> Optional[Any]:
        for path in paths:
            value = self._extract_value(path)
            if value is not None:
                return value
        return None
    
    def _extract_value(self, path: str) -> Optional[Any]:
        parts = path.split('.')
        obj = self.applicant
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None
        
        if isinstance(obj, bool):
            return obj
        return str(obj) if obj else None
    
    def get_boolean_answer(self, question: str) -> Optional[bool]:
        question_lower = question.lower()
        
        for pattern in self.BOOLEAN_PATTERNS["yes"]:
            if re.search(pattern, question_lower):
                if "authorized" in question_lower or "eligible" in question_lower:
                    return self.applicant.work_authorization.authorized_us
                return True
        
        for pattern in self.BOOLEAN_PATTERNS["no"]:
            if re.search(pattern, question_lower):
                return self.applicant.work_authorization.requires_sponsorship
        
        return None
    
    async def get_dropdown_value(self, options: list[str], field_label: str) -> Optional[str]:
        label_lower = field_label.lower()
        
        # 1. Try Heuristics
        if "country" in label_lower:
            target = self.applicant.address.country
            match = self._best_match(options, target)
            if match:
                return match
        
        if "state" in label_lower or "province" in label_lower:
            target = self.applicant.address.state
            match = self._best_match(options, target)
            if match:
                return match
        
        if "gender" in label_lower:
            target = self.applicant.demographics.gender
            match = self._best_match(options, target)
            if match:
                return match

        if "disability" in label_lower:
            target = self.applicant.demographics.disability_status.lower()
            if "not " in target or "no " in target:
                 # Prefer full "No, I do not have a disability" over just "No" often
                 for opt in options:
                     if "no, i do not" in opt.lower():
                         return opt
                 for opt in options:
                     if opt.lower().strip() == "no":
                         return opt
            elif "yes" in target:
                 for opt in options:
                     if "yes, i have" in opt.lower():
                         return opt
                 for opt in options:
                     if opt.lower().strip() == "yes":
                         return opt
        
        if "experience" in label_lower and "year" in label_lower:
            years = self.applicant.years_of_experience
            for opt in options:
                if str(years) in opt:
                    return opt
        
        # 2. Try LLM
        if self.llm_client:
            print(f"   🤖 Invoking LLM for dropdown: '{field_label}' with {len(options)} options. Sample: {options[:5]}...")
            context = self._get_applicant_context()
            val = await self.llm_client.select_best_option(options, field_label, context)
            if val:
                 print(f"      -> LLM selected: {val}")
            return val
        
        return None
    
    def _best_match(self, options: list[str], target: str) -> Optional[str]:
        if not target:
            return None
        
        target_lower = target.lower()
        
        for opt in options:
            if opt.lower() == target_lower:
                return opt
        
        for opt in options:
            if target_lower in opt.lower() or opt.lower() in target_lower:
                return opt
        
        target_first = target_lower.split()[0] if target_lower else ""
        for opt in options:
            if target_first and target_first in opt.lower():
                return opt
        
        return None
