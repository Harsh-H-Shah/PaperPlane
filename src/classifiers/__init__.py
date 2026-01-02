"""
Classifiers Package - Detect application portal types

Supports: Workday, Ashby, Greenhouse, Lever, ADP, Oracle, LinkedIn Easy Apply, and more.
"""

from src.classifiers.detector import ApplicationDetector, detect_application_type

__all__ = [
    "ApplicationDetector",
    "detect_application_type",
]
