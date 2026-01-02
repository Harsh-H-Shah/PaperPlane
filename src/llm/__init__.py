"""
LLM Package - Language model integration for intelligent question answering

IMPORTANT: Uses Gemini Pro free tier with strict rate limiting:
- 15 requests per minute
- 1 million tokens per month
- 1500 RPD (requests per day)
"""

from src.llm.gemini import GeminiClient, get_llm_client
from src.llm.prompts import PromptTemplates
from src.llm.answer_validator import AnswerValidator
from src.llm.context_builder import ContextBuilder

__all__ = [
    "GeminiClient",
    "get_llm_client",
    "PromptTemplates",
    "AnswerValidator",
    "ContextBuilder",
]
