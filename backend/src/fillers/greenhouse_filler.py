from playwright.async_api import Page
import asyncio
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller


class GreenhouseFiller(BaseFiller):
    PLATFORM_NAME = "Greenhouse"
    
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
        url = page.url.lower()
        print(f"DEBUG: GreenHouseFiller checking URL: {url}")
        if "greenhouse.io" in url:
            return True
        
        gh_elements = await page.locator("[data-source='greenhouse']").count()
        return gh_elements > 0
    
    async def fill(self, page: Page, job: Job, application: Application) -> bool:

        application.start()
        
        try:
            await self.wait_for_page_load(page)
            
            # Locate the correct frame (main page or iframe)
            frame = await self._get_frame(page)
            if not frame:
                raise Exception("Could not find application form (checked frames)")
            
            # Basic Info
            if not await self._fill_basic_info(frame):
                raise Exception("Failed to fill basic info (selectors not found)")
            
            application.add_log("filled_basic", "Filled name, email, phone")
            await asyncio.sleep(1) # Visual delay for user
            
            # Resume
            if not await self._upload_resume(frame):
                 application.add_log("resume_error", "Failed to upload resume")
            else:
                 application.resume_uploaded = True
                 application.add_log("uploaded_resume", "Resume uploaded")
            
            await self._fill_online_presence(frame)
            await asyncio.sleep(1) 
            
            await self._handle_custom_questions(frame, job, application)
            await asyncio.sleep(1)
            
            if application.questions_for_review:
                print(f"DEBUG: Review required for {len(application.questions_for_review)} items (PROCEEDING ANYWAY):")
                for q, reason in application.questions_for_review.items():
                    print(f"  - {q}: {reason}")
                
                # For demo purposes, we PROCEED even if review is needed
                application.add_log("warning", "Proceeding with submission despite review items")
            
            # SUBMIT
            print("   🚀 Submitting application...")
            success = await self.submit_application(frame)
            if success:
                 application.add_log("submitted", "Application submitted successfully")
                 job.mark_applied()
                 return True
            else:
                 raise Exception("Submission failed (Timeout or Error)")
            
        except Exception as e:
            print(f"DEBUG: Fill Exception: {e}")
            import traceback
            traceback.print_exc()
            application.fail(str(e))
            return False
            
    async def submit_application(self, page) -> bool:

        submit_btn = page.locator("button[type='submit'], input[type='submit'], #submit_app")
        if await submit_btn.count() > 0:
            # Scroll to it
            await submit_btn.first.scroll_into_view_if_needed()
            await asyncio.sleep(2) # Give user time to see
            
            try:
                # Click and waiting for navigation usually indicates success
                # But sometimes it's AJAX.
                # We'll just click and wait for url change or body text
                
                # DEBUG: Screenshot before submit
                try:
                    await page.screenshot(path="debug_before_submit.png")
                    print("   📸 Created debug_before_submit.png")
                except Exception:
                    pass
                
                await submit_btn.first.click()
                
                # Wait for navigation or success message
                # Greenhouse usually redirects to /confirmation or shows "Thank you"
                try:
                    await page.wait_for_url(lambda u: "confirmation" in u.lower() or "success" in u.lower(), timeout=15000)
                    return True
                except Exception:
                    # Check for success text
                    content = (await page.content()).lower()
                    success_patterns = [
                        "thank you for applying",
                        "application was received",
                        "application has been received",
                        "successfully submitted"
                    ]
                    if any(p in content for p in success_patterns):
                        await page.screenshot(path="debug_submit_success.png")
                        return True
                    # Check for "Verify your email" step (Greenhouse specific)
                    # "We've sent a 6-digit code to..." or "A verification code was sent to..."
                    content = await page.content()
                    is_verification = ("sent a" in content.lower() and "code" in content.lower()) or \
                                      ("verification code" in content.lower())
                    
                    if is_verification:
                         # Check for single input vs split inputs
                         split_inputs = await page.locator("input[id^='security-input-']").count()
                         single_input = await page.locator("input[id*='code'], input[name*='code']").count()
                         
                         if split_inputs > 0 or single_input > 0:
                             print("   📧 Email Verification Required! Initiating MailHandler...")
                             
                             try:
                                 from src.utils.mail_handler import MailHandler
                                 mail = MailHandler()
                                 
                                 print("   ⏳ Waiting for verification code to arrive (polling up to 90s)...")

                                 
                                 code = None
                                 # Poll every 15 seconds for up to 6 attempts (90 seconds total)
                                 for attempt in range(6):
                                     await asyncio.sleep(15) 
                                     print(f"      🔄 Checking inbox (Attempt {attempt+1}/6)...")
                                     
                                     try:
                                         code = mail.get_verification_code(subject_filter="Greenhouse")
                                         if code:
                                             print(f"      ✅ Code received on attempt {attempt+1}: {code}")
                                             break
                                     except Exception as e:
                                         print(f"      ⚠️ Polling error: {e}")
                                     
                                 if code:
                                     # Remove spaces/dashes just in case
                                     clean_code = code.replace("-", "").replace(" ", "").strip()
                                     
                                     if split_inputs > 0:
                                         print(f"   🔢 Filling split inputs with code: {clean_code}")
                                         for i, char in enumerate(clean_code):
                                             if i >= split_inputs:
                                                 break
                                             await page.locator(f"#security-input-{i}").fill(char)
                                             await asyncio.sleep(0.1)
                                     else:
                                         print(f"   🔢 Filling single input with code: {clean_code}")
                                         input_field = page.locator("input[id*='code'], input[name*='code']").first
                                         await input_field.fill(clean_code)
                                     
                                     # Submit code with robust button finding
                                     await asyncio.sleep(1)
                                     
                                     verify_selectors = [
                                         "button:has-text('Verify')", 
                                         "input[type='submit']",
                                         "button[id*='verify']",
                                         "button[class*='verify']",
                                         "input[value='Verify']"
                                     ]
                                     
                                     clicked = False
                                     for v_sel in verify_selectors:
                                         btn = page.locator(v_sel).first
                                         if await btn.count() > 0 and await btn.is_visible():
                                             print(f"   🖱️ Clicking Verify button: {v_sel}")
                                             await btn.click()
                                             clicked = True
                                             break
                                             
                                     if not clicked:
                                          print("   ⚠️ specific verify button not found, trying Enter key...")
                                          await page.keyboard.press("Enter")
                                          
                                     await page.wait_for_timeout(5000)
                                     return True
                                 else:
                                     print("   ❌ No code found in email (or credentials missing).")
                                     return False
                             except Exception as e:
                                 print(f"   ❌ MailHandler Failed: {e}")
                                 return False

                    # Check for errors
                    if "error" in content.lower() or "required" in content.lower():  
                         print("   ⚠️ Submission errors detected on page")
                         try:
                             await page.screenshot(path="debug_submit_error.png")
                         except Exception as e:
                             print(f"   ❌ Screenshot error: {e}")
                         
                         # SCAVENGE FOR ERRORS
                         error_selectors = [
                            ".error-message", 
                            ".field-error-msg", 
                            "div.field_error", 
                            "label.error",
                            "#error_message",
                            "div[class*='error']",
                            "div[role='alert']"
                         ]
                        
                         found_errors = []
                         for sel in error_selectors:
                            elements = page.locator(sel)
                            try:
                                count = await elements.count()
                                for i in range(count):
                                    el = elements.nth(i)
                                    text = await el.text_content()
                                    if text and text.strip():
                                         # Try to find associated label
                                         label_text = await el.evaluate("el => { const field = el.closest('.field') || el.closest('.custom-question'); return field ? field.querySelector('label')?.innerText : null; }")
                                         if label_text:
                                             found_errors.append(f"[{label_text.strip()}]: {text.strip()}")
                                         else:
                                             found_errors.append(f"[{sel}]: {text.strip()}")
                            except Exception:
                                pass
                        
                         if found_errors:
                            print(f"   ❌ CAPTURED VALIDATION ERRORS: {found_errors}")
                            try:
                                content = await page.content()
                                with open("greenhouse_validation_dump.html", "w") as f:
                                    f.write(content)
                                print("   📄 Saved greenhouse_validation_dump.html")
                            except Exception:
                                pass
                         else:
                            print("   ❌ No specific error text found (Might be Top-Level Alert or Captcha).")

                         return False

                # If we are here, assume success if no errors visible? 
                # Or maybe double check URL?
                # Let's assume True if no error.
                await page.screenshot(path="debug_submit_unknown.png")
                return True
            except Exception as e:
                print(f"   ❌ Click error: {e}")
                return False
        return False
        
    async def _get_frame(self, page: Page):
        # Check main page first
        if await page.locator(self.SELECTORS["first_name"]).count() > 0:
            return page
            
        # Check frames
        for frame in page.frames:
            try:
                if await frame.locator(self.SELECTORS["first_name"]).count() > 0:
                    return frame
            except Exception:
                continue
        return None
    
    async def _fill_basic_info(self, page) -> bool:

        # Returns True if at least one field was filled, or if primary fields found
        f = await self.fill_text_field(page, self.SELECTORS["first_name"], self.applicant.first_name)
        await asyncio.sleep(0.5)
        last_name_success = await self.fill_text_field(page, self.SELECTORS["last_name"], self.applicant.last_name)
        await asyncio.sleep(0.5)
        e = await self.fill_text_field(page, self.SELECTORS["email"], self.applicant.email)
        await asyncio.sleep(0.5)
        await self.fill_text_field(page, self.SELECTORS["phone"], self.applicant.phone)
        return f and last_name_success and e # Phone is sometimes optional
    
    async def _upload_resume(self, page) -> bool:
        from pathlib import Path
        
        resume_path_str = self.applicant.resume.file_path
        resume_path = None
        
        # Resolve resume path - check multiple locations
        candidates = [
            Path(resume_path_str),  # As-is (relative to CWD)
            Path.cwd().parent / resume_path_str,  # Relative to parent (project root)
            Path(__file__).parent.parent.parent.parent / resume_path_str,  # Relative to src/
        ]
        
        for candidate in candidates:
            if candidate.exists():
                resume_path = str(candidate.resolve())
                print(f"   📁 Found resume at: {resume_path}")
                break
        
        if not resume_path:
            print(f"   ❌ Resume not found! Tried: {[str(c) for c in candidates]}")
            return False
        
        # Selectors to find file input
        selectors = [
            self.SELECTORS["resume"],
            "input[data-qa='resume-input']",
            "input[type='file']"
        ]
        
        for selector in selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    await el.set_input_files(resume_path)
                    print(f"   ✅ Resume uploaded via selector: {selector}")
                    return True
            except Exception as e:
                print(f"   ⚠️ Failed to upload with {selector}: {e}")
                continue
                
        print("   ❌ No file input found for resume upload")
        return False
    
    async def _fill_online_presence(self, page) -> None:
        if self.applicant.linkedin:
            await self.fill_text_field(page, self.SELECTORS["linkedin"], self.applicant.linkedin)
        
        if self.applicant.github:
            await self.fill_text_field(page, self.SELECTORS["github"], self.applicant.github)
        
        if self.applicant.portfolio or self.applicant.website:
            website = self.applicant.portfolio or self.applicant.website
            await self.fill_text_field(page, self.SELECTORS["website"], website)

    async def _handle_custom_questions(self, page, job: Job, application: Application) -> None:
        # Broader selector to catch all fields with labels
        questions = page.locator("div.field, div.custom-question, .application-question, div:has(> label), div:has(> .label)")
        count = await questions.count()
        print(f"DEBUG: Found {count} potential question blocks.")
        
        for i in range(count):
            question_el = questions.nth(i)
            
            # Ensure it's not hidden
            if not await question_el.is_visible():
                continue
            
            label = question_el.locator("label, .label").first
            if await label.count() > 0:
                question_text = await label.text_content()
            else:
                continue
            
            if not question_text:
                continue
            
            question_text = question_text.strip()
            print(f"DEBUG: Processing question: '{question_text}'")
            text_lower = question_text.lower()
            
            if any(skip in text_lower for skip in ["first name", "last name", "email", "phone", "resume", "attach", "enter manually", "apply with", "cloudflares candidate privacy policy", "legal name", "would you like to include"]):
                print(f"DEBUG: Skipping '{question_text}' (matched skip list)")
                continue
            
            # Check for Location/City/School/Degree Autocomplete (Prioritize this over Dropdown)
            if any(k in text_lower for k in ["city", "location", "school", "degree", "discipline", "university", "year", "month"]):
                input_field = question_el.locator("input, textarea, select, [role='combobox']").first
                if await input_field.count() > 0:
                    await self._handle_autocomplete(input_field, question_text)
                    continue

            # Heuristic for Dropdowns/Selects
            # Includes hidden selects, select2 containers, and ARIA comboboxes
            is_dropdown = await question_el.locator("select, .select2-container, .select2-selection, [role='combobox'], ul[role='listbox']").count() > 0 or \
                          "country" in text_lower or \
                          "gender" in text_lower or \
                          "hear about" in text_lower or \
                          "race" in text_lower or \
                          "veteran" in text_lower or \
                          "disability" in text_lower or \
                          "month" in text_lower or \
                          "year" in text_lower

            is_file = await question_el.locator("input[type='file']").count() > 0

            if is_dropdown:
                 # Try to find the actual element to interact with
                 # If select is present, use it. If select2, usage might differ.
                 # _handle_dropdown usually expects a Select or something to click.
                 # We'll pass the container if needed? No, _handle_dropdown takes an element.
                 # Let's try to pass the select or the container.
                 dropdown_el = question_el.locator("select, [role='combobox']").first
                 if await dropdown_el.count() == 0:
                      # If only .select2-container exists, maybe pass that?
                      dropdown_el = question_el.locator(".select2-container").first
                 
                 if await dropdown_el.count() > 0:
                     await self._handle_dropdown(dropdown_el, question_text)
                     continue

            if is_file:
                 continue
            
            # General Input fields (Text, Checkbox, Radio, Combobox)
            input_field = question_el.locator("input, textarea, select, [role='combobox']").first
            if await input_field.count() == 0:
                 # Check if we already handled it?
                 if is_dropdown:
                     continue # Handled above but maybe logic failed
                 
                 print(f"      -> Review item added: {question_text} (Unknown field type)")
                 application.questions_for_review[question_text] = "Unknown field type"
                 continue
            
            await self._handle_input(input_field, question_text, job)
            continue # We handled it via _handle_input, skip existing logic below

        # Final sweep for Disability if missed
        try:
            print("DEBUG: Performing final sweep for Disability field...")
            # Check for standard select or React Select input
            disability_el = page.locator("select[id*='disability'], select[name*='disability'], #disability_status, [aria-labelledby*='disability_status-label']").first
            
            if await disability_el.count() > 0 and await disability_el.is_visible():
                 await disability_el.input_value()
                 # React Selects often have empty value but show placeholder
                 # checks value attrib or check if placeholder is visible?
                 # Actually, usually input value is empty until typed, but for dropdowns...
                 # We can just try to fill it regardless?
                 print(f"   -> Found Disability element (ID: {await disability_el.get_attribute('id')}), attempting fill...")
                 await self._handle_dropdown(disability_el, "Disability Status")
        except Exception as e:
            print(f"DEBUG: Disability sweep error: {e}")
            try:
                content = await page.content()
                with open("greenhouse_page_dump.html", "w") as f:
                    f.write(content)
                print("   📄 Saved greenhouse_page_dump.html for inspection")
            except Exception:
                pass
                
    async def _handle_autocomplete(self, field, question: str) -> bool:

        # 1. Determine value
        value = await self.field_mapper.get_value(question)
        if not value:
            return False
        
        print(f"DEBUG: Handling Autocomplete for '{question}' with '{value}'")
        
        try:
            # HYBRID "SHOCK AND AWE" STRATEGY
            # 1. Click to Focus
            await field.click()
            await asyncio.sleep(0.5)
            
            # 2. Type Value
            await field.clear()
            await field.press_sequentially(str(value), delay=100)
            await asyncio.sleep(2.0) # Wait for suggestions
            
            # 3. Try Clicking Suggestion (First attempt)
            suggestion_clicked = False
            for sel in [".ui-menu-item", ".select2-results__option", "li[role='option']", ".autocomplete-suggestion"]:
                 suggestions = field.page.locator(f"{sel}:visible")
                 if await suggestions.count() > 0:
                      print(f"   -> Clicking visible suggestion: {sel}")
                      await suggestions.first.click()
                      suggestion_clicked = True
                      break
            
            await asyncio.sleep(0.5)
            
            # 4. Force Keyboard Confirmation (Redundancy)
            # Even if we clicked, pressing Enter often commits the state
            if not suggestion_clicked:
                 print("   -> No suggestion clicked, using Keyboard Fallback")
                 await field.press("ArrowDown")
                 await asyncio.sleep(0.5)
            
            await field.press("Enter")
            await asyncio.sleep(0.5)
            await field.press("Tab") # Blur
            
            # 5. VERIFICATION & DEBUGGING
            current_val = await field.input_value()
            print(f"   -> Final Field Value: '{current_val}'")
            
            # 5. NUCLEAR OPTION: JS Injection
            # The input logic is failing to sync state. 
            # We will manually set the value and dispatch events at the browser level.
            
            print("   ☢️ Executing Nuclear Option: JS Value Injection...")
            
            success = await field.page.evaluate("""(data) => {
                const input = document.querySelector(data.selector);
                if (!input) return false;
                
                // 1. Set Value directly
                input.value = data.value;
                input.setAttribute('value', data.value);
                
                // 2. Dispatch comprehensive event chain to trigger React/Framework listeners
                const events = ['mousedown', 'focus', 'keydown', 'input', 'change', 'keyup', 'blur'];
                events.forEach(eventType => {
                    const event = new Event(eventType, { bubbles: true, cancelable: true });
                    input.dispatchEvent(event);
                });
                
                // 3. React 16+ State Hack (Try to find internal tracker)
                try {
                    const funcKey = Object.keys(input).find(k => k.startsWith('__reactEventHandlers'));
                    if (funcKey && input[funcKey].onChange) {
                        input[funcKey].onChange({ target: { value: data.value } });
                    }
                } catch(e) { console.log("React hack failed:", e); }
                
                return true;
            }""", {"selector": f"#{await field.get_attribute('id')}", "value": value})
            
            if success:
                 print(f"   ✅ JS Injection executed for {value}")
            else:
                 print("   ⚠️ JS Injection: Could not find element/selector.")

            # 6. CLEANUP: Force close any open dropdowns
            try:
                await field.press("Escape")
                await field.page.mouse.click(0, 0) # Click top-left of body to blur
            except Exception:
                pass
            
            return True
        except Exception as e:
            print(f"   ❌ Autocomplete Error: {e}")
            # Emergency Cleanup
            try:
                await field.press("Escape")
                await field.page.mouse.click(0, 0)
            except Exception:
                pass
            return False
    
    async def _handle_dropdown(self, field, question: str) -> None:

        tag = await field.evaluate("el => el.tagName.toLowerCase()")
        
        # If standard select
        if tag == "select":
            options = await field.locator("option").all_text_contents()
            best_option = await self.field_mapper.get_dropdown_value(options, question)
            if best_option:
                try:
                    await field.select_option(label=best_option)
                except Exception:
                    # Fallback for value matching
                    await field.select_option(value=best_option)
        else:
            # Handle Select2 / Combobox Divs
            # 1. Click to open
            try:
                await field.click()
                await asyncio.sleep(1) # Wait for dropdown to appear
                
                # 2. Find options in the now-visible dropdown container
                # Usually appended to body or near the element
                page = field.page
                option_selectors = [
                    "li[role='option']", 
                    ".select2-results__option", 
                    ".ui-menu-item",
                    "div[role='option']"
                ]
                
                all_options = []
                active_selector = ""
                
                for sel in option_selectors:
                    opts = page.locator(f"{sel}:visible")
                    if await opts.count() > 0:
                        all_options = await opts.all_text_contents()
                        active_selector = sel
                        break
                
                if not all_options:
                    print(f"   ⚠️ Could not find options for custom dropdown '{question}'")
                    # Try closing it to not block view
                    await field.press("Escape")
                    return

                # 3. Select best option
                best_option = await self.field_mapper.get_dropdown_value(all_options, question)
                if best_option:
                    print(f"   -> LLM Chose: {best_option} for '{question}'")
                    # Click the specific option
                    # We need to find the element that matches the text
                    # Using text= exact match if possible, or contains
                    await page.locator(active_selector).filter(has_text=best_option).first.click()
                else:
                    await field.press("Escape")

            except Exception as e:
                print(f"   ❌ Dropdown Error: {e}")
    
    async def _handle_textarea(self, field, question: str, job: Job, application: Application) -> None:
        common_answer = self.applicant.get_answer(
            self._question_to_key(question),
            company=job.company,
            position=job.title
        )
        
        if common_answer:
            await field.fill(common_answer)
            return
        
        if self.llm_client:
            answer = await self.answer_question_with_llm(question, job, max_length=500)
            if answer:
                await field.fill(answer)
                application.add_question(question_text=question, question_type="textarea")
                application.answer_question(len(application.questions) - 1, answer, "llm")
                return
        
        self.add_question_for_review(question_text=question, reason="Long-answer question needs human review")
    
    async def _handle_input(self, field, question: str, job: Job) -> None:
        value = await self.field_mapper.get_value(question)
        if not value:
            return
        
        try:
            # Check if it's actually a SELECT element that fell through
            tag = await field.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                await self._handle_dropdown(field, question)
                return

            # Check for checkbox/radio
            input_type = await field.get_attribute("type")
            if input_type in ["checkbox", "radio"]:
                if str(value).lower() in ["true", "yes", "1", "on"]:
                    await field.check()
                else:
                    await field.uncheck()
                return

            await field.fill(str(value))
        except Exception as e:
            print(f"   ⚠️ Error filling field '{question}': {e}")
            return
        
        bool_answer = self.field_mapper.get_boolean_answer(question)
        if bool_answer is not None:
            await field.fill("Yes" if bool_answer else "No")
            return
        
        self.add_question_for_review(question_text=question, reason="Unknown field type")
    
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
        if "salary" in q:
            return "salary_expectations"
        return ""
