"""
Answer validator - validates and improves LLM-generated answers.
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of answer validation"""
    is_valid: bool
    score: float  # 0.0 to 1.0
    issues: list[str]
    suggestions: list[str]
    needs_human_review: bool
    review_reason: str = ""


class AnswerValidator:
    """
    Validates LLM-generated answers for job applications.
    Ensures answers are appropriate, professional, and meet requirements.
    """
    
    # Words/phrases that indicate low-quality generic answers
    GENERIC_PHRASES = [
        "i am excited",
        "i am passionate",
        "i would love the opportunity",
        "i believe i would be a great fit",
        "team player",
        "fast learner",
        "hard worker",
        "results-driven",
        "think outside the box",
        "synergy",
        "leverage",
        "circle back",
    ]
    
    # Topics that ALWAYS need human review
    SENSITIVE_TOPICS = [
        "salary",
        "compensation",
        "pay",
        "money",
        "visa",
        "sponsorship",
        "immigration",
        "clearance",
        "security clearance",
        "criminal",
        "background check",
        "disability",
        "health",
        "religion",
        "political",
        "lawsuit",
        "fired",
        "terminated",
        "conflict",
    ]
    
    # Minimum quality thresholds
    MIN_LENGTH = 20
    MIN_WORDS = 5
    
    def __init__(self):
        pass
    
    def validate(
        self,
        answer: str,
        question: str,
        min_length: int = 20,
        max_length: int = 2000,
        required_keywords: list[str] = None,
    ) -> ValidationResult:
        """
        Validate an answer for a job application question.
        
        Args:
            answer: The generated answer
            question: The original question
            min_length: Minimum character length
            max_length: Maximum character length
            required_keywords: Keywords that should appear in answer
        
        Returns:
            ValidationResult with validation details
        """
        issues = []
        suggestions = []
        needs_review = False
        review_reason = ""
        score = 1.0
        
        # Check if answer exists
        if not answer or not answer.strip():
            return ValidationResult(
                is_valid=False,
                score=0.0,
                issues=["Answer is empty"],
                suggestions=["Generate a new answer"],
                needs_human_review=True,
                review_reason="Empty answer"
            )
        
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        # Check for sensitive topics
        for topic in self.SENSITIVE_TOPICS:
            if topic in question_lower or topic in answer_lower:
                needs_review = True
                review_reason = f"Sensitive topic detected: {topic}"
                issues.append(f"Contains sensitive topic: {topic}")
                score -= 0.3
                break
        
        # Check length
        if len(answer) < min_length:
            issues.append(f"Too short ({len(answer)} chars, min {min_length})")
            suggestions.append("Expand the answer with more details")
            score -= 0.2
        
        if len(answer) > max_length:
            issues.append(f"Too long ({len(answer)} chars, max {max_length})")
            suggestions.append("Shorten the answer")
            score -= 0.1
        
        # Check word count
        words = answer.split()
        if len(words) < self.MIN_WORDS:
            issues.append(f"Too few words ({len(words)})")
            score -= 0.2
        
        # Check for generic phrases
        generic_found = []
        for phrase in self.GENERIC_PHRASES:
            if phrase in answer_lower:
                generic_found.append(phrase)
        
        if generic_found:
            issues.append(f"Contains generic phrases: {', '.join(generic_found[:3])}")
            suggestions.append("Use more specific, authentic language")
            score -= 0.1 * len(generic_found)
        
        # Check for required keywords
        if required_keywords:
            missing = [kw for kw in required_keywords if kw.lower() not in answer_lower]
            if missing:
                issues.append(f"Missing keywords: {', '.join(missing)}")
                suggestions.append(f"Include: {', '.join(missing)}")
                score -= 0.1 * len(missing)
        
        # Check for all caps (shouting)
        caps_ratio = sum(1 for c in answer if c.isupper()) / max(len(answer), 1)
        if caps_ratio > 0.3:
            issues.append("Too many capital letters")
            suggestions.append("Use normal capitalization")
            score -= 0.1
        
        # Check for repetition
        if self._has_repetition(answer):
            issues.append("Contains repetitive content")
            suggestions.append("Vary your language")
            score -= 0.1
        
        # Check for proper sentences
        if not answer.rstrip().endswith(('.', '!', '?')):
            suggestions.append("End with proper punctuation")
            score -= 0.05
        
        # Check for first person (appropriate for applications)
        if not any(word in answer_lower for word in ['i ', 'my ', "i'm", "i've"]):
            suggestions.append("Consider using first-person perspective")
        
        # Normalize score
        score = max(0.0, min(1.0, score))
        
        # Determine if valid
        is_valid = score >= 0.5 and not needs_review
        
        # Add review flag for low scores
        if score < 0.6 and not needs_review:
            needs_review = True
            review_reason = "Low quality score"
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            issues=issues,
            suggestions=suggestions,
            needs_human_review=needs_review,
            review_reason=review_reason
        )
    
    def _has_repetition(self, text: str) -> bool:
        """Check if text has repetitive phrases"""
        words = text.lower().split()
        if len(words) < 10:
            return False
        
        # Check for repeated 3-word phrases
        trigrams = [tuple(words[i:i+3]) for i in range(len(words)-2)]
        unique_trigrams = set(trigrams)
        
        # If more than 20% are duplicates, flag it
        return len(unique_trigrams) < len(trigrams) * 0.8
    
    def needs_human_review(self, question: str) -> Tuple[bool, str]:
        """
        Check if a question should always require human review.
        
        Returns:
            (needs_review, reason)
        """
        question_lower = question.lower()
        
        for topic in self.SENSITIVE_TOPICS:
            if topic in question_lower:
                return True, f"Sensitive topic: {topic}"
        
        return False, ""
    
    def improve_answer(self, answer: str, issues: list[str]) -> str:
        """
        Apply automatic fixes to common issues.
        Returns improved answer.
        """
        improved = answer.strip()
        
        # Fix capitalization at start
        if improved and improved[0].islower():
            improved = improved[0].upper() + improved[1:]
        
        # Add period if missing
        if improved and not improved.endswith(('.', '!', '?')):
            improved += '.'
        
        # Remove excessive whitespace
        improved = re.sub(r'\s+', ' ', improved)
        
        # Remove common filler phrases at the start
        filler_starts = [
            "I would say that ",
            "I think that ",
            "I believe that ",
            "Well, ",
            "So, ",
            "Basically, ",
        ]
        for filler in filler_starts:
            if improved.startswith(filler):
                improved = improved[len(filler):]
                improved = improved[0].upper() + improved[1:] if improved else improved
        
        return improved
