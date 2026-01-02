"""
Gemini Pro API client with strict rate limiting for free tier.

FREE TIER LIMITS (as of 2024):
- 15 requests per minute (RPM)
- 1,500 requests per day (RPD)
- 1 million tokens per month
- 32,000 tokens per minute

We implement conservative rate limiting to avoid charges:
- Max 10 RPM (buffer from 15 limit)
- Track daily usage
- Warn when approaching limits
"""

import time
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from threading import Lock

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from src.utils.config import get_settings


class RateLimiter:
    """
    Rate limiter to stay within Gemini free tier limits.
    Tracks requests per minute, per day, and monthly tokens.
    """
    
    # Conservative limits (below actual free tier limits)
    MAX_RPM = 10  # Actual: 15
    MAX_RPD = 1000  # Actual: 1500
    MAX_MONTHLY_TOKENS = 900_000  # Actual: 1M
    MIN_REQUEST_INTERVAL = 6.0  # Seconds between requests (ensures <10 RPM)
    
    def __init__(self, usage_file: str = "data/llm_usage.json"):
        self.usage_file = Path(usage_file)
        self.lock = Lock()
        self.last_request_time = 0.0
        self._load_usage()
    
    def _load_usage(self) -> None:
        """Load usage data from file"""
        self.usage = {
            "daily_requests": 0,
            "monthly_tokens": 0,
            "date": str(date.today()),
            "month": date.today().month,
            "requests_log": []
        }
        
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    saved = json.load(f)
                    
                # Reset daily count if new day
                if saved.get("date") != str(date.today()):
                    saved["daily_requests"] = 0
                    saved["date"] = str(date.today())
                    saved["requests_log"] = []
                
                # Reset monthly count if new month
                if saved.get("month") != date.today().month:
                    saved["monthly_tokens"] = 0
                    saved["month"] = date.today().month
                
                self.usage = saved
            except Exception:
                pass
    
    def _save_usage(self) -> None:
        """Save usage data to file"""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_file, 'w') as f:
            json.dump(self.usage, f, indent=2)
    
    def can_make_request(self) -> tuple[bool, str]:
        """
        Check if we can make a request.
        Returns (can_proceed, reason_if_not)
        """
        with self.lock:
            # Check daily limit
            if self.usage["daily_requests"] >= self.MAX_RPD:
                return False, f"Daily limit reached ({self.MAX_RPD} requests). Resets at midnight."
            
            # Check monthly token limit
            if self.usage["monthly_tokens"] >= self.MAX_MONTHLY_TOKENS:
                return False, f"Monthly token limit reached ({self.MAX_MONTHLY_TOKENS:,} tokens)."
            
            # Check rate limiting (requests per minute)
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                wait_time = self.MIN_REQUEST_INTERVAL - elapsed
                return False, f"Rate limited. Wait {wait_time:.1f}s."
            
            return True, ""
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                wait_time = self.MIN_REQUEST_INTERVAL - elapsed
                time.sleep(wait_time)
    
    def record_request(self, tokens_used: int = 0) -> None:
        """Record a completed request"""
        with self.lock:
            self.usage["daily_requests"] += 1
            self.usage["monthly_tokens"] += tokens_used
            self.usage["requests_log"].append({
                "timestamp": datetime.now().isoformat(),
                "tokens": tokens_used
            })
            # Keep only last 100 log entries
            self.usage["requests_log"] = self.usage["requests_log"][-100:]
            self.last_request_time = time.time()
            self._save_usage()
    
    def get_usage_stats(self) -> dict:
        """Get current usage statistics"""
        return {
            "daily_requests": self.usage["daily_requests"],
            "daily_limit": self.MAX_RPD,
            "daily_remaining": self.MAX_RPD - self.usage["daily_requests"],
            "monthly_tokens": self.usage["monthly_tokens"],
            "monthly_limit": self.MAX_MONTHLY_TOKENS,
            "monthly_remaining": self.MAX_MONTHLY_TOKENS - self.usage["monthly_tokens"],
        }
    
    def is_near_limit(self) -> bool:
        """Check if we're approaching limits (>80% used)"""
        daily_pct = self.usage["daily_requests"] / self.MAX_RPD
        monthly_pct = self.usage["monthly_tokens"] / self.MAX_MONTHLY_TOKENS
        return daily_pct > 0.8 or monthly_pct > 0.8


class GeminiClient:
    """
    Gemini Pro API client with rate limiting and safety measures.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        
        if not self.api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY in .env file.\n"
                "Get your free key at: https://makersuite.google.com/app/apikey"
            )
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Use gemini-1.5-flash for better free tier limits
        # gemini-1.5-flash has higher rate limits than gemini-pro
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Rate limiter
        self.rate_limiter = RateLimiter()
        
        # Default generation config (conservative tokens)
        self.default_config = GenerationConfig(
            max_output_tokens=300,  # Keep responses short to save tokens
            temperature=0.7,
        )
        
        # Track if we've shown the limit warning
        self._limit_warning_shown = False
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7,
        system_instruction: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a response from Gemini.
        
        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens in response (default 300 to save quota)
            temperature: Creativity (0.0-1.0)
            system_instruction: Optional system context
        
        Returns:
            Generated text or None if failed/rate limited
        """
        # Check rate limits
        can_proceed, reason = self.rate_limiter.can_make_request()
        if not can_proceed:
            print(f"⚠️ LLM Request blocked: {reason}")
            return None
        
        # Wait if needed for rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Warn if approaching limits
        if self.rate_limiter.is_near_limit() and not self._limit_warning_shown:
            stats = self.rate_limiter.get_usage_stats()
            print(f"⚠️ Approaching LLM limits: {stats['daily_requests']}/{stats['daily_limit']} daily, "
                  f"{stats['monthly_tokens']:,}/{stats['monthly_limit']:,} monthly tokens")
            self._limit_warning_shown = True
        
        try:
            # Build the full prompt
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"
            
            # Configure generation
            config = GenerationConfig(
                max_output_tokens=min(max_tokens, 500),  # Cap at 500 to save tokens
                temperature=temperature,
            )
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=config,
            )
            
            # Extract text
            if response and response.text:
                # Estimate tokens (rough: 1 token ≈ 4 chars)
                input_tokens = len(full_prompt) // 4
                output_tokens = len(response.text) // 4
                total_tokens = input_tokens + output_tokens
                
                # Record usage
                self.rate_limiter.record_request(total_tokens)
                
                return response.text.strip()
            
            return None
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific errors
            if "quota" in error_msg or "rate" in error_msg:
                print(f"⚠️ Rate limit exceeded: {e}")
                # Record as if we made a request to prevent rapid retries
                self.rate_limiter.record_request(0)
            elif "api key" in error_msg:
                print(f"❌ Invalid API key: {e}")
            else:
                print(f"❌ LLM Error: {e}")
            
            return None
    
    def answer_application_question(
        self,
        question: str,
        job_title: str,
        company: str,
        applicant_context: str,
        max_length: int = 500,
    ) -> Optional[str]:
        """
        Generate an answer for a job application question.
        
        Args:
            question: The application question
            job_title: Job being applied for
            company: Company name
            applicant_context: Info about the applicant
            max_length: Character limit for answer
        
        Returns:
            Generated answer or None
        """
        prompt = f"""You are helping someone apply for a {job_title} position at {company}.

Answer the following application question professionally and concisely.
Keep the answer under {max_length} characters.
Be authentic and specific, avoiding generic responses.

Applicant Background:
{applicant_context}

Question: {question}

Answer (be concise and professional):"""

        # Calculate appropriate token limit based on char limit
        # Rough estimate: 1 token ≈ 4 characters
        max_tokens = min(max_length // 3, 300)
        
        return self.generate(prompt, max_tokens=max_tokens, temperature=0.7)
    
    def get_usage_stats(self) -> dict:
        """Get current API usage statistics"""
        return self.rate_limiter.get_usage_stats()
    
    def is_available(self) -> bool:
        """Check if LLM is available (not rate limited)"""
        can_proceed, _ = self.rate_limiter.can_make_request()
        return can_proceed


# Global client instance
_client: Optional[GeminiClient] = None


def get_llm_client() -> GeminiClient:
    """Get the global LLM client instance"""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
