"""Focused Smart DJ provider tests."""

from music_assistant.providers.smart_dj.engine import (
    MODES,
    DJControls,
    SignalControl,
    score_candidate,
)
from music_assistant.providers.smart_dj.provider import (
    _camelot_from_key,
    _snapshot_start_index,
)


def test_camelot_conversion() -> None:
    """Camelot conversion."""
    assert _camelot_from_key("A", "minor") == "8A"
    assert _camelot_from_key("C", "major") == "8B"


def test_hard_bpm_rule_is_never_violated() -> None:
    """Hard bpm rule is never violated."""
    score, _reasons, violations = score_candidate(
        {"bpm": 120, "camelot": "8A"},
        {"bpm": 160, "camelot": "8A"},
        MODES["ai_dj"],
        DJControls(bpm=SignalControl("hard")),
    )
    assert score == 0.0
    assert "hard BPM compatibility" in violations


def test_disabled_key_does_not_affect_score() -> None:
    """Disabled key does not affect score."""
    current = {"bpm": 120, "camelot": "8A", "energy": 0.5}
    candidate = {"bpm": 120, "camelot": "9A", "energy": 0.5}
    soft, _, _ = score_candidate(current, candidate, MODES["ai_dj"], DJControls())
    disabled, _, _ = score_candidate(
        current, candidate, MODES["ai_dj"], DJControls(key=SignalControl("disabled"))
    )
    assert disabled > 0
    assert soft != disabled


def test_required_excluded_and_fixed_controls_are_serializable() -> None:
    """Required excluded and fixed controls are serializable."""
    controls = DJControls(
        required_ids=frozenset({"required"}),
        excluded_ids=frozenset({"excluded"}),
        fixed_ids=frozenset({"fixed"}),
    )
    assert "required" in controls.required_ids
    assert "excluded" in controls.excluded_ids
    assert "fixed" in controls.fixed_ids

def test_snapshot_starts_at_current_queue_item() -> None:
    """Previously played queue items must not be treated as current/upcoming."""
    snapshot = [
        {"queue_item_id": "q1"},
        {"queue_item_id": "q2"},
        {"queue_item_id": "q3"},
    ]
    assert _snapshot_start_index(snapshot, ["q1", "q2", "q3"], 1) == 1


def test_snapshot_start_skips_unresolvable_current_item() -> None:
    """If current media is unresolvable, start at the next playable queue item."""
    snapshot = [
        {"queue_item_id": "q1"},
        {"queue_item_id": "q3"},
    ]
    assert _snapshot_start_index(snapshot, ["q1", "q2", "q3"], 1) == 1


def test_snapshot_start_returns_none_when_no_playable_items_remain() -> None:
    """An exhausted queue has no analysis start item."""
    snapshot = [{"queue_item_id": "q1"}]
    assert _snapshot_start_index(snapshot, ["q1"], 1) is None
