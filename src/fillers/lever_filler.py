"""
Lever form filler
"""

from typing import Optional
from playwright.async_api import Page

from src.core.applicant import Applicant
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller
from src.llm.gemini import GeminiClient


class LeverFiller(BaseFiller):
    """
    Form filler for Lever job boards.
    Pattern: jobs.lever.co/company/id
    """
    
    PLATFORM_NAME = "Lever"
    
    SELECTORS = {
        "name": "input[name='name']",
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "org": "input[name='org']",  # Current company
        "resume": "input[type='file']",
        "urls": "input[name='urls[LinkedIn]'], input[name*='linkedin']",
        "github": "input[name='urls[GitHub]'], input[name*='github']",
        "portfolio": "input[name='urls[Portfolio]'], input[name*='portfolio']",
        "submit": "button[type='submit']",
        "custom_questions": ".application-question, .custom-question",
    }
    
    async def can_handle(self, page: Page) -> bool:
        """Check if this is a Lever page"""
        url = page.url.lower()
        if "lever.co" in url:
            return True
        
        # Check for Lever elements
        lever_elements = await page.locator("[data-qa='application-form']").count()
        return lever_elements > 0
    
    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        """Fill out a Lever application form"""
        application.start()
        
        try:
            await self.wait_for_page_load(page)
            
            # Fill basic fields
            await self._fill_basic_info(page)
            application.add_log("filled_basic", "Filled name, email, phone")
            
            # Upload resume
            resume_input = page.locator("input[type='file']").first
            if await resume_input.count() > 0:
                await resume_input.set_input_files(self.applicant.resume.file_path)
                application.resume_uploaded = True
                application.add_log("uploaded_resume", "Resume uploaded")
            
            # Fill URLs
            await self._fill_urls(page)
            
            # Handle custom questions
            await self._handle_custom_questions(page, job, application)
            
            if self.questions_for_review:
                application.questions.extend(self.questions_for_review)
                application.request_review(
                    f"{len(self.questions_for_review)} questions need review"
                )
                return False
            
            application.add_log("ready_submit", "Form filled, ready for review")
            return True
            
        except Exception as e:
            application.fail(str(e))
            return False
    
    async def _fill_basic_info(self, page: Page) -> None:
        """Fill basic contact information"""
        # Full name (Lever uses single name field)
        name_input = page.locator(self.SELECTORS["name"])
        if await name_input.count() > 0:
            await name_input.fill(self.applicant.full_name)
        
        # Email
        email_input = page.locator(self.SELECTORS["email"])
        if await email_input.count() > 0:
            await email_input.fill(self.applicant.email)
        
        # Phone
        phone_input = page.locator(self.SELECTORS["phone"])
        if await phone_input.count() > 0:
            await phone_input.fill(self.applicant.phone)
        
        # Current company (if field exists)
        org_input = page.locator(self.SELECTORS["org"])
        if await org_input.count() > 0:
            current = self.applicant.current_job
            if current:
                await org_input.fill(current.company)
    
    async def _fill_urls(self, page: Page) -> None:
        """Fill LinkedIn, GitHub, Portfolio"""
        # LinkedIn
        linkedin = page.locator("input[name*='linkedin' i], input[placeholder*='linkedin' i]")
        if await linkedin.count() > 0 and self.applicant.linkedin:
            await linkedin.first.fill(self.applicant.linkedin)
        
        # GitHub
        github = page.locator("input[name*='github' i], input[placeholder*='github' i]")
        if await github.count() > 0 and self.applicant.github:
            await github.first.fill(self.applicant.github)
        
        # Portfolio/Website
        portfolio = page.locator("input[name*='portfolio' i], input[name*='website' i]")
        if await portfolio.count() > 0:
            url = self.applicant.portfolio or self.applicant.website
            if url:
                await portfolio.first.fill(url)
    
    async def _handle_custom_questions(
        self, 
        page: Page, 
        job: Job,
        application: Application
    ) -> None:
        """Handle custom application questions"""
        # Lever wraps questions in divs
        questions = page.locator("div.application-question, li.application-additional")
        count = await questions.count()
        
        for i in range(count):
            question_el = questions.nth(i)
            
            # Get question text
            label = question_el.locator("label, .application-label")
            if await label.count() == 0:
                continue
            
            question_text = await label.first.text_content()
            if not question_text:
                continue
            
            question_text = question_text.strip()
            
            # Skip basic fields
            if any(skip in question_text.lower() for skip in 
                   ["name", "email", "phone", "resume", "linkedin", "github"]):
                continue
            
            # Find input
            input_field = question_el.locator("input, textarea, select")
            if await input_field.count() == 0:
                continue
            
            # Get field type
            tag = await input_field.first.evaluate("el => el.tagName.toLowerCase()")
            input_type = await input_field.first.get_attribute("type") or "text"
            
            if tag == "select":
                await self._handle_dropdown(input_field.first, question_text, job)
            elif tag == "textarea":
                await self._handle_textarea(input_field.first, question_text, job, application)
            elif input_type == "radio":
                await self._handle_radio(question_el, question_text)
            else:
                await self._handle_input(input_field.first, question_text, job)
    
    async def _handle_dropdown(self, field, question: str, job: Job) -> None:
        """Handle dropdown selection"""
        options = await field.locator("option").all_text_contents()
        best = self.field_mapper.get_dropdown_value(options, question)
        if best:
            await field.select_option(label=best)
    
    async def _handle_textarea(self, field, question: str, job: Job, application: Application) -> None:
        """Handle long-answer questions"""
        # Try pre-defined answers
        answer = self.applicant.get_answer(
            self._question_to_key(question),
            company=job.company,
            position=job.title
        )
        
        if answer:
            await field.fill(answer)
            return
        
        # Try LLM
        if self.llm_client:
            answer = await self.answer_question_with_llm(question, job, max_length=500)
            if answer:
                await field.fill(answer)
                return
        
        # Flag for review
        self.add_question_for_review(question, "Long-answer question")
    
    async def _handle_radio(self, container, question: str) -> None:
        """Handle radio button questions"""
        # Check for yes/no questions
        bool_answer = self.field_mapper.get_boolean_answer(question)
        
        if bool_answer is not None:
            target = "yes" if bool_answer else "no"
            radio = container.locator(f"input[type='radio'][value*='{target}' i]")
            if await radio.count() > 0:
                await radio.first.click()
                return
        
        # Flag for review
        self.add_question_for_review(question, "Radio question needs review")
    
    async def _handle_input(self, field, question: str, job: Job) -> None:
        """Handle text input fields"""
        value = self.field_mapper.get_value(question)
        if value:
            await field.fill(str(value))
            return
        
        bool_answer = self.field_mapper.get_boolean_answer(question)
        if bool_answer is not None:
            await field.fill("Yes" if bool_answer else "No")
            return
        
        self.add_question_for_review(question, "Unknown field")
    
    def _question_to_key(self, question: str) -> str:
        """Convert question to key for common_answers"""
        q = question.lower()
        if "why" in q and "company" in q:
            return "why_this_company"
        if "why" in q and ("role" in q or "position" in q):
            return "why_this_role"
        if "strength" in q:
            return "greatest_strength"
        if "weakness" in q:
            return "greatest_weakness"
        return ""
