"""Focused Smart DJ provider tests."""

from music_assistant.providers.smart_dj.engine import (
    MODES,
    DJControls,
    SignalControl,
    score_candidate,
)
from music_assistant.providers.smart_dj.provider import (
    _camelot_from_key,
    _upcoming_queue_window,
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


def test_upcoming_queue_window_starts_at_current_item() -> None:
    """Analysis begins at the active item, not the start of the queue."""
    items = [{"queue_index": i, "queue_item_id": str(i)} for i in range(8)]

    result = _upcoming_queue_window(items, current_index=3, limit=4)

    assert [item["queue_item_id"] for item in result] == ["3", "4", "5", "6"]


def test_upcoming_queue_window_preserves_unanalyzable_current_item() -> None:
    """A current item without provider metadata still anchors the queue window."""
    items = [
        {"queue_index": 0, "queue_item_id": "old"},
        {"queue_index": 1, "queue_item_id": "current", "item_id": None},
        {"queue_index": 2, "queue_item_id": "next"},
    ]

    result = _upcoming_queue_window(items, current_index=1, limit=0)

    assert [item["queue_item_id"] for item in result] == ["current"]
