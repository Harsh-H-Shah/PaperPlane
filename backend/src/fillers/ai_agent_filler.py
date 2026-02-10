"""
AI Agent Filler - Custom agent using Gemini Free Tier
Mimics Stagehand's intelligent form filling capabilities.
"""
import json
import asyncio
from typing import Optional, List, Dict, Any
from playwright.async_api import Page

from src.core.applicant import Applicant
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller
from src.llm.gemini import GeminiClient
from src.utils.logger import logger


class AIAgentFiller(BaseFiller):
    """
    Custom AI agent that uses Gemini to intelligently fill forms.
    Works on any form structure without platform-specific code.
    """
    PLATFORM_NAME = "AI Agent"
    
    def __init__(self, applicant: Applicant, llm_client: Optional[GeminiClient] = None):
        super().__init__(applicant, llm_client)
        if not llm_client:
            try:
                self.llm_client = GeminiClient()
            except Exception:
                logger.warning("   ⚠️ AI Agent: LLM not available, will use fallback")
                self.llm_client = None
        
        self.max_steps = 30
        self.action_history: List[Dict] = []
    
    async def can_handle(self, page: Page) -> bool:
        """Can handle any form"""
        return True
    
    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        """
        AI agent that autonomously fills forms by:
        1. Observing page state
        2. Planning actions using Gemini
        3. Executing actions
        4. Verifying success
        """
        application.start()
        application.add_log("ai_agent_start", "Starting AI agent form filling")
        
        try:
            await self.wait_for_page_load(page)
            
            for step in range(self.max_steps):
                logger.info(f"   🤖 AI Agent: Step {step + 1}/{self.max_steps}")
                
                # 1. Observe current state
                page_state = await self._observe_page(page)
                
                # 2. Check if we're done
                if await self._check_success(page):
                    logger.info("   ✅ AI Agent: Application completed successfully!")
                    return True
                
                # 3. Plan next action
                action = await self._plan_action(page_state, job, application, step)
                
                if action.get("type") == "DONE":
                    logger.info("   ✅ AI Agent: Agent determined form is complete")
                    return await self._check_success(page)
                
                # 4. Execute action
                success = await self._execute_action(page, action, job)
                
                if success:
                    self.action_history.append(action)
                    application.add_log("action", f"{action['type']}: {action.get('reason', '')}")
                else:
                    logger.warning(f"   ⚠️ AI Agent: Action failed: {action.get('type')}")
                
                # 5. Wait for page to update
                await asyncio.sleep(1.5)
                await self.wait_for_page_load(page)
            
            # Final success check
            return await self._check_success(page)
        
        except Exception as e:
            logger.error(f"   ❌ AI Agent error: {e}")
            application.fail(f"AI Agent error: {str(e)}")
            return False
    
    async def _observe_page(self, page: Page) -> Dict[str, Any]:
        """Extract page structure and form fields"""
        try:
            # Get all form elements
            form_elements = await page.evaluate("""
                () => {
                    const elements = [];
                    const seen = new Set();
                    
                    document.querySelectorAll('input, textarea, select, button, a[role="button"]').forEach(el => {
                        // Skip hidden elements
                        if (el.offsetParent === null && el.type !== 'hidden') return;
                        
                        const id = el.id || el.name || el.className || '';
                        if (seen.has(id)) return;
                        seen.add(id);
                        
                        // Get label
                        let label = '';
                        if (el.labels && el.labels.length > 0) {
                            label = el.labels[0].textContent.trim();
                        } else {
                            const labelEl = document.querySelector(`label[for="${el.id}"]`);
                            if (labelEl) label = labelEl.textContent.trim();
                        }
                        
                        // Get placeholder/aria-label
                        const placeholder = el.placeholder || el.getAttribute('aria-label') || '';
                        
                        elements.push({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || el.tagName.toLowerCase(),
                            id: el.id || '',
                            name: el.name || '',
                            placeholder: placeholder,
                            label: label,
                            value: el.value || '',
                            visible: el.offsetParent !== null,
                            required: el.required || el.hasAttribute('aria-required'),
                            selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : '')
                        });
                    });
                    
                    return elements;
                }
            """)
            
            # Get page text for context (limited)
            page_text = await page.evaluate("() => document.body.innerText")
            
            # Get current URL
            current_url = page.url
            
            return {
                "elements": form_elements[:30],  # Limit to avoid token limits
                "text": page_text[:1500],
                "url": current_url,
                "title": await page.title()
            }
        
        except Exception as e:
            logger.error(f"   ⚠️ Error observing page: {e}")
            return {"elements": [], "text": "", "url": page.url, "title": ""}
    
    async def _plan_action(self, page_state: Dict, job: Job, application: Application, step: int) -> Dict:
        """Use Gemini to plan the next action"""
        if not self.llm_client:
            return {"type": "WAIT", "target": "", "value": "", "reason": "LLM not available"}
        
        # Build context
        applicant_summary = f"""
        Name: {self.applicant.full_name}
        Email: {self.applicant.email}
        Phone: {self.applicant.phone}
        Location: {self.applicant.location}
        LinkedIn: {self.applicant.linkedin_url or 'N/A'}
        """
        
        job_summary = f"""
        Title: {job.title}
        Company: {job.company}
        Description: {(job.description or '')[:300]}
        """
        
        # Recent actions for context
        recent_actions = self.action_history[-3:] if self.action_history else []
        
        prompt = f"""
You are an AI agent filling out a job application form. Analyze the current page state and determine the next action.

JOB INFORMATION:
{job_summary}

APPLICANT INFORMATION:
{applicant_summary}

CURRENT PAGE STATE:
URL: {page_state.get('url', '')}
Title: {page_state.get('title', '')}

FORM ELEMENTS (first 20):
{json.dumps(page_state.get('elements', [])[:20], indent=2)}

PAGE TEXT (first 500 chars):
{page_state.get('text', '')[:500]}

RECENT ACTIONS:
{json.dumps(recent_actions, indent=2) if recent_actions else "None"}

STEP: {step + 1}/{self.max_steps}

Analyze the form and determine the next action. Return ONLY valid JSON:
{{
    "type": "FILL" | "CLICK" | "SELECT" | "UPLOAD" | "WAIT" | "DONE",
    "target": "element selector (id, name, or description)",
    "value": "value to fill (if type is FILL)",
    "reason": "brief explanation of why this action"
}}

Rules:
- Fill text fields with applicant info (name, email, phone, etc.)
- Answer questions using job description context
- Click continue/submit buttons when form sections are complete
- Upload resume when file input is found (use path: data/Harsh_Shah.pdf)
- Return DONE when application is fully submitted or no more actions needed
- Use element IDs or names as selectors when available
- Be specific about which element to interact with

Return ONLY the JSON, no other text.
"""
        
        try:
            response = await self.llm_client.generate(prompt, max_tokens=300, temperature=0.1)
            
            # Clean response (remove markdown code blocks if present)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()
            
            # Parse JSON
            action = json.loads(response)
            
            # Validate action
            if action.get("type") not in ["FILL", "CLICK", "SELECT", "UPLOAD", "WAIT", "DONE"]:
                action["type"] = "WAIT"
            
            return action
        
        except json.JSONDecodeError as e:
            logger.warning(f"   ⚠️ Failed to parse action JSON: {e}")
            logger.debug(f"   Response was: {response[:200]}")
            return {"type": "WAIT", "target": "", "value": "", "reason": "Failed to parse response"}
        except Exception as e:
            logger.error(f"   ❌ Error planning action: {e}")
            return {"type": "WAIT", "target": "", "value": "", "reason": f"Error: {str(e)}"}
    
    async def _execute_action(self, page: Page, action: Dict, job: Job) -> bool:
        """Execute the planned action"""
        action_type = action.get("type")
        target = action.get("target", "")
        value = action.get("value", "")
        
        try:
            # Find selector
            selector = await self._find_selector(page, target)
            
            if not selector and target:
                # Try direct selector
                selector = target
            
            if not selector:
                logger.warning(f"   ⚠️ Could not find selector for: {target}")
                return False
            
            # Execute based on type
            if action_type == "FILL":
                await page.fill(selector, value)
                logger.info(f"   ✏️ Filled: {selector} = {value[:50]}")
                return True
            
            elif action_type == "CLICK":
                await page.click(selector)
                logger.info(f"   🖱️ Clicked: {selector}")
                return True
            
            elif action_type == "SELECT":
                await page.select_option(selector, value)
                logger.info(f"   📋 Selected: {selector} = {value}")
                return True
            
            elif action_type == "UPLOAD":
                resume_path = getattr(self.applicant, 'resume_path', None) or "data/Harsh_Shah.pdf"
                try:
                    await page.set_input_files(selector, resume_path)
                    logger.info(f"   📄 Uploaded resume: {selector}")
                    return True
                except Exception:
                    logger.warning(f"   ⚠️ Could not upload resume to {selector}")
                    return False
            
            elif action_type == "WAIT":
                await asyncio.sleep(2)
                return True
            
            elif action_type == "DONE":
                return True
        
        except Exception as e:
            logger.debug(f"   ⚠️ Action execution error: {e}")
            return False
        
        return False
    
    async def _find_selector(self, page: Page, description: str) -> Optional[str]:
        """Find element selector from description"""
        if not description:
            return None
        
        # If description is already a selector (starts with #, ., [, etc.)
        if description.startswith(("#", ".", "[", "/")):
            try:
                count = await page.locator(description).count()
                if count > 0:
                    return description
            except Exception:
                pass
        
        # Try to find by ID or name
        try:
            # Check if it's an ID
            if await page.locator(f"#{description}").count() > 0:
                return f"#{description}"
            
            # Check if it's a name
            if await page.locator(f"[name='{description}']").count() > 0:
                return f"[name='{description}']"
        except Exception:
            pass
        
        # Use LLM to generate selector (if available)
        if self.llm_client:
            try:
                prompt = f"""
Given this element description: "{description}"
Generate a CSS selector to find this element on the page.
Return ONLY the selector, nothing else.
Examples: #email, [name="phone"], input[type="text"]
"""
                selector = await self.llm_client.generate(prompt, max_tokens=50, temperature=0.0)
                selector = selector.strip().strip('"').strip("'")
                
                # Verify selector exists
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        return selector
                except Exception:
                    pass
            except Exception:
                pass
        
        return None
    
    async def _check_success(self, page: Page) -> bool:
        """Check if application was submitted successfully"""
        # Check URL for success indicators
        url = page.url.lower()
        success_urls = ["confirmation", "thank-you", "application-submitted", "success"]
        if any(indicator in url for indicator in success_urls):
            return True
        
        # Check page text for success messages
        try:
            page_text = await page.evaluate("() => document.body.innerText").lower()
            success_texts = [
                "application submitted",
                "thank you for applying",
                "your application was received",
                "successfully submitted"
            ]
            if any(text in page_text for text in success_texts):
                return True
        except Exception:
            pass
        
        return False

