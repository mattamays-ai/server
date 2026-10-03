"""Data models for Smart Fades configuration."""

from enum import StrEnum


class SmartFadesMode(StrEnum):
    """Smart fades modes."""

    SMART_CROSSFADE = "smart_crossfade"
    STANDARD_CROSSFADE = "standard_crossfade"
    DISABLED = "disabled"
    LONG_BLEND = "long_blend"
    SHORT_BLEND = "short_blend"
    VOCAL_SAFE = "vocal_safe"
    TEMPO_MATCH = "tempo_match"
    CLEAN_BLEND = "clean_blend"


class SmartFadesProfile(StrEnum):
    """Fine-grained smart fade profiles."""

    AUTO = "auto"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    VOCAL_SAFE = "vocal_safe"
    TEMPO_MATCH = "tempo_match"
    HARMONIC = "harmonic"
    CLEAN = "clean"
