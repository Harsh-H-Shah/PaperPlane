import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class Address(BaseModel):
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
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state


class WorkAuthorization(BaseModel):
    authorized_us: bool = True
    requires_sponsorship: bool = False
    visa_status: str = "US Citizen"
    clearance: str = "None"


class Demographics(BaseModel):
    gender: str = "Prefer not to say"
    ethnicity: str = "Prefer not to say"
    veteran_status: str = "I am not a protected veteran"
    disability_status: str = "I do not have a disability"


class SalaryPreference(BaseModel):
    min: int = 0
    max: int = 0
    currency: str = "USD"
    
    def __str__(self) -> str:
        if self.min and self.max:
            return f"${self.min:,} - ${self.max:,} {self.currency}"
        return "Negotiable"


class Preferences(BaseModel):
    desired_salary: SalaryPreference = Field(default_factory=SalaryPreference)
    work_type: list[str] = Field(default_factory=lambda: ["Remote", "Hybrid"])
    willing_to_relocate: bool = False
    available_start_date: str = "2 weeks notice"
    open_to_contract: bool = False


class Experience(BaseModel):
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
        return f"{self.start_date} - {self.end_date}"


class Education(BaseModel):
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
        return f"{self.degree} in {self.field}"


class Skill(BaseModel):
    name: str
    level: str = "Intermediate"
    years: int = 0


class Skills(BaseModel):
    programming_languages: list[Skill] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud_devops: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    
    @property
    def all_technical(self) -> list[str]:
        skills = [s.name for s in self.programming_languages]
        skills.extend(self.frameworks)
        skills.extend(self.databases)
        skills.extend(self.cloud_devops)
        skills.extend(self.tools)
        return skills
    
    @property
    def top_languages(self) -> list[str]:
        sorted_langs = sorted(self.programming_languages, key=lambda x: x.years, reverse=True)
        return [lang.name for lang in sorted_langs[:5]]


class Project(BaseModel):
    name: str
    description: str = ""
    url: str = ""
    date_range: str = ""
    technologies: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str
    issuer: str
    date: str = ""
    expiry: str = ""
    url: str = ""


class Language(BaseModel):
    language: str
    proficiency: str = "Native"


class Resume(BaseModel):
    file_path: str = "data/resume.pdf"
    last_updated: str = ""


class Achievement(BaseModel):
    name: str
    description: str
    year: str = ""


class Applicant(BaseModel):
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    full_name: str = Field(default="")
    email: str = Field(default="")
    phone: str = Field(default="")
    address: Address = Field(default_factory=Address)
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    website: str = ""
    work_authorization: WorkAuthorization = Field(default_factory=WorkAuthorization)
    demographics: Demographics = Field(default_factory=Demographics)
    preferences: Preferences = Field(default_factory=Preferences)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    projects: list[Project] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    resume: Resume = Field(default_factory=Resume)
    cover_letter_template: str = ""
    common_answers: dict[str, str] = Field(default_factory=dict)
    
    def get_full_context(self) -> str:
        """Returns a comprehensive summary of the applicant for LLM context."""
        context = {
            "personal": {
                "name": self.full_name,
                "email": self.email,
                "phone": self.phone,
                "location": str(self.address)
            },
            "education": [
                {
                    "institution": edu.institution,
                    "degree": edu.degree,
                    "field": edu.field,
                    "location": edu.location,
                    "dates": f"{edu.start_date} - {edu.end_date}"
                } for edu in self.education
            ],
            "experience": [
                {
                    "company": exp.company,
                    "title": exp.title,
                    "dates": exp.duration,
                    "description": exp.description,
                    "highlights": exp.highlights,
                    "technologies": exp.technologies
                } for exp in self.experience
            ],
            "skills": {
                "technical": self.skills.all_technical,
                "soft": self.skills.soft_skills
            },
            "projects": [
                {
                    "name": proj.name,
                    "description": proj.description,
                    "tech": proj.technologies
                } for proj in self.projects
            ],
            "common_answers": self.common_answers
        }
        return json.dumps(context, indent=2)
    
    @classmethod
    def from_file(cls, path: str | Path) -> "Applicant":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        if 'personal' in data:
            personal = data.pop('personal')
            data.update(personal)
        
        return cls(**data)
    
    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)
    
    @property
    def years_of_experience(self) -> int:
        return len(self.experience) * 2
    
    @property
    def current_job(self) -> Optional[Experience]:
        for exp in self.experience:
            if exp.current:
                return exp
        return self.experience[0] if self.experience else None
    
    @property
    def highest_education(self) -> Optional[Education]:
        return self.education[0] if self.education else None
    
    def get_skills_string(self, max_skills: int = 10) -> str:
        skills = self.skills.all_technical[:max_skills]
        return ", ".join(skills)
    
    def get_answer(self, question_key: str, **kwargs) -> Optional[str]:
        answer = self.common_answers.get(question_key)
        if answer:
            return answer.format(**kwargs)
        return None
    
    def generate_cover_letter(self, company: str, position: str, custom_paragraph: str = "") -> str:
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
