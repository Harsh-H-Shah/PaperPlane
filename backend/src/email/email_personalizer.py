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
                max_tokens=100,
                temperature=0.7  # Some creativity
            )
            
            if response:
                # Clean up response
                hook = response.strip()
                hook = hook.replace('"', '').replace("'", "")
                
                # Ensure it's not too long
                if len(hook) > max_length:
                    hook = hook[:max_length].rsplit(' ', 1)[0] + "..."
                
                return hook
                
        except Exception as e:
            print(f"   ⚠️ Personalization error: {e}")
        
        return self._get_fallback_hook(contact)
    
    def _build_hook_prompt(self, contact: Contact, job = None) -> str:
        """Build the prompt for generating personalized hook"""
        
        persona_context = {
            ContactPersona.RECRUITER: "a recruiter who screens candidates",
            ContactPersona.HIRING_MANAGER: "a hiring manager making final decisions",
            ContactPersona.ENGINEERING_MANAGER: "an engineering manager focused on team fit",
            ContactPersona.HR: "an HR professional managing the hiring process",
            ContactPersona.TALENT_ACQUISITION: "a talent acquisition specialist sourcing candidates",
        }
        
        role_context = persona_context.get(
            contact.persona, 
            "a professional at this company"
        )
        
        job_context = ""
        if job:
            job_context = f"The candidate applied for: {job.title}"
        
        prompt = f"""Write a single, professional opening line for a cold email to {contact.first_name}, who is {role_context} at {contact.company}.

Context:
- Recipient: {contact.name}, {contact.title}
- Company: {contact.company}
{job_context}

Requirements:
- Be warm but professional
- Show genuine interest in the company
- Don't be overly flattering or salesy
- Keep it concise (1-2 sentences max)
- Don't mention applying or job search directly
- Focus on connection or shared interest

Write ONLY the opening line, nothing else:"""
        
        return prompt
    
    def _get_fallback_hook(self, contact: Contact) -> str:
        """Get a fallback hook when LLM is unavailable"""
        
        fallbacks = {
            ContactPersona.RECRUITER: f"I hope this finds you well! I came across {contact.company}'s team and was impressed by what you're building.",
            
            ContactPersona.HIRING_MANAGER: f"I've been following {contact.company}'s work and am excited about the direction your team is taking.",
            
            ContactPersona.ENGINEERING_MANAGER: f"As a fellow engineer, I've been impressed by the technical challenges {contact.company} is tackling.",
            
            ContactPersona.HR: f"I hope you're having a great week! I wanted to reach out about opportunities at {contact.company}.",
            
            ContactPersona.TALENT_ACQUISITION: f"I've heard great things about {contact.company}'s culture and wanted to connect.",
        }
        
        return fallbacks.get(
            contact.persona,
            f"I came across {contact.company} and was impressed by what your team is building."
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
        # Generate hook
        hook = await self.generate_personalized_hook(contact, job)
        
        # Replace placeholder
        personalized_body = body.replace("{personalized_hook}", hook)
        
        return subject, personalized_body
    
    def generate_subject_variation(
        self,
        base_subject: str,
        contact: Contact
    ) -> str:
        """Generate a slight variation of the subject line"""
        
        # Simple variations - could be enhanced with LLM
        variations = [
            base_subject,
            f"Quick Question - {base_subject}",
            f"Re: {base_subject}",
        ]
        
        # Pick based on contact persona for consistency
        idx = hash(contact.email) % len(variations)
        return variations[idx]
