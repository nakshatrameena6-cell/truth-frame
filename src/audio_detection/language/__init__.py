"""Language detection and code-switching reporting package."""
from .detector import SUPPORTED_LANGUAGES, LanguageReport, detect_language

__all__ = ["SUPPORTED_LANGUAGES", "LanguageReport", "detect_language"]
