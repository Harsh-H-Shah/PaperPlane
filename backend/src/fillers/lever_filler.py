from playwright.async_api import Page

from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller



class LeverFiller(BaseFiller):
    PLATFORM_NAME = "Lever"
    
    SELECTORS = {
        "name": "input[name='name']",
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "org": "input[name='org']",
        "resume": "input[type='file']",
        "urls": "input[name='urls[LinkedIn]'], input[name*='linkedin']",
        "github": "input[name='urls[GitHub]'], input[name*='github']",
        "portfolio": "input[name='urls[Portfolio]'], input[name*='portfolio']",
        "submit": "button[type='submit']",
        "custom_questions": ".application-question, .custom-question",
    }
    
    async def can_handle(self, page: Page) -> bool:
        url = page.url.lower()
        if "lever.co" in url:
            return True
        
        lever_elements = await page.locator("[data-qa='application-form']").count()
        return lever_elements > 0
    
    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        application.start()
        
        try:
            await self.wait_for_page_load(page)
            
            await self._fill_basic_info(page)
            application.add_log("filled_basic", "Filled name, email, phone")
            
            # Resolve resume path
            from pathlib import Path
            resume_path_str = self.applicant.resume.file_path
            resume_path = None
            candidates = [
                Path(resume_path_str),
                Path.cwd().parent / resume_path_str,
                Path(__file__).parent.parent.parent.parent / resume_path_str,
            ]
            for candidate in candidates:
                if candidate.exists():
                    resume_path = str(candidate.resolve())
                    print(f"   📁 Found resume at: {resume_path}")
                    break
            
            if resume_path:
                resume_input = page.locator("input[type='file']").first
                if await resume_input.count() > 0:
                    await resume_input.set_input_files(resume_path)
                    application.resume_uploaded = True
                    application.add_log("uploaded_resume", "Resume uploaded")
                    print("   ✅ Resume uploaded")
                else:
                    print("   ⚠️ No file input found for resume")
            else:
                print("   ❌ Resume file not found")
            
            await self._fill_urls(page)
            await self._handle_custom_questions(page, job, application)
            
            if self.questions_for_review:
                application.questions.extend(self.questions_for_review)
                application.request_review(f"{len(self.questions_for_review)} questions need review")
                return False
            
            application.add_log("ready_submit", "Form filled, ready for review")
            return True
            
        except Exception as e:
            application.fail(str(e))
            return False
    
    async def _fill_basic_info(self, page: Page) -> None:
        name_input = page.locator(self.SELECTORS["name"])
        if await name_input.count() > 0:
            await name_input.fill(self.applicant.full_name)
        
        email_input = page.locator(self.SELECTORS["email"])
        if await email_input.count() > 0:
            await email_input.fill(self.applicant.email)
        
        phone_input = page.locator(self.SELECTORS["phone"])
        if await phone_input.count() > 0:
            await phone_input.fill(self.applicant.phone)
        
        org_input = page.locator(self.SELECTORS["org"])
        if await org_input.count() > 0:
            current = self.applicant.current_job
            if current:
                await org_input.fill(current.company)
    
    async def _fill_urls(self, page: Page) -> None:
        linkedin = page.locator("input[name*='linkedin' i], input[placeholder*='linkedin' i]")
        if await linkedin.count() > 0 and self.applicant.linkedin:
            await linkedin.first.fill(self.applicant.linkedin)
        
        github = page.locator("input[name*='github' i], input[placeholder*='github' i]")
        if await github.count() > 0 and self.applicant.github:
            await github.first.fill(self.applicant.github)
        
        portfolio = page.locator("input[name*='portfolio' i], input[name*='website' i]")
        if await portfolio.count() > 0:
            url = self.applicant.portfolio or self.applicant.website
            if url:
                await portfolio.first.fill(url)
    
    async def _handle_custom_questions(self, page: Page, job: Job, application: Application) -> None:
        questions = page.locator("div.application-question, li.application-additional")
        count = await questions.count()
        
        for i in range(count):
            question_el = questions.nth(i)
            
            label = question_el.locator("label, .application-label")
            if await label.count() == 0:
                continue
            
            question_text = await label.first.text_content()
            if not question_text:
                continue
            
            question_text = question_text.strip()
            
            if any(skip in question_text.lower() for skip in ["name", "email", "phone", "resume", "linkedin", "github"]):
                continue
            
            input_field = question_el.locator("input, textarea, select")
            if await input_field.count() == 0:
                continue
            
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
        options = await field.locator("option").all_text_contents()
        best = await self.field_mapper.get_dropdown_value(options, question)
        if best:
            await field.select_option(label=best)
    
    async def _handle_textarea(self, field, question: str, job: Job, application: Application) -> None:
        answer = self.applicant.get_answer(
            self._question_to_key(question),
            company=job.company,
            position=job.title
        )
        
        if answer:
            await field.fill(answer)
            return
        
        if self.llm_client:
            answer = await self.answer_question_with_llm(question, job, max_length=500)
            if answer:
                await field.fill(answer)
                return
        
        self.add_question_for_review(question, "Long-answer question")
    
    async def _handle_radio(self, container, question: str) -> None:
        bool_answer = self.field_mapper.get_boolean_answer(question)
        
        if bool_answer is not None:
            target = "yes" if bool_answer else "no"
            radio = container.locator(f"input[type='radio'][value*='{target}' i]")
            if await radio.count() > 0:
                await radio.first.click()
                return
        
        self.add_question_for_review(question, "Radio question needs review")
    
    async def _handle_input(self, field, question: str, job: Job) -> None:
        value = await self.field_mapper.get_value(question)
        if value:
            await field.fill(str(value))
            return
        
        bool_answer = self.field_mapper.get_boolean_answer(question)
        if bool_answer is not None:
            await field.fill("Yes" if bool_answer else "No")
            return
        
        self.add_question_for_review(question, "Unknown field")
    
    def _question_to_key(self, question: str) -> str:
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
