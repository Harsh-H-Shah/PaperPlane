"""
Field mapper - maps form field labels to applicant profile fields
"""

import re
from typing import Optional, Any
from src.core.applicant import Applicant


class FieldMapper:
    """
    Maps common form field labels to corresponding applicant profile values.
    Handles variations in field naming across different platforms.
    """
    
    # Field name variations -> (profile_path, transform_function)
    FIELD_MAPPINGS = {
        # Name fields
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
        
        # Contact
        "email": ["personal.email", "email"],
        "email address": ["personal.email", "email"],
        "e-mail": ["personal.email", "email"],
        
        "phone": ["personal.phone", "phone"],
        "phone number": ["personal.phone", "phone"],
        "telephone": ["personal.phone", "phone"],
        "mobile": ["personal.phone", "phone"],
        "cell": ["personal.phone", "phone"],
        
        # Address
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
        
        # Online presence
        "linkedin": ["personal.linkedin", "linkedin"],
        "linkedin url": ["personal.linkedin", "linkedin"],
        "linkedin profile": ["personal.linkedin", "linkedin"],
        
        "github": ["personal.github", "github"],
        "github url": ["personal.github", "github"],
        "github profile": ["personal.github", "github"],
        
        "portfolio": ["personal.portfolio", "portfolio"],
        "website": ["personal.website", "website"],
        "personal website": ["personal.website", "website"],
        
        # Work authorization
        "authorized to work": ["work_authorization.authorized_us"],
        "work authorization": ["work_authorization.authorized_us"],
        "legally authorized": ["work_authorization.authorized_us"],
        
        "sponsorship": ["work_authorization.requires_sponsorship"],
        "require sponsorship": ["work_authorization.requires_sponsorship"],
        "visa sponsorship": ["work_authorization.requires_sponsorship"],
        "need sponsorship": ["work_authorization.requires_sponsorship"],
        
        # Demographics (EEO)
        "gender": ["demographics.gender"],
        "veteran": ["demographics.veteran_status"],
        "veteran status": ["demographics.veteran_status"],
        "disability": ["demographics.disability_status"],
        "disability status": ["demographics.disability_status"],
        "ethnicity": ["demographics.ethnicity"],
        "race": ["demographics.ethnicity"],
    }
    
    # Boolean question patterns
    BOOLEAN_PATTERNS = {
        "yes": [
            r"authorized.*work",
            r"legally.*work",
            r"eligible.*work",
            r"18.*years",
            r"over.*18",
        ],
        "no": [
            r"require.*sponsorship",
            r"need.*sponsorship", 
            r"visa.*sponsorship",
        ],
    }
    
    def __init__(self, applicant: Applicant):
        self.applicant = applicant
        self._cache = {}
    
    def get_value(self, field_label: str) -> Optional[Any]:
        """
        Get the applicant value for a field label.
        
        Args:
            field_label: The form field label text
        
        Returns:
            The matching value from applicant profile, or None
        """
        # Normalize the label
        normalized = self._normalize(field_label)
        
        # Check cache
        if normalized in self._cache:
            return self._cache[normalized]
        
        # Try direct mapping
        value = self._try_direct_mapping(normalized)
        if value is not None:
            self._cache[normalized] = value
            return value
        
        # Try fuzzy matching
        value = self._try_fuzzy_mapping(normalized)
        if value is not None:
            self._cache[normalized] = value
            return value
        
        return None
    
    def _normalize(self, text: str) -> str:
        """Normalize field label for matching"""
        # Lowercase, remove extra whitespace, remove special chars
        text = text.lower().strip()
        text = re.sub(r'[*:\(\)]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _try_direct_mapping(self, label: str) -> Optional[Any]:
        """Try to find a direct mapping for the label"""
        if label in self.FIELD_MAPPINGS:
            paths = self.FIELD_MAPPINGS[label]
            return self._get_from_path(paths)
        return None
    
    def _try_fuzzy_mapping(self, label: str) -> Optional[Any]:
        """Try fuzzy matching for partial matches"""
        for key, paths in self.FIELD_MAPPINGS.items():
            if key in label or label in key:
                value = self._get_from_path(paths)
                if value:
                    return value
        return None
    
    def _get_from_path(self, paths: list) -> Optional[Any]:
        """Get value from applicant using path(s)"""
        for path in paths:
            value = self._extract_value(path)
            if value is not None:
                return value
        return None
    
    def _extract_value(self, path: str) -> Optional[Any]:
        """Extract a value from the applicant object given a dotted path"""
        parts = path.split('.')
        obj = self.applicant
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None
        
        # Convert to string if needed
        if isinstance(obj, bool):
            return obj
        return str(obj) if obj else None
    
    def get_boolean_answer(self, question: str) -> Optional[bool]:
        """
        Determine boolean answer for yes/no questions.
        
        Args:
            question: The question text
        
        Returns:
            True for yes, False for no, None if unclear
        """
        question_lower = question.lower()
        
        # Check patterns that should be "yes"
        for pattern in self.BOOLEAN_PATTERNS["yes"]:
            if re.search(pattern, question_lower):
                # Check if it's about work authorization
                if "authorized" in question_lower or "eligible" in question_lower:
                    return self.applicant.work_authorization.authorized_us
                return True
        
        # Check patterns that should be "no"
        for pattern in self.BOOLEAN_PATTERNS["no"]:
            if re.search(pattern, question_lower):
                # Check sponsorship need
                return self.applicant.work_authorization.requires_sponsorship
        
        return None
    
    def get_dropdown_value(self, options: list[str], field_label: str) -> Optional[str]:
        """
        Select the best matching option from a dropdown.
        
        Args:
            options: Available dropdown options
            field_label: The field label/question
        
        Returns:
            The best matching option
        """
        label_lower = field_label.lower()
        
        # Country selection
        if "country" in label_lower:
            target = self.applicant.address.country
            return self._best_match(options, target)
        
        # State selection
        if "state" in label_lower or "province" in label_lower:
            target = self.applicant.address.state
            return self._best_match(options, target)
        
        # Gender
        if "gender" in label_lower:
            target = self.applicant.demographics.gender
            return self._best_match(options, target)
        
        # Experience level
        if "experience" in label_lower and "year" in label_lower:
            years = self.applicant.years_of_experience
            # Try to match year ranges
            for opt in options:
                if str(years) in opt:
                    return opt
        
        return None
    
    def _best_match(self, options: list[str], target: str) -> Optional[str]:
        """Find the best matching option for a target value"""
        if not target:
            return None
        
        target_lower = target.lower()
        
        # Exact match
        for opt in options:
            if opt.lower() == target_lower:
                return opt
        
        # Contains match
        for opt in options:
            if target_lower in opt.lower() or opt.lower() in target_lower:
                return opt
        
        # First word match
        target_first = target_lower.split()[0] if target_lower else ""
        for opt in options:
            if target_first and target_first in opt.lower():
                return opt
        
        return None
