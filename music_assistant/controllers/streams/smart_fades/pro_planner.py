"""Deeper automatic transition planning for Smart Fades.

This module deliberately contains no playback code. It turns analysis metadata and
user policy into a deterministic transition plan that the mixer can apply.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProAutoMixPolicy:
    """User-facing policy for deeper automatic transitions."""

    enabled: bool = True
    min_bars: int = 4
    max_bars: int = 16
    max_bpm_change_pct: float = 5.0
    prefer_harmonic_keys: bool = True
    energy_protection: bool = True
    vocal_protection: bool = True


@dataclass(frozen=True, slots=True)
class TransitionPlan:
    """Deterministic plan consumed by the SmartCrossFade mixer."""

    bars: int
    bpm_change_pct: float
    harmonic: bool | None
    energy_delta: float | None
    vocal_overlap_risk: float | None
    reason: str


def _camelot_compatible(first: object, second: object) -> bool | None:
    """Return Camelot compatibility when both values are available."""
    if not first or not second:
        return None
    a = str(first).upper()
    b = str(second).upper()
    if len(a) < 2 or len(b) < 2:
        return None
    try:
        anum, bnum = int(a[:-1]), int(b[:-1])
    except ValueError:
        return None
    if a[-1] not in "AB" or b[-1] not in "AB":
        return None
    return anum == bnum and a[-1] == b[-1] or (
        a[-1] == b[-1] and ((anum - bnum) % 12 in (1, 11))
    ) or (anum == bnum and a[-1] != b[-1])


def plan_transition(
    fade_out_analysis: object,
    fade_in_analysis: object,
    policy: ProAutoMixPolicy | None = None,
) -> TransitionPlan:
    """Plan a deeper transition without requiring a particular analysis provider."""
    policy = policy or ProAutoMixPolicy()
    bpm_out = float(getattr(fade_out_analysis, "bpm", 0) or 0)
    bpm_in = float(getattr(fade_in_analysis, "bpm", 0) or 0)
    bpm_change = abs(1.0 - (bpm_in / bpm_out)) * 100 if bpm_out and bpm_in else 0.0

    harmonic = _camelot_compatible(
        getattr(fade_out_analysis, "camelot", None),
        getattr(fade_in_analysis, "camelot", None),
    )
    energy_out = getattr(fade_out_analysis, "energy", None)
    energy_in = getattr(fade_in_analysis, "energy", None)
    energy_delta = (
        float(energy_in) - float(energy_out)
        if energy_out is not None and energy_in is not None
        else None
    )

    vocal_out = getattr(fade_out_analysis, "vocal_activity", None)
    vocal_in = getattr(fade_in_analysis, "vocal_activity", None)
    vocal_risk = (
        float(vocal_out) * float(vocal_in)
        if vocal_out is not None and vocal_in is not None
        else None
    )

    bars = 8
    reason = "balanced"
    if policy.prefer_harmonic_keys and harmonic is False:
        bars = 4
        reason = "shortened_for_key_clash"
    elif policy.energy_protection and energy_delta is not None and energy_delta < -0.2:
        bars = 12
        reason = "extended_for_energy_drop"
    elif policy.vocal_protection and vocal_risk is not None and vocal_risk > 0.35:
        bars = 4
        reason = "shortened_for_vocal_overlap"

    if bpm_change > policy.max_bpm_change_pct:
        bars = min(bars, 4)
        reason = "shortened_for_tempo_gap"

    bars = max(policy.min_bars, min(policy.max_bars, bars))
    return TransitionPlan(
        bars=bars,
        bpm_change_pct=round(bpm_change, 3),
        harmonic=harmonic,
        energy_delta=energy_delta,
        vocal_overlap_risk=vocal_risk,
        reason=reason,
    )
