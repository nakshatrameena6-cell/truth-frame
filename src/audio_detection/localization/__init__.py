"""Localization package for partial-spoof detection and speech windowing."""
from .partial_spoof import (
    LocalizationResult,
    ScoredSegment,
    generate_speech_windows,
    localize_partial_spoofs,
    score_speech_segments,
)

__all__ = [
    "LocalizationResult",
    "ScoredSegment",
    "generate_speech_windows",
    "localize_partial_spoofs",
    "score_speech_segments",
]
