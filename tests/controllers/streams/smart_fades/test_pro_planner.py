from types import SimpleNamespace

from music_assistant.controllers.streams.smart_fades.pro_planner import (
    ProAutoMixPolicy,
    plan_transition,
)


def test_harmonic_clash_shortens_transition() -> None:
    out = SimpleNamespace(bpm=124, camelot="8A", energy=0.7, vocal_activity=0.1)
    incoming = SimpleNamespace(bpm=125, camelot="2B", energy=0.7, vocal_activity=0.1)
    plan = plan_transition(out, incoming)
    assert plan.bars == 4
    assert plan.reason == "shortened_for_key_clash"


def test_energy_drop_extends_transition() -> None:
    out = SimpleNamespace(bpm=124, camelot="8A", energy=0.8, vocal_activity=0.1)
    incoming = SimpleNamespace(bpm=124, camelot="9A", energy=0.5, vocal_activity=0.1)
    plan = plan_transition(out, incoming)
    assert plan.bars == 12
    assert plan.reason == "extended_for_energy_drop"


def test_large_tempo_gap_shortens_transition() -> None:
    out = SimpleNamespace(bpm=100)
    incoming = SimpleNamespace(bpm=130)
    plan = plan_transition(out, incoming, ProAutoMixPolicy(max_bpm_change_pct=5))
    assert plan.bars == 4
    assert plan.reason == "shortened_for_tempo_gap"
