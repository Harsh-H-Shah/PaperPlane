from typing import Optional, List, Dict, Any
from playwright.async_api import Page, ElementHandle
import json
import asyncio

from src.core.applicant import Applicant
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller
from src.llm.gemini import GeminiClient
from src.utils.logger import logger

class UniversalFiller(BaseFiller):
    PLATFORM_NAME = "Universal"
    
    # Common success indicators - moved to more specific patterns
    SUCCESS_URL_PARTS = ["confirmation", "application-submitted", "thank-you-for-applying"]
    SUCCESS_TEXTS = [
        "application submitted successfully", 
        "thank you for applying", 
        "your application was received",
        "has been received",
        "successfully submitted"
    ]
    
    def __init__(self, applicant: Applicant, llm_client: Optional[GeminiClient] = None):
        super().__init__(applicant, llm_client)
        self.processed_fields = set()

    async def can_handle(self, page: Page) -> bool:
        # Acts as a catch-all filler
        return True
    
    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        """
        Generic filling logic:
        1. Analyze page to find form fields
        2. Map fields to applicant data using LLM
        3. Fill fields
        4. Look for submit button
        """
        application.start()
        
        try:
            await self.wait_for_page_load(page)
            
            # 1. Analyze and Fill Loop (handling multi-page forms)
            max_pages = 5
            for page_idx in range(max_pages):
                logger.info(f"   📄 Analyzing page {page_idx + 1}")
                application.add_log("analyzing_page", f"Analyzing page {page_idx + 1}")
                
                # Check for success ONLY after we've filled something or clicked a button
                # No more early check that catches job description text

                filled_count = await self._analyze_and_fill_current_view(page, job, application)
                
                if filled_count > 0:
                    logger.info(f"   ✨ Filled {filled_count} fields")
                    application.add_log("filled_fields", f"Filled {filled_count} fields")
                else:
                    logger.info("   ℹ️ No fields filled on this page")
                
                # Try to find and click continue/submit
                moved_forward = await self._find_and_click_action_button(page)
                
                if not moved_forward:
                    # If we didn't fill anything and couldn't move forward, maybe we are stuck or done
                    if filled_count == 0:
                        logger.warning("   ⚠️ Stuck: No fields filled and no button found")
                        application.add_log("stuck", "Could not identify fields or action buttons")
                        # Try one last success check
                        if await self._check_success(page):
                            return True
                        break
                    else:
                        logger.info("   ℹ️ Filled fields but didn't find next button - waiting...")
                else:
                    logger.info("   🖱️ Clicked action button")
                
                await self.wait_for_page_load(page)
                await asyncio.sleep(2) # stabilization wait
            
            return await self._check_success(page)
            
        except Exception as e:
            logger.error(f"   ❌ Universal filler error: {e}")
            application.fail(f"Universal filler error: {str(e)}")
            return False

    async def _analyze_and_fill_current_view(self, page: Page, job: Job, application: Application) -> int:
        if not self.llm_client:
            return 0

        # Extract simplified DOM for inputs
        form_elements = await self._extract_form_elements(page)
        if not form_elements:
            return 0
            
        # Filter out already processed fields to save tokens/time
        new_elements = [el for el in form_elements if el['id'] not in self.processed_fields]
        if not new_elements:
            return 0

        # Ask LLM to map values
        mappings = await self._get_llm_mappings(new_elements, job)
        
        filled_count = 0
        for element_id, value in mappings.items():
            if value is None or value == "None":
                continue
                
            success = await self._apply_value(page, element_id, value)
            if success:
                self.processed_fields.add(element_id)
                filled_count += 1
                
        return filled_count

    async def _extract_form_elements(self, page: Page) -> List[Dict[str, Any]]:
        """Extracts interactive elements from all frames and shadow roots."""
        all_elements = []
        
        # Recursive JS function to find elements in shadow roots
        getter_script = """
        (root) => {
            const elements = [];
            
            const findInputs = (node) => {
                // Check for inputs in this node (document or shadowRoot)
                const inputs = node.querySelectorAll('input, select, textarea');
                inputs.forEach((el, index) => {
                    if (el.type === 'hidden' || el.style.display === 'none' || el.disabled) return;
                    
                    // Try to find label
                    let labelText = '';
                    if (el.id) {
                        const label = (node.querySelector ? node : document).querySelector(`label[for="${el.id}"]`);
                        if (label) labelText = label.innerText;
                    }
                    if (!labelText && el.closest('label')) {
                        labelText = el.closest('label').innerText;
                    }
                    if (!labelText) {
                        labelText = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || '';
                    }
                    
                    // Gen synthetic ID if needed
                    const uniqueId = el.id || `auto_gen_${Math.random().toString(36).substr(2, 5)}`;
                    el.setAttribute('data-auto-id', uniqueId);
                    
                    elements.push({
                        id: uniqueId,
                        tag: el.tagName.toLowerCase(),
                        type: el.type || 'text',
                        label: labelText.trim().substring(0, 100),
                        options: el.tagName.toLowerCase() === 'select' ? Array.from(el.options).map(o => o.text) : []
                    });
                });

                // Find shadow roots and recurse
                const all = node.querySelectorAll('*');
                all.forEach(el => {
                    if (el.shadowRoot) {
                        elements.push(...findInputs(el.shadowRoot));
                    }
                });
                return elements;
            };

            return findInputs(root);
        }
        """
        
        # Scan all frames
        for frame in page.frames:
            try:
                # Some frames are cross-origin and might error on evaluate
                frame_elements = await frame.evaluate(getter_script, "document")
                # Mark which frame they belong to if needed, or rely on data-auto-id + page.locator(..., frame=...)
                # For simplicity, we assume we can locate them via global locator if we use the attribute
                all_elements.extend(frame_elements)
            except:
                continue
                
        return all_elements

    async def _get_llm_mappings(self, elements: List[Dict], job: Job) -> Dict[str, Any]:
        if not self.llm_client:
            return {}

        prompt = f"""
        You are an auto-filling bot. Map the user's profile information to these form fields.
        
        Job: {job.title} at {job.company}
        
        User Profile:
        {self.applicant.get_full_context()}
        
        Form Fields:
        {json.dumps(elements, indent=2)}
        
        Task:
        Return a JSON object where keys are the 'id' of the elements and values are the string values to fill.
        - For checkboxes/radios, return "true" (click it) or "false" (don't click).
        - For dropdowns, return the EXACT option text to select.
        - For text inputs, return the text to type.
        - If you don't know or shouldn't fill it, omit the key.
        - If asking for resume/CV, ignore it (handled separately).
        """
        
        response = await self.llm_client.generate(prompt, max_tokens=1000, temperature=0.0)
        if not response:
            return {}
            
        try:
            # Cleanup JSON block
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except:
            return {}

    async def _apply_value(self, page: Page, element_id: str, value: Any) -> bool:
        try:
            # Locate by the distinct data attribute we set
            locator = page.locator(f'[data-auto-id="{element_id}"]')
            if await locator.count() == 0:
                # Fallback to ID
                locator = page.locator(f'#{element_id}')
                
            if await locator.count() == 0:
                return False

            tag_name = await locator.evaluate("el => el.tagName.toLowerCase()")
            input_type = await locator.get_attribute("type")

            if tag_name == "select":
                await locator.select_option(label=str(value))
            elif input_type == "checkbox" or input_type == "radio":
                if str(value).lower() == "true":
                    await locator.check()
            elif input_type == "file":
                # Handle file upload if value indicates it's a resume field, 
                # but usually we handle resumes specifically. 
                pass 
            else:
                await locator.fill(str(value))
                
            return True
        except Exception:
            return False

    async def _find_and_click_action_button(self, page: Page) -> bool:
        # Heuristic to find Submit / Next / Continue buttons across all frames
        candidate = None
        candidate_score = 0
        
        button_script = """
        () => {
            const results = [];
            const findBtn = (node) => {
                const buttons = node.querySelectorAll("button, input[type='submit'], a.btn, [role='button']");
                buttons.forEach(btn => {
                    const style = window.getComputedStyle(btn);
                    if (style.display === 'none' || style.visibility === 'hidden') return;
                    
                    const text = (btn.textContent || btn.value || '').toLowerCase();
                    const uniqueId = btn.id || `btn_gen_${Math.random().toString(36).substr(2, 5)}`;
                    btn.setAttribute('data-btn-id', uniqueId);
                    
                    results.push({
                        id: uniqueId,
                        text: text
                    });
                });
                
                const all = node.querySelectorAll('*');
                all.forEach(el => { if (el.shadowRoot) findBtn(el.shadowRoot); });
            };
            findBtn(document);
            return results;
        }
        """
        
        for frame in page.frames:
            try:
                btns = await frame.evaluate(button_script)
                for b_info in btns:
                    text = b_info['text']
                    score = 0
                    if "submit" in text or "apply" in text: score = 10
                    elif "continue" in text or "next" in text: score = 8
                    elif "review" in text: score = 5
                    
                    if "back" in text or "cancel" in text or "login" in text: score = -10
                    
                    if score > candidate_score:
                        candidate = frame.locator(f"[data-btn-id='{b_info['id']}']")
                        candidate_score = score
            except: continue
        
        if candidate and candidate_score > 0:
            await candidate.first.click()
            return True
            
        return False

    async def _check_success(self, page: Page) -> bool:
        url = page.url.lower()
        if any(part in url for part in self.SUCCESS_URL_PARTS):
            return True
            
        content = (await page.content()).lower()
        if any(text in content for text in self.SUCCESS_TEXTS):
            return True
            
        return False
