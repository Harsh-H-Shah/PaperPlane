"""
Prompt templates for generating application answers.
"""

from typing import Optional


class PromptTemplates:
    """
    Collection of prompt templates for common application questions.
    Each template is designed to generate concise, professional answers.
    """
    
    @staticmethod
    def why_this_company(
        company: str,
        job_title: str,
        company_info: str = "",
        applicant_skills: str = "",
    ) -> str:
        """Generate prompt for 'Why do you want to work at X?'"""
        return f"""Write a concise answer (under 300 characters) for why someone wants to work at {company} as a {job_title}.

Company info: {company_info or 'A technology company'}
Candidate skills: {applicant_skills}

Be specific, enthusiastic, and authentic. Mention how their skills align with the company's work.
Do NOT use generic phrases like "I am excited" or "I would love the opportunity".

Answer:"""

    @staticmethod
    def why_this_role(
        job_title: str,
        job_description: str = "",
        applicant_experience: str = "",
    ) -> str:
        """Generate prompt for 'Why are you interested in this role?'"""
        return f"""Write a concise answer (under 300 characters) for why someone is interested in the {job_title} role.

Role description: {job_description[:500] if job_description else 'Software engineering role'}
Their experience: {applicant_experience}

Focus on specific aspects of the role and how their experience is relevant.

Answer:"""

    @staticmethod
    def describe_experience(
        years: int,
        skills: str,
        highlights: str = "",
    ) -> str:
        """Generate prompt for describing relevant experience"""
        return f"""Write a brief professional summary (under 400 characters) of someone's relevant experience.

Years of experience: {years}
Key skills: {skills}
Career highlights: {highlights}

Be specific and quantify achievements where possible.

Summary:"""

    @staticmethod
    def challenging_project(
        project_description: str,
        technologies: str,
    ) -> str:
        """Generate prompt for 'Describe a challenging project'"""
        return f"""Write a concise answer (under 500 characters) describing a challenging technical project.

Project: {project_description}
Technologies used: {technologies}

Use the STAR format briefly: Situation, Task, Action, Result.
Focus on the technical challenge and impact.

Answer:"""

    @staticmethod
    def strength_question(
        skill: str,
        example: str = "",
    ) -> str:
        """Generate prompt for strength-related questions"""
        return f"""Write a concise answer (under 300 characters) about a professional strength.

Strength: {skill}
Example: {example}

Be specific and give a brief concrete example.

Answer:"""

    @staticmethod  
    def weakness_question(
        area: str = "code perfectionism",
    ) -> str:
        """Generate prompt for weakness questions"""
        return f"""Write a concise answer (under 300 characters) about a professional weakness and how it's being addressed.

Area: {area}

Frame it positively, showing self-awareness and growth.

Answer:"""

    @staticmethod
    def generic_question(
        question: str,
        context: str = "",
        max_chars: int = 500,
    ) -> str:
        """Generate prompt for any question"""
        return f"""Answer this job application question concisely (under {max_chars} characters).

Question: {question}

Context about the applicant: {context}

Be professional, specific, and authentic. Avoid generic phrases.

Answer:"""

    @staticmethod
    def cover_letter_paragraph(
        company: str,
        job_title: str,
        key_skills: str,
        specific_interest: str = "",
    ) -> str:
        """Generate a custom paragraph for cover letter"""
        return f"""Write a compelling paragraph (100-150 words) for a cover letter.

Company: {company}
Position: {job_title}
Candidate's key skills: {key_skills}
Specific interest in company: {specific_interest}

Make it personal and specific to this company. Avoid clichés.

Paragraph:"""


# Question type detection patterns
QUESTION_PATTERNS = {
    "why_company": [
        "why do you want to work",
        "why are you interested in",
        "what interests you about",
        "what attracts you to",
    ],
    "why_role": [
        "why this role",
        "why this position",
        "interested in this job",
    ],
    "experience": [
        "describe your experience",
        "tell us about your background",
        "relevant experience",
        "years of experience",
    ],
    "challenging_project": [
        "challenging project",
        "difficult problem",
        "technical challenge",
        "complex project",
    ],
    "strength": [
        "greatest strength",
        "what are you good at",
        "best quality",
        "top skill",
    ],
    "weakness": [
        "greatest weakness",
        "area of improvement",
        "what could you improve",
    ],
}


def detect_question_type(question: str) -> str:
    """
    Detect the type of question based on patterns.
    Returns the question type or 'generic' if unknown.
    """
    question_lower = question.lower()
    
    for qtype, patterns in QUESTION_PATTERNS.items():
        for pattern in patterns:
            if pattern in question_lower:
                return qtype
    
    return "generic"
