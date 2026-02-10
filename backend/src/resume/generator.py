
import json
import subprocess
import shutil
from pathlib import Path


from jinja2 import Environment, FileSystemLoader


from src.llm.gemini import GeminiClient

class ResumeGenerator:
    def __init__(self, profile_path: str = "data/profile.json", output_dir: str = "data/resumes"):
        self.profile_path = Path(profile_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.env = Environment(
            loader=FileSystemLoader("src/resume/templates"),
            block_start_string='{%',
            block_end_string='%}',
            variable_start_string='{{',
            variable_end_string='}}',
            comment_start_string='((=',
            comment_end_string='=))',
        )
        
        self.llm = GeminiClient()

    def load_profile(self) -> dict:
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Profile not found at {self.profile_path}")
        
        with open(self.profile_path, 'r') as f:
            return json.load(f)

    def generate(self, variant: str = None, job_description: str = None) -> Path:
        """
        Generates a PDF resume based on variant and JD.
        """
        profile = self.load_profile()
        final_data = self._customize_profile(profile, variant, job_description)
        
        # Render LaTeX
        template = self.env.get_template("classic.tex")
        latex_content = template.render(**final_data)
        
        # Save .tex file
        filename = f"resume_{variant or 'default'}_{json.dumps(final_data['personal']['last_name']).strip(chr(34))}.tex"
        tex_path = self.output_dir / filename
        
        with open(tex_path, 'w') as f:
            f.write(latex_content)
        
        # Compile PDF
        pdf_path = self._compile_pdf(tex_path)
        return pdf_path

    def _customize_profile(self, profile: dict, variant: str, jd: str) -> dict:
        """
        Filters and customizes the profile data.
        """
        # 1. Apply Variant (Filter Experience/Projects)
        if variant and "resume_configurations" in profile:
             config = profile["resume_configurations"].get(variant)
             if config:
                 if "experience_ids" in config:
                     target_ids = set(map(str, config["experience_ids"]))
                     profile["experience"] = [
                         e for i, e in enumerate(profile["experience"]) 
                         if str(i) in target_ids or str(e.get("id", "")).lower() in target_ids
                     ]
                 if "project_ids" in config:
                     target_ids = set(map(str, config["project_ids"]))
                     profile["projects"] = [
                         p for i, p in enumerate(profile["projects"])
                         if str(i) in target_ids or str(p.get("id", "")).lower() in target_ids
                     ]
                 if "skill_categories" in config:
                     # Filter and Order skills
                     ordered_skills = {}
                     for cat in config["skill_categories"]:
                         if cat in profile["skills"]:
                             ordered_skills[cat] = profile["skills"][cat]
                     profile["skills"] = ordered_skills
        
        # 2. AI Customization (Skills re-ordering based on JD)
        if jd:
            self._tailor_resume(profile, jd)
            
        # Flatten skills for template
        # Convert list of objects to list of strings if necessary, or keep structure
        # Template expects dict of list of strings: skills.languages = ["Python", ...]
        
        flat_skills = {}
        if "skills" in profile:
            for cat, items in profile["skills"].items():
                safe_cat = self._escape_latex_string(cat)
                if isinstance(items, list):
                    if items and isinstance(items[0], dict) and "name" in items[0]:
                         flat_skills[safe_cat] = [i["name"] for i in items]
                    else:
                         flat_skills[safe_cat] = items
        profile["skills"] = flat_skills

        return self._sanitize_for_latex(profile)

    def _tailor_resume(self, profile: dict, jd: str) -> None:
        """
        Uses LLM to highlight relevant skills based on JD.
        Modifies profile in-place.
        """
        if not self.llm:
            return

        print("   🤖 AI tailoring resume to job description...")
        
        # Extract all available skills
        all_skills = []
        original_skills_map = profile.get("skills", {})
        
        for cat, skills in original_skills_map.items():
            if isinstance(skills, list):
                # Handle both string and dict skills
                names = [s["name"] if isinstance(s, dict) and "name" in s else str(s) for s in skills]
                all_skills.extend(names)
        
        if not all_skills:
            return

        prompt = f"""
        Job Description Excerpt:
        {jd[:2000]}...
        
        Candidate Skills:
        {', '.join(all_skills)}
        
        Task:
        Identify the top 6-8 most critical skills from the Candidate Skills list that match the Job Description.
        Return ONLY a JSON list of strings (e.g. ["Python", "AWS", "React"]).
        Do not explain.
        """
        
        try:
            response = self.llm.generate(prompt, temperature=0.2)
            if response:
                # Clean potential markdown
                clean_json = response.replace("```json", "").replace("```", "").strip()
                import json
                top_skills = json.loads(clean_json)
                
                if isinstance(top_skills, list) and len(top_skills) > 0:
                    # Move 'Highlights' to the top of the skills dictionary
                    # Note: We create a new dict to control order
                    new_skills = {"Highlights": top_skills}
                    # Add remaining categories
                    new_skills.update(original_skills_map)
                    profile["skills"] = new_skills
                    print(f"      ✅ tailored {len(top_skills)} skills to 'Highlights'")
                    
        except Exception as e:
            print(f"      ⚠️ AI tailoring failed: {e}")

    def _sanitize_for_latex(self, data):
        """Recursively escape LaTeX special characters in data"""
        if isinstance(data, dict):
            # Only sanitize values, keep keys as-is for structure/template access
            return {k: self._sanitize_for_latex(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_latex(v) for v in data]
        elif isinstance(data, str):
            return self._escape_latex_string(data)
        return data

    def _escape_latex_string(self, text: str) -> str:
        CHARS = {
            '&':  r'\&',
            '%':  r'\%',
            '$':  r'\$',
            '#':  r'\#',
            '_':  r'\_',
            '{':  r'\{',
            '}':  r'\}',
            '~':  r'\textasciitilde{}',
            '^':  r'\textasciicircum{}',
            '\\': r'\textbackslash{}',
        }
        return "".join([CHARS.get(char, char) for char in text])

    def _compile_pdf(self, tex_path: Path) -> Path:
        """
        Compiles .tex to .pdf using pdflatex.
        """
        if not shutil.which("pdflatex"):
            raise RuntimeError("pdflatex not found. Please install texlive-latex-base.")
            
        try:
            # Run pdflatex twice for formatting/references
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(self.output_dir), str(tex_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            pdf_filename = tex_path.with_suffix('.pdf').name
            return self.output_dir / pdf_filename
            
        except subprocess.CalledProcessError as e:
            print(f"LaTeX Error: {e.stdout.decode()}")
            raise RuntimeError("Failed to compile resume PDF.")
