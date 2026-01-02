"""
Applicant data model - represents the user applying for jobs
"""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class Address(BaseModel):
    """Physical address"""
    street: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "United States"
    
    def __str__(self) -> str:
        parts = [p for p in [self.street, self.city, self.state, self.zip, self.country] if p]
        return ", ".join(parts)
    
    @property
    def city_state(self) -> str:
        """City, State format"""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state


class WorkAuthorization(BaseModel):
    """Work authorization status"""
    authorized_us: bool = True
    requires_sponsorship: bool = False
    visa_status: str = "US Citizen"
    clearance: str = "None"


class Demographics(BaseModel):
    """Demographic information (for EEO questions)"""
    gender: str = "Prefer not to say"
    ethnicity: str = "Prefer not to say"
    veteran_status: str = "I am not a protected veteran"
    disability_status: str = "I do not have a disability"


class SalaryPreference(BaseModel):
    """Salary preferences"""
    min: int = 0
    max: int = 0
    currency: str = "USD"
    
    def __str__(self) -> str:
        if self.min and self.max:
            return f"${self.min:,} - ${self.max:,} {self.currency}"
        return "Negotiable"


class Preferences(BaseModel):
    """Job preferences"""
    desired_salary: SalaryPreference = Field(default_factory=SalaryPreference)
    work_type: list[str] = Field(default_factory=lambda: ["Remote", "Hybrid"])
    willing_to_relocate: bool = False
    available_start_date: str = "2 weeks notice"
    open_to_contract: bool = False


class Experience(BaseModel):
    """Work experience entry"""
    company: str
    title: str
    location: str = ""
    start_date: str
    end_date: str = "Present"
    current: bool = False
    description: str = ""
    highlights: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    
    @property
    def duration(self) -> str:
        """Human readable duration"""
        return f"{self.start_date} - {self.end_date}"


class Education(BaseModel):
    """Education entry"""
    institution: str
    degree: str
    field: str
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    honors: list[str] = Field(default_factory=list)
    relevant_coursework: list[str] = Field(default_factory=list)
    
    @property
    def full_degree(self) -> str:
        """Full degree string"""
        return f"{self.degree} in {self.field}"


class Skill(BaseModel):
    """Programming language or skill with proficiency"""
    name: str
    level: str = "Intermediate"  # Beginner, Intermediate, Advanced, Expert
    years: int = 0


class Skills(BaseModel):
    """All skills"""
    programming_languages: list[Skill] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud_devops: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    
    @property
    def all_technical(self) -> list[str]:
        """Get all technical skills as a flat list"""
        skills = [s.name for s in self.programming_languages]
        skills.extend(self.frameworks)
        skills.extend(self.databases)
        skills.extend(self.cloud_devops)
        skills.extend(self.tools)
        return skills
    
    @property
    def top_languages(self) -> list[str]:
        """Get top programming languages by experience"""
        sorted_langs = sorted(self.programming_languages, key=lambda x: x.years, reverse=True)
        return [lang.name for lang in sorted_langs[:5]]


class Project(BaseModel):
    """Personal or professional project"""
    name: str
    description: str = ""
    url: str = ""
    technologies: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    """Professional certification"""
    name: str
    issuer: str
    date: str = ""
    expiry: str = ""
    url: str = ""


class Language(BaseModel):
    """Language proficiency"""
    language: str
    proficiency: str = "Native"  # Native, Fluent, Conversational, Basic


class Resume(BaseModel):
    """Resume file information"""
    file_path: str = "data/resume.pdf"
    last_updated: str = ""


class Applicant(BaseModel):
    """
    Complete applicant profile containing all information needed for job applications.
    """
    # Personal info
    first_name: str = Field(default="", description="First name")
    last_name: str = Field(default="", description="Last name")
    full_name: str = Field(default="", description="Full name")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    address: Address = Field(default_factory=Address)
    
    # Online presence
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    website: str = ""
    
    # Work authorization
    work_authorization: WorkAuthorization = Field(default_factory=WorkAuthorization)
    
    # Demographics (for EEO)
    demographics: Demographics = Field(default_factory=Demographics)
    
    # Preferences
    preferences: Preferences = Field(default_factory=Preferences)
    
    # Experience & Education
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    
    # Skills
    skills: Skills = Field(default_factory=Skills)
    
    # Projects & Certifications
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    
    # Languages
    languages: list[Language] = Field(default_factory=list)
    
    # Resume
    resume: Resume = Field(default_factory=Resume)
    
    # Cover letter template
    cover_letter_template: str = ""
    
    # Common answers for frequently asked questions
    common_answers: dict[str, str] = Field(default_factory=dict)
    
    @classmethod
    def from_file(cls, path: str | Path) -> "Applicant":
        """Load applicant profile from JSON file"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Handle nested personal section
        if 'personal' in data:
            personal = data.pop('personal')
            data.update(personal)
        
        return cls(**data)
    
    def save(self, path: str | Path) -> None:
        """Save profile to JSON file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)
    
    @property
    def years_of_experience(self) -> int:
        """Calculate total years of experience"""
        # Simple calculation - can be made more accurate
        return len(self.experience) * 2  # Rough estimate
    
    @property
    def current_job(self) -> Optional[Experience]:
        """Get current job if any"""
        for exp in self.experience:
            if exp.current:
                return exp
        return self.experience[0] if self.experience else None
    
    @property
    def highest_education(self) -> Optional[Education]:
        """Get highest education level"""
        return self.education[0] if self.education else None
    
    def get_skills_string(self, max_skills: int = 10) -> str:
        """Get skills as comma-separated string"""
        skills = self.skills.all_technical[:max_skills]
        return ", ".join(skills)
    
    def get_answer(self, question_key: str, **kwargs) -> Optional[str]:
        """
        Get a pre-defined answer for common questions.
        Supports template variables like {company}, {position}.
        """
        answer = self.common_answers.get(question_key)
        if answer:
            return answer.format(**kwargs)
        return None
    
    def generate_cover_letter(self, company: str, position: str, custom_paragraph: str = "") -> str:
        """Generate a cover letter from template"""
        if not self.cover_letter_template:
            return ""
        
        return self.cover_letter_template.format(
            name=self.full_name,
            company=company,
            position=position,
            years=self.years_of_experience,
            skills=self.get_skills_string(5),
            custom_paragraph=custom_paragraph
        )
    
    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"
