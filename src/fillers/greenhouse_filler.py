"""
Greenhouse job board form filler
"""

from typing import Optional
from playwright.async_api import Page

from src.core.applicant import Applicant
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller
from src.llm.gemini import GeminiClient


class GreenhouseFiller(BaseFiller):
    """
    Form filler for Greenhouse job boards.
    Pattern: boards.greenhouse.io/company/jobs/id
    """
    
    PLATFORM_NAME = "Greenhouse"
    
    # Common Greenhouse selectors
    SELECTORS = {
        "first_name": "#first_name",
        "last_name": "#last_name",
        "email": "#email",
        "phone": "#phone",
        "resume": "input[type='file'][name*='resume']",
        "cover_letter": "input[type='file'][name*='cover']",
        "linkedin": "input[name*='linkedin'], input[id*='linkedin']",
        "github": "input[name*='github'], input[id*='github']",
        "website": "input[name*='website'], input[id*='website']",
        "submit": "button[type='submit'], input[type='submit']",
        "custom_questions": ".field, .custom-question",
    }
    
    async def can_handle(self, page: Page) -> bool:
        """Check if this is a Greenhouse page"""
        url = page.url.lower()
        if "greenhouse.io" in url:
            return True
        
        # Check for Greenhouse elements
        gh_elements = await page.locator("[data-source='greenhouse']").count()
        return gh_elements > 0
    
    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        """Fill out a Greenhouse application form"""
        application.start()
        
        try:
            # Wait for form to load
            await self.wait_for_page_load(page)
            
            # Fill basic fields
            await self._fill_basic_info(page)
            application.add_log("filled_basic", "Filled name, email, phone")
            
            # Upload resume
            await self._upload_resume(page)
            application.resume_uploaded = True
            application.add_log("uploaded_resume", "Resume uploaded")
            
            # Fill online presence
            await self._fill_online_presence(page)
            
            # Handle custom questions
            await self._handle_custom_questions(page, job, application)
            
            # Check for questions needing review
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
        await self.fill_text_field(
            page, 
            self.SELECTORS["first_name"], 
            self.applicant.first_name
        )
        await self.fill_text_field(
            page, 
            self.SELECTORS["last_name"], 
            self.applicant.last_name
        )
        await self.fill_text_field(
            page, 
            self.SELECTORS["email"], 
            self.applicant.email
        )
        await self.fill_text_field(
            page, 
            self.SELECTORS["phone"], 
            self.applicant.phone
        )
    
    async def _upload_resume(self, page: Page) -> bool:
        """Upload resume file"""
        resume_path = self.applicant.resume.file_path
        return await self.upload_file(page, self.SELECTORS["resume"], resume_path)
    
    async def _fill_online_presence(self, page: Page) -> None:
        """Fill LinkedIn, GitHub, website fields"""
        if self.applicant.linkedin:
            await self.fill_text_field(
                page, 
                self.SELECTORS["linkedin"], 
                self.applicant.linkedin
            )
        
        if self.applicant.github:
            await self.fill_text_field(
                page, 
                self.SELECTORS["github"], 
                self.applicant.github
            )
        
        if self.applicant.portfolio or self.applicant.website:
            website = self.applicant.portfolio or self.applicant.website
            await self.fill_text_field(page, self.SELECTORS["website"], website)
    
    async def _handle_custom_questions(
        self, 
        page: Page, 
        job: Job,
        application: Application
    ) -> None:
        """Handle custom application questions"""
        # Find all question fields
        questions = page.locator("div.field, div.custom-question, .application-question")
        count = await questions.count()
        
        for i in range(count):
            question_el = questions.nth(i)
            
            # Get the question text
            label = question_el.locator("label")
            if await label.count() > 0:
                question_text = await label.text_content()
            else:
                continue
            
            if not question_text:
                continue
            
            question_text = question_text.strip()
            
            # Skip if already filled (name, email, etc.)
            if any(skip in question_text.lower() for skip in 
                   ["first name", "last name", "email", "phone", "resume"]):
                continue
            
            # Find the input field
            input_field = question_el.locator("input, textarea, select")
            if await input_field.count() == 0:
                continue
            
            # Determine field type
            tag = await input_field.evaluate("el => el.tagName.toLowerCase()")
            
            if tag == "select":
                await self._handle_dropdown(input_field, question_text)
            elif tag == "textarea":
                await self._handle_textarea(input_field, question_text, job, application)
            else:
                await self._handle_input(input_field, question_text, job)
    
    async def _handle_dropdown(self, field, question: str) -> None:
        """Handle dropdown selection"""
        # Get options
        options = await field.locator("option").all_text_contents()
        
        # Use field mapper to select best option
        best_option = self.field_mapper.get_dropdown_value(options, question)
        if best_option:
            await field.select_option(label=best_option)
    
    async def _handle_textarea(
        self, 
        field, 
        question: str, 
        job: Job,
        application: Application
    ) -> None:
        """Handle long-answer questions"""
        # Check for pre-defined answers
        common_answer = self.applicant.get_answer(
            self._question_to_key(question),
            company=job.company,
            position=job.title
        )
        
        if common_answer:
            await field.fill(common_answer)
            return
        
        # Use LLM if available
        if self.llm_client:
            answer = await self.answer_question_with_llm(question, job, max_length=500)
            if answer:
                await field.fill(answer)
                application.add_question(
                    question_text=question,
                    question_type="textarea",
                )
                application.answer_question(
                    len(application.questions) - 1,
                    answer,
                    "llm"
                )
                return
        
        # Flag for human review
        self.add_question_for_review(
            question_text=question,
            reason="Long-answer question needs human review"
        )
    
    async def _handle_input(self, field, question: str, job: Job) -> None:
        """Handle text input fields"""
        # Try field mapper first
        value = self.field_mapper.get_value(question)
        if value:
            await field.fill(str(value))
            return
        
        # Check for boolean questions
        bool_answer = self.field_mapper.get_boolean_answer(question)
        if bool_answer is not None:
            await field.fill("Yes" if bool_answer else "No")
            return
        
        # Flag unknown fields
        self.add_question_for_review(
            question_text=question,
            reason="Unknown field type"
        )
    
    def _question_to_key(self, question: str) -> str:
        """Convert question to key for common_answers lookup"""
        q = question.lower()
        if "why" in q and "company" in q:
            return "why_this_company"
        if "why" in q and ("role" in q or "position" in q):
            return "why_this_role"
        if "strength" in q:
            return "greatest_strength"
        if "weakness" in q:
            return "greatest_weakness"
        if "salary" in q:
            return "salary_expectations"
        return ""
