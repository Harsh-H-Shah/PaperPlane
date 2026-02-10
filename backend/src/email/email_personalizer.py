"""
Email Personalizer - Uses Gemini AI to generate personalized email hooks.
Creates context-aware openers based on recipient role, company, and job.
"""
from typing import Optional

from src.core.cold_email_models import Contact, ContactPersona
from src.llm.gemini import GeminiClient


class EmailPersonalizer:
    """Generates personalized email content using Gemini"""
    
    def __init__(self, llm_client: GeminiClient = None):
        self.llm_client = llm_client
        
        if not self.llm_client:
            try:
                self.llm_client = GeminiClient()
            except Exception as e:
                print(f"   ⚠️ EmailPersonalizer: LLM not available: {e}")
    
    async def generate_personalized_hook(
        self,
        contact: Contact,
        job = None,
        max_length: int = 150
    ) -> str:
        """
        Generate a personalized opening line for the email.
        This appears as {personalized_hook} in templates.
        """
        if not self.llm_client:
            return self._get_fallback_hook(contact)
        
        try:
            prompt = self._build_hook_prompt(contact, job)
            
            response = self.llm_client.generate(
                prompt,
                max_tokens=80,
                temperature=0.6
            )
            
            if response:
                hook = response.strip()
                hook = hook.replace('"', '').replace("'", "")
                
                if len(hook) > max_length:
                    hook = hook[:max_length].rsplit(' ', 1)[0] + "..."
                
                return hook
                
        except Exception as e:
            print(f"   ⚠️ Personalization error: {e}")
        
        return self._get_fallback_hook(contact)
    
    def _build_hook_prompt(self, contact: Contact, job = None) -> str:
        """Build the prompt for generating personalized hook"""
        
        persona_context = {
            ContactPersona.RECRUITER: "a recruiter",
            ContactPersona.HIRING_MANAGER: "a hiring manager",
            ContactPersona.ENGINEERING_MANAGER: "an engineering manager",
            ContactPersona.HR: "an HR professional",
            ContactPersona.TALENT_ACQUISITION: "a talent acquisition specialist",
        }
        
        role_context = persona_context.get(
            contact.persona, 
            "a professional"
        )
        
        job_context = ""
        if job:
            job_context = f"The sender applied for: {job.title}"
        
        company = (contact.company if contact else "") or "the company"
        
        prompt = f"""Write ONE short, natural opening line for a cold email to {contact.first_name} ({role_context} at {company}).

Context:
- Recipient: {contact.name}, {contact.title}
- Company: {company}
{job_context}

Rules:
- 1 sentence max, under 20 words
- Sound like a real person, not a bot
- No "I hope this finds you well" or "I hope you're doing well"
- No excessive flattery or buzzwords
- Reference something specific about the company if possible
- Casual-professional tone — like messaging a colleague you haven't met yet

Write ONLY the line, nothing else:"""
        
        return prompt
    
    def _get_fallback_hook(self, contact: Contact) -> str:
        """Fallback hooks that sound human, not AI-generated"""
        company = (contact.company if contact else "") or "your company"
        
        fallbacks = {
            ContactPersona.RECRUITER: f"I came across the role at {company} and it caught my eye.",
            ContactPersona.HIRING_MANAGER: f"I've been looking into {company}'s engineering work and it's impressive stuff.",
            ContactPersona.ENGINEERING_MANAGER: f"I've been following what {company}'s engineering team has been shipping — really solid work.",
            ContactPersona.HR: f"I saw {company} is hiring and wanted to reach out.",
            ContactPersona.TALENT_ACQUISITION: f"I came across {company}'s open roles and wanted to connect.",
        }
        
        return fallbacks.get(
            contact.persona if contact else ContactPersona.UNKNOWN,
            f"I came across {company} and wanted to reach out."
        )
    
    async def personalize_email(
        self,
        subject: str,
        body: str,
        contact: Contact,
        job = None
    ) -> tuple[str, str]:
        """
        Fully personalize an email subject and body.
        Returns (personalized_subject, personalized_body) tuple.
        """
        hook = await self.generate_personalized_hook(contact, job)
        personalized_body = body.replace("{personalized_hook}", hook)
        return subject, personalized_body
    
    def generate_subject_variation(
        self,
        base_subject: str,
        contact: Contact
    ) -> str:
        """Generate a slight variation of the subject line"""
        variations = [
            base_subject,
            f"Quick Question - {base_subject}",
            f"Re: {base_subject}",
        ]
        
        idx = hash(contact.email) % len(variations)
        return variations[idx]
