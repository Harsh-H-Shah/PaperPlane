import re
from typing import Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    is_valid: bool
    score: float
    issues: list[str]
    suggestions: list[str]
    needs_human_review: bool
    review_reason: str = ""


class AnswerValidator:
    GENERIC_PHRASES = [
        "i am excited", "i am passionate", "i would love the opportunity",
        "i believe i would be a great fit", "team player", "fast learner",
        "hard worker", "results-driven", "think outside the box",
        "synergy", "leverage", "circle back",
    ]
    
    SENSITIVE_TOPICS = [
        "salary", "compensation", "pay", "money", "visa", "sponsorship",
        "immigration", "clearance", "security clearance", "criminal",
        "background check", "disability", "health", "religion",
        "political", "lawsuit", "fired", "terminated", "conflict",
    ]
    
    MIN_LENGTH = 20
    MIN_WORDS = 5
    
    def __init__(self):
        pass
    
    def validate(self, answer: str, question: str, min_length: int = 20, max_length: int = 2000, required_keywords: list[str] = None) -> ValidationResult:
        issues = []
        suggestions = []
        needs_review = False
        review_reason = ""
        score = 1.0
        
        if not answer or not answer.strip():
            return ValidationResult(
                is_valid=False, score=0.0, issues=["Answer is empty"],
                suggestions=["Generate a new answer"], needs_human_review=True, review_reason="Empty answer"
            )
        
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        for topic in self.SENSITIVE_TOPICS:
            if topic in question_lower or topic in answer_lower:
                needs_review = True
                review_reason = f"Sensitive topic detected: {topic}"
                issues.append(f"Contains sensitive topic: {topic}")
                score -= 0.3
                break
        
        if len(answer) < min_length:
            issues.append(f"Too short ({len(answer)} chars, min {min_length})")
            suggestions.append("Expand the answer with more details")
            score -= 0.2
        
        if len(answer) > max_length:
            issues.append(f"Too long ({len(answer)} chars, max {max_length})")
            suggestions.append("Shorten the answer")
            score -= 0.1
        
        words = answer.split()
        if len(words) < self.MIN_WORDS:
            issues.append(f"Too few words ({len(words)})")
            score -= 0.2
        
        generic_found = []
        for phrase in self.GENERIC_PHRASES:
            if phrase in answer_lower:
                generic_found.append(phrase)
        
        if generic_found:
            issues.append(f"Contains generic phrases: {', '.join(generic_found[:3])}")
            suggestions.append("Use more specific, authentic language")
            score -= 0.1 * len(generic_found)
        
        if required_keywords:
            missing = [kw for kw in required_keywords if kw.lower() not in answer_lower]
            if missing:
                issues.append(f"Missing keywords: {', '.join(missing)}")
                suggestions.append(f"Include: {', '.join(missing)}")
                score -= 0.1 * len(missing)
        
        caps_ratio = sum(1 for c in answer if c.isupper()) / max(len(answer), 1)
        if caps_ratio > 0.3:
            issues.append("Too many capital letters")
            suggestions.append("Use normal capitalization")
            score -= 0.1
        
        if self._has_repetition(answer):
            issues.append("Contains repetitive content")
            suggestions.append("Vary your language")
            score -= 0.1
        
        if not answer.rstrip().endswith(('.', '!', '?')):
            suggestions.append("End with proper punctuation")
            score -= 0.05
        
        if not any(word in answer_lower for word in ['i ', 'my ', "i'm", "i've"]):
            suggestions.append("Consider using first-person perspective")
        
        score = max(0.0, min(1.0, score))
        is_valid = score >= 0.5 and not needs_review
        
        if score < 0.6 and not needs_review:
            needs_review = True
            review_reason = "Low quality score"
        
        return ValidationResult(
            is_valid=is_valid, score=score, issues=issues,
            suggestions=suggestions, needs_human_review=needs_review, review_reason=review_reason
        )
    
    def _has_repetition(self, text: str) -> bool:
        words = text.lower().split()
        if len(words) < 10:
            return False
        
        trigrams = [tuple(words[i:i+3]) for i in range(len(words)-2)]
        unique_trigrams = set(trigrams)
        
        return len(unique_trigrams) < len(trigrams) * 0.8
    
    def needs_human_review(self, question: str) -> Tuple[bool, str]:
        question_lower = question.lower()
        
        for topic in self.SENSITIVE_TOPICS:
            if topic in question_lower:
                return True, f"Sensitive topic: {topic}"
        
        return False, ""
    
    def improve_answer(self, answer: str, issues: list[str]) -> str:
        improved = answer.strip()
        
        if improved and improved[0].islower():
            improved = improved[0].upper() + improved[1:]
        
        if improved and not improved.endswith(('.', '!', '?')):
            improved += '.'
        
        improved = re.sub(r'\s+', ' ', improved)
        
        filler_starts = ["I would say that ", "I think that ", "I believe that ", "Well, ", "So, ", "Basically, "]
        for filler in filler_starts:
            if improved.startswith(filler):
                improved = improved[len(filler):]
                improved = improved[0].upper() + improved[1:] if improved else improved
        
        return improved
