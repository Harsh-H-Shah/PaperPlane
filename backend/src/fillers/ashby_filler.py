from typing import Optional, List
from playwright.async_api import Page
import asyncio

from src.core.applicant import Applicant
from src.core.application import Application
from src.core.job import Job
from src.fillers.base_filler import BaseFiller
from src.llm.gemini import GeminiClient

class AshbyFiller(BaseFiller):
    PLATFORM_NAME = "Ashby"
    
    SELECTORS = {
        "apply_button": "a[href*='application'], button:has-text('Apply Now'), a:has-text('Apply Now'), button:has-text('Apply for this Job'), a:has-text('Apply for this Job'), button:has-text('Apply')",
        "name": "input#_systemfield_name, input[name='name'], input[id*='name'], input[name='_systemfield_name']",
        "email": "input#_systemfield_email, input[name='email'], input[id*='email'], input[name='_systemfield_email']",
        "phone": "input[name='phone'], input[id*='phone'], input[id*='mobile']",
        "resume": "input[type='file'][name*='resume'], input[type='file'][accept*='pdf'], input[id*='resume']",
        "cover_letter": "input[type='file'][name*='cover']",
        "linkedin": "input[name*='linkedin'], input[id*='linkedin'], div:has(label:has-text('LinkedIn')) input, input[id*='_systemfield_linkedin']",
        "github": "input[name*='github'], input[id*='github'], div:has(label:has-text('GitHub')) input",
        "website": "input[name*='website'], input[name*='portfolio'], input[id*='website'], div:has(label:has-text('Website')) input, div:has(label:has-text('Portfolio')) input",
        "submit": "button[type='submit']:has-text('Submit Application'), button:has-text('Submit Application'), button[type='submit']:has-text('Apply')",
        # Ashby often wraps questions in these classes
        "question_container": "div._container_11l3u_1, div[class*='_container_']" 
    }

    async def can_handle(self, page: Page) -> bool:
        url = page.url.lower()
        if "ashbyhq.com" in url:
            return True
        
        # Check all frames for Ashby specific indicators
        for frame in page.frames:
            try:
                # Check for Ashby link or specific container
                if await frame.locator("a[href*='ashbyhq.com']").count() > 0 or \
                   await frame.locator("div[class*='ashby'], div[class*='_container_']").count() > 0:
                    return True
            except:
                continue
            
        return False

    async def fill(self, page: Page, job: Job, application: Application) -> bool:
        application.start()
        print(f"DEBUG: AshbyFiller starting for {job.company}")

        try:
            await self.wait_for_page_load(page)
            
            # 1. Ensure we are on the form (click Apply Now if needed)
            # Some Ashby pages are job descriptions, some are already forms
            is_form_visible = await page.locator(self.SELECTORS["name"]).count() > 0
            
            if not is_form_visible:
                apply_btn = page.locator(self.SELECTORS["apply_button"])
                if await apply_btn.count() > 0:
                    print("   🖱️ Clicking 'Apply' button to reveal form...")
                    await apply_btn.first.click()
                    # Wait for form elements to appear
                    try:
                        await page.wait_for_selector(self.SELECTORS["name"], timeout=5000)
                        print("   ✅ Form revealed")
                    except:
                        print("   ⚠️ Form fields didn't appear after click. Trying to wait for URL...")
                        try:
                            await page.wait_for_url(lambda u: "application" in u, timeout=3000)
                        except: pass
                else:
                    print("   ℹ️ No 'Apply' button found, assuming we might be on form or it's slow...")
            
            await asyncio.sleep(1)

            # Ensure we are in the right frame? Ashby is usually not iframed, but just in case
            # We'll stick to main page for now
            
            # 2. Basic Info
            if not await self._fill_basic_info(page, application):
                 # If we can't find basic info, maybe the form didn't load or it's a different structure
                 print("   ⚠️ Could not find basic info fields. Trying to wait longer...")
                 await asyncio.sleep(2)
                 if not await self._fill_basic_info(page, application):
                     raise Exception("Failed to identify application form fields")

            application.add_log("filled_basic", "Filled basic information")
            await asyncio.sleep(1)

            # 3. Resume
            if not await self._upload_resume(page):
                application.add_log("resume_error", "Failed to upload resume")
            else:
                application.resume_uploaded = True
                application.add_log("uploaded_resume", "Resume uploaded")
            
            # 4. Links
            await self._fill_online_presence(page)
            await asyncio.sleep(1)
            
            # 5. Custom Questions
            await self._handle_custom_questions(page, job, application)
            await asyncio.sleep(1)

            # 6. Submit
            if application.questions_for_review:
                 print(f"DEBUG: Application needs review: {application.questions_for_review}")
                 # For now, we proceed in 'shock and awe' mode unless critical
            
            print("   🚀 Submitting application...")
            success = await self.submit_application(page)
            
            if success:
                application.add_log("submitted", "Application submitted successfully")
                job.mark_applied()
                return True
            else:
                 await page.screenshot(path="debug_ashby_submit_fail.png")
                 print("   📸 Saved debug_ashby_submit_fail.png")
                 raise Exception("Submission failed or verification timed out")

        except Exception as e:
            try:
                await page.screenshot(path="debug_ashby_error.png")
            except: pass
            print(f"DEBUG: Ashby Fill Error: {e}")
            import traceback
            traceback.print_exc()
            application.fail(str(e))
            return False

    async def _fill_basic_info(self, page: Page, application: Application) -> bool:
        print("   🔍 Searching for basic info fields (Name, Email, Phone)...")
        
        # Strategy A: Ashby System Fields (High Priority)
        system_name = page.locator("input#_systemfield_name").first
        if await system_name.count() > 0:
            await system_name.fill(self.applicant.full_name)
            name_filled = True
            print(f"      ✅ Filled Name via System ID")

        # Strategy B: Full Name Field (General)
        if not name_filled:
            name_sel = "input[name='name'], input[id*='name'], input[aria-label*='Name'], input[placeholder*='Name']"
            name_input = page.locator(name_sel).first
            
            if await name_input.count() > 0 and await name_input.is_visible():
                await name_input.fill(self.applicant.full_name)
                name_filled = True
                print(f"      ✅ Filled Full Name: {self.applicant.full_name}")
        
        # Strategy C: Split Name (First + Last)
        if not name_filled:
            first_sel = "input[name*='first'], input[id*='first'], input[placeholder*='First']"
            last_sel = "input[name*='last'], input[id*='last'], input[placeholder*='Last']"
            
            first_input = page.locator(first_sel).first
            last_input = page.locator(last_sel).first
            
            if await first_input.count() > 0 and await last_input.count() > 0:
                await first_input.fill(self.applicant.first_name)
                await last_input.fill(self.applicant.last_name)
                name_filled = True
                print(f"      ✅ Filled Split Names: {self.applicant.first_name} {self.applicant.last_name}")

        # Strategy D: Label-Based Search (Nuclear)
        if not name_filled:
            # Look for labels and find adjacent inputs
            labels = ["Name", "Full Name", "First Name"]
            for label_text in labels:
                label_el = page.locator(f"label:has-text('{label_text}')").first
                if await label_el.count() > 0:
                    # Find following input
                    input_el = page.locator(f"label:has-text('{label_text}') + div input, label:has-text('{label_text}') + input").first
                    if await input_el.count() > 0:
                        val = self.applicant.full_name if "First" not in label_text else self.applicant.first_name
                        await input_el.fill(val)
                        name_filled = True
                        print(f"      ✅ Filled Name via Label '{label_text}'")
                        break

        # 2. EMAIL DETECTION
        email_filled = False
        
        # Strategy A: Ashby System Field
        system_email = page.locator("input#_systemfield_email").first
        if await system_email.count() > 0:
            await system_email.fill(self.applicant.email)
            email_filled = True
            print(f"      ✅ Filled Email via System ID")
            
        if not email_filled:
            email_sel = self.SELECTORS["email"] + ", input[type='email'], input[placeholder*='email']"
            email_input = page.locator(email_sel).first
            
            if await email_input.count() > 0:
                await email_input.fill(self.applicant.email)
                email_filled = True
            else:
                # Label search for email
                email_label = page.locator("label:has-text('Email')").first
                if await email_label.count() > 0:
                    input_el = page.locator("label:has-text('Email') + div input, label:has-text('Email') + input").first
                    if await input_el.count() > 0:
                        await input_el.fill(self.applicant.email)
                        email_filled = True

        # 3. PHONE DETECTION
        phone_sel = self.SELECTORS["phone"] + ", input[type='tel'], input[placeholder*='phone']"
        phone_input = page.locator(phone_sel).first
        if await phone_input.count() > 0:
            await phone_input.fill(self.applicant.phone)
        else:
            # Label search for phone
            phone_label = page.locator("label:has-text('Phone'), label:has-text('Mobile')").first
            if await phone_label.count() > 0:
                input_el = page.locator("label:has-text('Phone') + div input, label:has-text('Mobile') + div input").first
                if await input_el.count() > 0:
                    await input_el.fill(self.applicant.phone)

        # Basic verification: at least Name and Email must be found
        return name_filled and email_filled

    async def _upload_resume(self, page: Page) -> bool:
        if not self.applicant.resume or not self.applicant.resume.file_path:
            return False
            
        resume_path = self.applicant.resume.file_path
        
        # Try finding standard file input
        file_input = page.locator(self.SELECTORS["resume"]).first
        if await file_input.count() > 0:
            try:
                await file_input.set_input_files(resume_path)
                return True
            except Exception as e:
                print(f"   ❌ Resume upload failed: {e}")
                return False
        
        # Sometimes Ashby has a hidden input we need to unhide or just target directly
        all_file_inputs = page.locator("input[type='file']")
        count = await all_file_inputs.count()
        for i in range(count):
            try:
                await all_file_inputs.nth(i).set_input_files(resume_path)
                return True
            except: continue
            
        return False

    async def _fill_online_presence(self, page: Page) -> None:
        if self.applicant.linkedin:
            await self.fill_text_field(page, self.SELECTORS["linkedin"], self.applicant.linkedin)
        
        if self.applicant.github:
            await self.fill_text_field(page, self.SELECTORS["github"], self.applicant.github)
            
        if self.applicant.portfolio:
             await self.fill_text_field(page, self.SELECTORS["website"], self.applicant.portfolio)

    async def _handle_custom_questions(self, page: Page, job: Job, application: Application) -> None:
        # Ashby structure:
        # div._container_...
        #   label._label_...
        #   div._inputContainer_... > input / select / textarea
        
        # Broad selector for question blocks
        # We look for divs that contain a label and an input
        
        # NOTE: Class names in Ashby are often hashed css modules (e.g. _container_11l3u_1)
        # We should rely on structural logic: div that has label
        
        # Ashby structure:
        # div/fieldset containing label and input
        
        # NOTE: Using 'fieldset' is semantic for Ashby, missed previously.
        question_blocks = page.locator("div:has(> label), fieldset:has(> label), div[class*='container']:has(label)")
        count = await question_blocks.count()
        
        print(f"DEBUG: Found {count} potential question blocks")

        handled_inputs = set()
        for i in range(count):
            block = question_blocks.nth(i)
            
            # 0. Skip if this block is contained within another question block we already handled
            # (Ashby often nests labels/inputs in ways that trigger broad selectors)
            if not await block.is_visible():
                continue
                
            label_el = block.locator("label").first
            if await label_el.count() == 0:
                continue
                
            question_text = await label_el.text_content()
            if not question_text: continue
            question_text = question_text.strip()
            
            if self._should_skip_question(question_text):
                continue
                
            print(f"DEBUG: Processing question: '{question_text}'")
            await asyncio.sleep(2) # Throttle to avoid LLM rate limits
            
            # Find input element within the block
            input_el = block.locator("input, textarea, select, [role='combobox']").first
            
            # Special Handling for "Button Groups" (Yes/No buttons often used by Ashby/Ramp)
            # If no input found, OR if input is hidden, look for buttons
            has_buttons = await block.locator("button").count() > 0
            if (await input_el.count() == 0 or not await input_el.is_visible()) and has_buttons:
                 await self._handle_button_group(block, question_text)
                 continue
            
            if await input_el.count() == 0:
                 continue
            
            # Determine type
            tag_name = await input_el.evaluate("el => el.tagName.toLowerCase()")
            input_type = await input_el.get_attribute("type")
            
            # Skip if we already handled this specific input (primary for choice groups)
            input_id = await input_el.get_attribute("id") or await input_el.get_attribute("name")
            if input_id in handled_inputs:
                print(f"   ⏩ Skipping already handled input: {input_id}")
                continue
            if input_id: handled_inputs.add(input_id)

            # 1. Dropdowns (Select or custom)
            if tag_name == "select" or (await block.locator("div[class*='select']").count() > 0):
                await self._handle_dropdown(block, question_text)
                continue
                
            # 1. Checkboxes / Radios (High Priority - often styled as other things)
            if input_type in ["checkbox", "radio"]:
                # If Choice Group, mark all inner inputs as handled
                inner_inputs = await block.locator(f"input[type='{input_type}']").all()
                for inp in inner_inputs:
                    iid = await inp.get_attribute("id") or await inp.get_attribute("name")
                    if iid: handled_inputs.add(iid)
                # Check if this is a GROUP (multiple options) or Single
                all_inputs = block.locator(f"input[type='{input_type}']")
                if await all_inputs.count() > 1:
                     await self._handle_choice_group(block, question_text, input_type)
                else:
                     await self._handle_checkbox(input_el, question_text)
                continue

            # 1.5 Autocomplete (School/Location)
            # Check for School/University/Degree specific inputs that need typing
            if any(k in question_text.lower() for k in ["school", "university", "college", "degree", "location", "city", "institution", "education"]):
                 await self._handle_autocomplete(input_el, question_text)
                 continue


                
            # 2. Textarea
            if tag_name == "textarea":
                await self._handle_textarea(input_el, question_text, job, application)
                continue
                
            # 3. Text Input (Catch-all for remaining inputs)
            # If it's an input and NOT a checkbox/radio/file/hidden (handled above/below)
            if tag_name == "input" and input_type not in ["checkbox", "radio", "file", "hidden", "submit", "button", "image"]:
                await self._handle_input(input_el, question_text, job)
                continue


                
            # 5. Hidden Inputs (often styled radios/checkboxes)
            if await input_el.count() > 0 and not await input_el.is_visible():
                 if input_type in ["checkbox", "radio"]:
                     # Same logic for hidden inputs
                     all_inputs = block.locator(f"input[type='{input_type}']")
                     if await all_inputs.count() > 1:
                          await self._handle_choice_group(block, question_text, input_type)
                     else:
                          await self._handle_checkbox(input_el, question_text)
                     continue

    async def _handle_input(self, element, question: str, job: Job) -> None:
        q_lower = question.lower()
        val = None
        
        # Explicitly handle social links if they fell through to here
        if "linkedin" in q_lower:
            val = self.applicant.linkedin
        elif "github" in q_lower:
            val = self.applicant.github
        elif "website" in q_lower or "portfolio" in q_lower:
            val = self.applicant.portfolio
            
        # Fallback to general mapper
        if not val:
            val = self.field_mapper.get_value(question)
            
        if val:
            await element.fill(str(val))

    def _should_skip_question(self, text: str) -> bool:
        t = text.lower()
        # Skip basic fields we already filled
        # removed linkedin/github/website/portfolio from skip list to allow retry as custom question
        if any(x in t for x in ["name", "email", "phone", "resume", "cv"]):
             return True
        return False

    async def _handle_dropdown(self, block, question_text: str) -> None:
        # Ashby uses custom react-select or similar
        # If it's a native select:
        select = block.locator("select").first
        if await select.count() > 0 and await select.is_visible():
            options = await select.locator("option").all_text_contents()
            val = self.field_mapper.get_dropdown_value(options, question_text)
            if val:
                await select.select_option(label=val)
            return

        # If custom dropdown
        # Usually checking for a role=kCombobox or just clicking the container
        # Ashby often requires clicking the input field which acts as a search/dropdown trigger
        trigger = block.locator("input[role='combobox'], div[class*='control']").first
        if await trigger.count() > 0:
             await trigger.click()
             await asyncio.sleep(0.5)
             
             # Locate options (usually in a portal at root)
             # Ashby options often have class containing 'option'
             options_locator = self.applicant.page_locator("div[id*='react-select'], div[class*='option']") 
             # Wait, we need page reference. 
             # We can use block.page
             page = block.page
             
             # Try to find the menu
             menu = page.locator("div[class*='menu']").last # most recently opened
             if await menu.count() > 0:
                 opts = await menu.locator("div[id*='react-select']").all_text_contents()
                 if opts:
                     val = self.field_mapper.get_dropdown_value(opts, question_text)
                     if val:
                         await menu.locator(f"div:has-text('{val}')").first.click()
                         return
            
             # Fallback: type and enter
             val = self.field_mapper.get_value(question_text)
             if val:
                 await trigger.fill(str(val))
                 await asyncio.sleep(0.5)
                 await trigger.press("Enter")

    async def _handle_checkbox(self, element, question_text: str) -> None:
         val = self.field_mapper.get_boolean_answer(question_text)
         target_state = True if val else False
         
         try:
             # Standard visibility check
             if await element.is_visible():
                 if target_state:
                     await element.check(force=True)
                 else:
                     await element.uncheck(force=True)
                 return
             
             # Hidden input handling - NUCLEAR DOUBLE TAP
             print(f"      ⚠️ Hidden radio/checkbox '{question_text}', attempting Double-Tap Label Click...")
             
             # 1. Click parent label (forcefully)
             await element.evaluate("el => el.closest('label')?.click() || el.parentElement?.click()")
             await asyncio.sleep(0.1)
             
             # 2. Fire explicit MouseEvent sequence (mousedown -> mouseup -> click)
             # This often wakes up stubborn React listeners
             await element.evaluate("""el => {
                 const label = el.closest('label') || el.parentElement;
                 if (label) {
                     label.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                     label.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                     label.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                 }
             }""")
             
         except Exception as e:
             print(f"      ❌ Standard check failed: {e}")
             # Fallback: Direct JS set
             try:
                 print(f"      ☢️ Attempting JS Injection for checkbox '{question_text}'")
                 await element.evaluate(f"el => el.checked = {'true' if target_state else 'false'}")
                 await element.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
             except Exception as e2:
                 print(f"      ❌ JS Injection failed: {e2}")

    async def _handle_choice_group(self, block, question: str, input_type: str) -> None:
        print(f"DEBUG: Handling Choice Group ('{input_type}') for '{question}'")
        
        # 1. Extract all options with their associated elements
        options = []
        inputs = block.locator(f"input[type='{input_type}']")
        count = await inputs.count()
        
        element_map = {}  # text -> clickable element (label/parent)
        input_map = {}    # text -> input element (for force-setting)
        
        for i in range(count):
            inp = inputs.nth(i)
            id_val = await inp.get_attribute("id")
            value_attr = await inp.get_attribute("value")
            
            label_text = ""
            click_target = inp  # fallback
            
            # Case A: Label with 'for' attribute (most reliable)
            if id_val:
                for_label = block.page.locator(f"label[for='{id_val}']")
                if await for_label.count() > 0:
                    label_text = await for_label.first.text_content()
                    click_target = for_label.first
            
            # Case B: Wrapped in Label
            if not label_text:
                parent = inp.locator("xpath=..")
                parent_tag = await parent.evaluate("el => el.tagName")
                if parent_tag == "LABEL":
                    label_text = await parent.text_content()
                    click_target = parent
            
            # Case C: Sibling text or nearby text
            if not label_text:
                # Look for text in parent container
                container = inp.locator("xpath=..")
                label_text = await container.text_content()
            
            # Case D: Use value attribute as last resort
            if not label_text and value_attr:
                label_text = value_attr
            
            if label_text:
                clean_text = label_text.strip()
                # Remove the input's own text to avoid duplicates
                # Keep only unique options
                if clean_text and clean_text not in options:
                    options.append(clean_text)
                    element_map[clean_text] = click_target
                    input_map[clean_text] = inp
        
        if not options:
            print("   ⚠️ Could not extract options for choice group.")
            return

        print(f"   📋 Found options: {options}")
        
        # 2. Select best option via LLM or fallback
        best_option = None
        
        if self.llm_client:
            try:
                # Build context for LLM
                context = self.context_builder.build_full_context(None)
                
                # Use LLM to select the best option
                best_option = await self.llm_client.select_best_option(
                    options=options,
                    field_label=question,
                    applicant_context=context
                )
                print(f"   🤖 AI Selected: '{best_option}'")
            except Exception as e:
                print(f"   ⚠️ LLM selection failed: {e}")
                best_option = None
        
        # Fallback logic if LLM fails or is unavailable
        if not best_option:
            # Try field mapper first
            mapper_value = await self.field_mapper.get_value(question)
            if mapper_value:
                # Find closest match in options
                mapper_str = str(mapper_value).lower()
                for opt in options:
                    if mapper_str in opt.lower() or opt.lower() in mapper_str:
                        best_option = opt
                        print(f"   🔍 Mapper matched: '{best_option}'")
                        break
            
            # Last resort: intelligent default
            if not best_option:
                q_lower = question.lower()
                # Common patterns
                if "citizen" in q_lower or "authorized" in q_lower or "legally" in q_lower:
                    # Look for Yes/Authorized
                    for opt in options:
                        if any(x in opt.lower() for x in ["yes", "authorized", "citizen"]):
                            best_option = opt
                            break
                elif "sponsorship" in q_lower or "visa" in q_lower:
                    # Look for No (don't need sponsorship)
                    for opt in options:
                        if "no" in opt.lower() or "do not" in opt.lower():
                            best_option = opt
                            break
                
                # Ultimate fallback: first option
                if not best_option:
                    best_option = options[0]
                    print(f"   ⚠️ Using first option as fallback: '{best_option}'")
        
        # 3. Click the selected option
        if best_option and best_option in element_map:
            await self._click_radio_option(
                click_target=element_map[best_option],
                input_element=input_map.get(best_option),
                option_text=best_option
            )
        else:
            print(f"   ❌ Could not find element for selected option: '{best_option}'")


    async def _click_radio_option(self, click_target, input_element, option_text: str) -> None:
        """
        Robust radio button clicking with multiple fallback strategies.
        Prevents toggling by checking state first.
        """
        print(f"   🎯 Selecting: '{option_text}'")
        
        # 0. Check if already selected (Prevent Toggling)
        is_active = await click_target.evaluate("""el => {
            const check = (node) => {
                if (!node) return false;
                const style = window.getComputedStyle(node);
                return node.classList.contains('active') || 
                       node.classList.contains('selected') ||
                       node.classList.contains('checked') ||
                       node.classList.contains('is-selected') ||
                       node.classList.contains('is-active') ||
                       node.className.toLowerCase().includes('active') || 
                       node.className.toLowerCase().includes('selected') ||
                       node.className.toLowerCase().includes('checked') ||
                       node.getAttribute('aria-checked') === 'true' ||
                       node.getAttribute('aria-pressed') === 'true' ||
                       (node.tagName === 'INPUT' && node.checked) ||
                       (style.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
                        style.backgroundColor !== 'transparent' && 
                        !style.backgroundColor.includes('255, 255, 255'));
            };
            return check(el) || check(el.parentElement) || (el.querySelector && check(el.querySelector('input:checked')));
        }""")
        
        if is_active:
            print(f"   ✅ Option '{option_text}' already selected. Skipping click to avoid toggle.")
            return

        try:
            # Strategy 1: Standard click (works for most visible elements)
            if await click_target.is_visible():
                await click_target.click(force=True, timeout=2000)
                await asyncio.sleep(0.3)
                
                # Verify if it worked
                if input_element:
                    is_checked = await input_element.is_checked()
                    if is_checked:
                        print(f"   ✅ Successfully selected '{option_text}'")
                        return
        except Exception as e:
            print(f"   ⚠️ Standard click failed: {e}")
        
        # Strategy 2: JavaScript click on label
        try:
            print(f"   🔧 Trying JS click...")
            await click_target.evaluate("el => el.click()")
            await asyncio.sleep(0.2)
            
            if input_element:
                is_checked = await input_element.is_checked()
                if is_checked:
                    print(f"   ✅ JS click successful for '{option_text}'")
                    return
        except Exception as e:
            print(f"   ⚠️ JS click failed: {e}")
        
        # Strategy 3: Direct input manipulation (nuclear option)
        if input_element:
            try:
                print(f"   ☢️ Forcing radio input state for '{option_text}'")
                await input_element.evaluate("""el => {
                    el.checked = true;
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('click', {bubbles: true}));
                }""")
                await asyncio.sleep(0.2)
                print(f"   ✅ Force-set successful for '{option_text}'")
            except Exception as e:
                print(f"   ❌ Force-set failed: {e}")

    async def _handle_textarea(self, element, question: str, job: Job, application: Application) -> None:
         # Similar to Greenhouse
        common_answer = self.applicant.get_answer("", company=job.company, position=job.title) # Key mapping needed?
        # Use simple mapping for now
        if "cover letter" in question.lower():
             # Check if we have cover letter content
             cl = self.applicant.cover_letter_content
             if cl:
                 await element.fill(cl)
                 return

        # Use LLM if enabled
        if self.llm_client:
             ans = await self.answer_question_with_llm(question, job)
             if ans:
                 await element.fill(ans)
                 return
        
        application.add_question_for_review(question, "Long answer needed")

    async def _handle_input(self, element, question: str, job: Job) -> None:
        val = await self.field_mapper.get_value(question)
        if val:
            await element.fill(str(val))
            return

        # Fallback to LLM for one-liners (e.g. "How did you hear about us?")
        if self.llm_client:
             ans = await self.answer_question_with_llm(question, job)
             if ans:
                 await element.fill(ans)
                 return
                 
        print(f"   ⚠️ Could not determine answer for input: '{question}'")

    async def _verify_filled_state(self, page: Page) -> None:
        print("   🕵️ Verifying form state before submission...")
        
        # Re-scan for all question blocks
        # Using the robust selector we found earlier
        question_blocks = page.locator("div:has(> label), fieldset:has(> label), div[class*='container']:has(label)")
        count = await question_blocks.count()
        
        for i in range(count):
            block = question_blocks.nth(i)
            if not await block.is_visible(): continue
            
            label_el = block.locator("label").first
            q_text = await label_el.text_content()
            q_text = q_text.strip() if q_text else ""
            
            # Skip if we shouldn't answer
            if self._should_skip_question(q_text): continue
            
            # Check status
            is_filled = False
            
            # 1. Check Input/Textarea value
            input_el = block.locator("input:not([type='checkbox']):not([type='radio']), textarea").first
            if await input_el.count() > 0:
                val = await input_el.input_value()
                if val and len(val.strip()) > 0:
                    is_filled = True
            
            # 2. Comprehensive State Check (JS)
            if not is_filled:
                is_filled = await block.evaluate("""block => {
                    const check = (node) => {
                        if (!node) return false;
                        const style = window.getComputedStyle(node);
                        return node.classList.contains('active') || 
                               node.classList.contains('selected') ||
                               node.classList.contains('checked') ||
                               node.classList.contains('is-selected') ||
                               node.classList.contains('is-active') ||
                               node.className.toLowerCase().includes('active') || 
                               node.className.toLowerCase().includes('selected') ||
                               node.className.toLowerCase().includes('checked') ||
                               node.getAttribute('aria-checked') === 'true' ||
                               node.getAttribute('aria-pressed') === 'true' ||
                               (node.tagName === 'INPUT' && node.checked) ||
                               (style.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
                                style.backgroundColor !== 'transparent' && 
                                !style.backgroundColor.includes('255, 255, 255'));
                    };

                    // 1. Check text inputs/textareas
                    const inputs = block.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), textarea');
                    for (const input of inputs) {
                        if (input.value && input.value.trim().length > 0) return true;
                    }
                    
                    // 2. Check checkboxes/radios (native)
                    if (block.querySelector('input:checked')) return true;
                    
                    // 3. Check custom buttons/toggles (comprehensive)
                    const elements = block.querySelectorAll('button, [role="button"], label, div[class*="option"], div[class*="choice"], span');
                    for (const el of elements) {
                        if (check(el) || check(el.parentElement)) return true;
                    }
                    
                    // 4. Large blocks with text (last resort)
                    const text = block.innerText || "";
                    if (text.length > 500) return true;
                    
                    return false;
                }""")

            if not is_filled:
                print(f"   ⚠️ Field '{q_text}' appears EMPTY. Retrying...")
                # Call specific retry logic
                await self._retry_fill(block, q_text)

    async def _retry_fill(self, block, question: str) -> None:
        """
        Forcefully re-applies logic to a block that appeared empty.
        """
        # Determine the type of input again
        input_el = block.locator("input, textarea, select").first
        has_buttons = await block.locator("button, [role='button']").count() > 0
        
        if await input_el.count() > 0:
            tag = await input_el.evaluate("el => el.tagName.toLowerCase()")
            input_type = await input_el.get_attribute("type")
            
            if input_type in ["checkbox", "radio"]:
                # Re-run choice group or button group logic
                all_inputs = block.locator(f"input[type='{input_type}']")
                if await all_inputs.count() > 1:
                    await self._handle_choice_group(block, question, input_type)
                else:
                    await self._handle_button_group(block, question)
                return
                
            if tag == "textarea" or input_type == "text":
                # JS Force Fill
                ans = await self.field_mapper.get_value(question) or " "
                await input_el.evaluate(f"el => el.value = '{ans}'")
                await input_el.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
                print(f"      -> Forced JS fill for '{question}'")
                return

        if has_buttons:
            await self._handle_button_group(block, question)
             
    async def submit_application(self, page: Page) -> bool:
        # Verify before submitting
        await self._verify_filled_state(page)
        
        # Check for Review Mode (Pause Before Submit)
        # We need to access settings. Assuming base filler or we import it
        from src.utils.config import get_settings
        settings = get_settings()
        
        if settings.application.review_mode:
            print(f"   👀 REVIEW MODE ACTIVE (Value: {settings.application.review_mode})")
            print("   👀 REVIEW MODE: Pausing before submission.")
            print("   🛑 WAITING FOR USER INPUT: Review the form in the browser, then press Enter in this console to continue...")
            # We can't actually capture console input here easily in this environment without blocking the agent loop weirdly.
            # But since we use 'WaitMsBeforeAsync' in run_command, we can't interact via stdin easily unless we use send_command_input.
            # However, for the 'Assisted Mode' workflow requested by the user, we just need to PAUSE.
            # Let's implement a wait loop that allows the user to manually click submit if they want, OR we wait for a signal.
            
            # Better approach for this agentic environment: 
            # effectively 'Wait for user to manually click submit' OR 'Wait for user to signal continue'
            # But the user said "show me before submitting".
            
            print("   🛑 AUTOMATION PAUSED. Please review the application.")
            print("   👉 If everything looks good, YOU MUST click the 'Submit Application' button in the browser.")
            print("   👉 The automation will NOT click it for you in this mode.")
            
            # Wait loop that checks if success page is reached (user clicked submit)
            # Wait efficiently for up to 30 minutes
            for i in range(1800): 
                if i % 10 == 0:
                     print(f"   ⏳ Waiting for YOU to submit... ({i}s)")
                
                if await self._check_success(page):
                     print("   ✅ User submitted manually!")
                     return True
                await asyncio.sleep(1)
                
            print("   ❌ Timeout waiting for user submission.")
            return False

        submit_btn = page.locator(self.SELECTORS["submit"]).first
        
        if await submit_btn.count() > 0:
            print("   🚀 Clicking submit...")
            await submit_btn.click()
            await asyncio.sleep(2)
            
            # Check for immediate success
            if await self._check_success(page):
                return True
                
            # Check for spam block or generic failure
            msg = await page.content()
            if "spam" in msg.lower() or "captcha" in msg.lower() or await page.locator("text=spam").count() > 0:
                print("   ⚠️ Application flagged or CAPTCHA detected!")
                # ASSISTED MODE: Wait for user
                print("   🛑 WAITING FOR USER INPUT: Please solve CAPTCHA/Submit manually in the browser...")
                
                # Wait loop
                for i in range(120): # 10 minutes max
                    if i % 10 == 0:
                         print(f"   ⏳ Waiting for success URL... ({i*5}s)")
                    
                    if await self._check_success(page):
                        print("   ✅ Detected manual success!")
                        return True
                    
                    await asyncio.sleep(5)
            
    async def _check_success(self, page: Page) -> bool:
        url = page.url.lower()
        # Ashby success URLs usually have /confirmation
        if "confirmation" in url:
            return True
            
        # Check for specific success headers only
        # Avoid generic "submit application" text or footer text
        success_selector = "h1:has-text('Application received'), h2:has-text('Application received'), h3:has-text('Application received'), h1:has-text('Thank you'), h2:has-text('Thank you')"
        if await page.locator(success_selector).count() > 0:
            return True
            
        return False

    async def _handle_autocomplete(self, field, question: str) -> bool:
        # Ported from GreenhouseFiller
        # 1. Determine value
        value = self.field_mapper.get_value(question)
        if not value: return False
        
        print(f"DEBUG: Handling Autocomplete for '{question}' with '{value}'")
        
        try:
            # 1. Click to Focus
            await field.click()
            await asyncio.sleep(0.5)
            
            # 2. Type Value
            await field.clear()
            await field.press_sequentially(str(value), delay=100)
            await asyncio.sleep(2.0) # Wait for suggestions
            
            # 3. Try Clicking Suggestion
            # Ashby suggestions usually appear in a portal
            page = field.page
            suggestion_selectors = [
                 # Subagent Verified: "div[role='option']" works heavily
                 "div[role='option']", 
                 # Generic Ashby Option
                 "div[class*='option']", 
                 # React Select standard
                 "div[id*='react-select']", 
                 "li[role='option']"
            ]
            
            suggestion_clicked = False
            for sel in suggestion_selectors:
                 # Check visible options containing text first
                 suggestions = page.locator(f"{sel}:visible")
                 if await suggestions.count() > 0:
                      # Try to click the one matching our text loosely
                      # Or just the first one if it looks like a match?
                      # Let's try matching first
                      best_match = suggestions.filter(has_text=value).first
                      if await best_match.count() > 0:
                           await best_match.click()
                           suggestion_clicked = True
                           break
                      
                      # Fallback: click first
                      print(f"   -> Clicking visible suggestion fallback: {sel}")
                      await suggestions.first.click()
                      suggestion_clicked = True
                      break
            
            await asyncio.sleep(0.5)
            
            # 4. Fallback: Enter
            if not suggestion_clicked:
                 print("   -> No suggestion clicked, using Keyboard Enter")
                 await field.press("Enter")
            
            # 5. NUCLEAR OPTION: JS Injection (React Event Dispatch)
            # If the value isn't sticking, we force it.
            val_in_field = await field.input_value()
            if not val_in_field or len(val_in_field) < 2:
                 print(f"   ☢️ Autocomplete failed via typing... attempting JS Injection for '{value}'")
                 success = await field.page.evaluate("""(data) => {
                    const input = document.querySelector(data.selector);
                    if (!input) return false;
                    
                    // Set native value
                    input.value = data.value;
                    input.setAttribute('value', data.value);
                    
                    // Dispatch React-compatible events
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
                    input.dispatchEvent(new Event('blur', { bubbles: true }));
                    return true;
                 }""", {"selector": f"#{await field.get_attribute('id')}" if await field.get_attribute('id') else "input[type='text']", "value": value})
                 
            return True
        except Exception as e:
            print(f"   ❌ Autocomplete Error: {e}")
            return False

    async def _handle_button_group(self, block, question: str) -> None:
        print(f"DEBUG: Handling Button Group for '{question}'")
        
        # Extract button options with a broad reach
        buttons = await block.locator("button, div[role='button'], label, [class*='option'], [class*='button']").all()
        options = []
        element_map = {}
        
        for btn in buttons:
            # Check for direct text or nested text
            text = await btn.evaluate("""el => {
                const getVisibleText = (node) => {
                    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
                    if (node.nodeType !== Node.ELEMENT_NODE) return '';
                    const style = window.getComputedStyle(node);
                    if (style.display === 'none' || style.visibility === 'hidden') return '';
                    let text = '';
                    for (const child of node.childNodes) text += getVisibleText(child);
                    return text;
                };
                return getVisibleText(el);
            }""")
            if text:
                clean = text.strip()
                if clean and clean not in options:
                    # Filter out long texts which are usually questions, not options
                    if len(clean) < 30:
                        options.append(clean)
                        element_map[clean] = btn
        
        if not options:
            # Fallback: specific text search for Yes/No if general query fails
            for target in ["Yes", "No"]:
                btn = block.locator(f"text='{target}'").first
                if await btn.count() > 0:
                    options.append(target)
                    element_map[target] = btn
        
        if not options:
            print("   ⚠️ No button options found")
            return
        
        # Use LLM to select best option
        selected_option = None
        if self.llm_client:
            try:
                # Build context for LLM
                context = self.context_builder.build_full_context(None)
                
                # Use LLM to select the best option
                selected_option = await self.llm_client.select_best_option(
                    options=options, 
                    field_label=question, 
                    applicant_context=context
                )
                print(f"   🤖 AI Selected: '{selected_option}'")
            except Exception as e:
                print(f"   ⚠️ LLM failed: {e}")
                selected_option = None
        
        # Fallback to boolean logic
        if not selected_option:
            val = self.field_mapper.get_boolean_answer(question)
            if val is None:
                val = True
            selected_option = "Yes" if val else "No"
            print(f"   🔍 Using fallback selection: '{selected_option}'")
        
        # Click the selected button
        if selected_option in element_map:
             target_el = element_map[selected_option]
             
             # Attempt to find a corresponding hidden input for the selection
             # This helps with the click verification in _click_radio_option
             input_el = block.locator("input[type='radio'], input[type='checkbox']").filter(has_text=selected_option).first
             if await input_el.count() == 0:
                 # Try finding input by parent traversal if direct text match fails
                 try:
                     parent = target_el.locator("xpath=..")
                     nearby_input = parent.locator("input")
                     if await nearby_input.count() > 0:
                         input_el = nearby_input.first
                 except: pass
                 
             await self._click_radio_option(
                 click_target=target_el,
                 input_element=input_el if await input_el.count() > 0 else None,
                 option_text=selected_option
             )
        else:
             print(f"   ❌ Could not find element for selected option: '{selected_option}'")