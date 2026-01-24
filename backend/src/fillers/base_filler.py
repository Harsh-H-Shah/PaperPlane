from abc import ABC, abstractmethod
from typing import Optional
from playwright.async_api import Page

from src.core.applicant import Applicant
from src.core.application import Application, ApplicationQuestion
from src.core.job import Job
from src.fillers.field_mapper import FieldMapper
from src.llm.gemini import GeminiClient
from src.llm.context_builder import ContextBuilder
from src.llm.answer_validator import AnswerValidator


class BaseFiller(ABC):
    PLATFORM_NAME = "Base"
    
    def __init__(self, applicant: Applicant, llm_client: Optional[GeminiClient] = None):
        self.applicant = applicant
        self.llm_client = llm_client
        self.field_mapper = FieldMapper(applicant, llm_client)
        self.context_builder = ContextBuilder(applicant)
        self.validator = AnswerValidator()
        self.questions_for_review: list[ApplicationQuestion] = []
    
    @abstractmethod
    async def can_handle(self, page: Page) -> bool:
        pass
    
    @abstractmethod
    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        pass
    
    async def fill_text_field(self, page: Page, selector: str, value: str, clear_first: bool = True) -> bool:
        try:
            element = page.locator(selector)
            if await element.count() == 0:
                return False
            
            if clear_first:
                await element.clear()
            
            await element.fill(value)
            return True
        except Exception:
            return False
    
    async def click_button(self, page: Page, selector: str) -> bool:
        try:
            element = page.locator(selector)
            if await element.count() == 0:
                return False
            
            await element.click()
            return True
        except Exception:
            return False
    
    async def select_dropdown(self, page: Page, selector: str, value: str) -> bool:
        try:
            element = page.locator(selector)
            if await element.count() == 0:
                return False
            
            await element.select_option(value=value)
            return True
        except Exception:
            return False
    
    async def upload_file(self, page: Page, selector: str, file_path: str) -> bool:
        try:
            element = page.locator(selector)
            if await element.count() == 0:
                return False
            
            await element.set_input_files(file_path)
            return True
        except Exception:
            return False
    
    async def get_field_label(self, page: Page, field_selector: str) -> Optional[str]:
        try:
            field = page.locator(field_selector)
            field_id = await field.get_attribute("id")
            
            if field_id:
                label = page.locator(f"label[for='{field_id}']")
                if await label.count() > 0:
                    return await label.text_content()
            
            parent_label = field.locator("xpath=ancestor::label")
            if await parent_label.count() > 0:
                return await parent_label.text_content()
            
            aria_label = await field.get_attribute("aria-label")
            if aria_label:
                return aria_label
            
            placeholder = await field.get_attribute("placeholder")
            if placeholder:
                return placeholder
            
            return None
        except Exception:
            return None
    
    async def fill_field_auto(self, page: Page, field_selector: str, job: Optional[Job] = None) -> bool:
        label = await self.get_field_label(page, field_selector)
        if not label:
            return False
        
        value = await self.field_mapper.get_value(label)
        if value:
            return await self.fill_text_field(page, field_selector, str(value))
        
        return False
    
    async def answer_question_with_llm(self, question: str, job: Job, max_length: int = 500) -> Optional[str]:
        if not self.llm_client:
            return None
        
        needs_review, reason = self.validator.needs_human_review(question)
        if needs_review:
            return None
        
        context = self.context_builder.build_full_context(job, max_chars=800)
        
        answer = await self.llm_client.answer_application_question(
            question=question,
            job_title=job.title,
            company=job.company,
            applicant_context=context,
            max_length=max_length
        )
        
        if answer:
            validation = self.validator.validate(answer=answer, question=question, max_length=max_length)
            
            if validation.needs_human_review:
                return None
            
            answer = self.validator.improve_answer(answer, validation.issues)
            return answer
        
        return None
    
    def add_question_for_review(self, question_text: str, reason: str, field_name: str = "") -> None:
        q = ApplicationQuestion(
            question_text=question_text,
            field_name=field_name,
            needs_review=True,
            review_reason=reason,
        )
        self.questions_for_review.append(q)
    
    async def wait_for_page_load(self, page: Page, timeout: int = 10000) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass
