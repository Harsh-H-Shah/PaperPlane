"""
Context builder - creates context for LLM prompts from applicant profile.
"""

from typing import Optional
from src.core.applicant import Applicant
from src.core.job import Job


class ContextBuilder:
    """
    Builds context strings from applicant profile and job data
    for use in LLM prompts.
    """
    
    def __init__(self, applicant: Applicant):
        self.applicant = applicant
    
    def build_applicant_summary(self, max_chars: int = 500) -> str:
        """Build a concise summary of the applicant's background"""
        parts = []
        
        # Basic info
        if self.applicant.full_name:
            parts.append(f"Name: {self.applicant.full_name}")
        
        # Current role
        current = self.applicant.current_job
        if current:
            parts.append(f"Current: {current.title} at {current.company}")
        
        # Experience
        years = self.applicant.years_of_experience
        parts.append(f"Experience: ~{years} years")
        
        # Education
        edu = self.applicant.highest_education
        if edu:
            parts.append(f"Education: {edu.full_degree} from {edu.institution}")
        
        # Top skills
        skills = self.applicant.get_skills_string(8)
        if skills:
            parts.append(f"Skills: {skills}")
        
        summary = "\n".join(parts)
        return summary[:max_chars] if len(summary) > max_chars else summary
    
    def build_experience_context(self, max_chars: int = 800) -> str:
        """Build detailed experience context"""
        parts = []
        
        for exp in self.applicant.experience[:3]:  # Top 3 experiences
            exp_text = f"- {exp.title} at {exp.company} ({exp.duration})"
            if exp.highlights:
                exp_text += f": {'; '.join(exp.highlights[:2])}"
            parts.append(exp_text)
        
        return "\n".join(parts)[:max_chars]
    
    def build_skills_context(self) -> str:
        """Build skills context"""
        skills = self.applicant.skills
        parts = []
        
        # Programming languages with levels
        if skills.programming_languages:
            langs = [f"{s.name} ({s.level})" for s in skills.programming_languages[:5]]
            parts.append(f"Languages: {', '.join(langs)}")
        
        # Frameworks
        if skills.frameworks:
            parts.append(f"Frameworks: {', '.join(skills.frameworks[:5])}")
        
        # Cloud/DevOps
        if skills.cloud_devops:
            parts.append(f"Cloud/DevOps: {', '.join(skills.cloud_devops[:4])}")
        
        return "\n".join(parts)
    
    def build_job_context(self, job: Job) -> str:
        """Build context about the job being applied to"""
        parts = [
            f"Position: {job.title}",
            f"Company: {job.company}",
        ]
        
        if job.location:
            parts.append(f"Location: {job.location}")
        
        if job.description:
            # Truncate description
            desc = job.description[:300]
            if len(job.description) > 300:
                desc += "..."
            parts.append(f"About: {desc}")
        
        return "\n".join(parts)
    
    def build_full_context(self, job: Optional[Job] = None, max_chars: int = 1000) -> str:
        """Build complete context for answering questions"""
        parts = [
            "=== Applicant ===",
            self.build_applicant_summary(400),
            "",
            "=== Skills ===",
            self.build_skills_context(),
        ]
        
        if job:
            parts.extend([
                "",
                "=== Target Position ===",
                self.build_job_context(job),
            ])
        
        full = "\n".join(parts)
        return full[:max_chars] if len(full) > max_chars else full
    
    def get_common_answer(self, question_key: str, **kwargs) -> Optional[str]:
        """Get a pre-defined answer if available"""
        return self.applicant.get_answer(question_key, **kwargs)
