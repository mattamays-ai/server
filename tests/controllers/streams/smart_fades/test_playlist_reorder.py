from music_assistant.controllers.streams.smart_fades.playlist_reorder import (
    PlaylistRequirements,
    PlaylistTrack,
    SmartPlaylistReorder,
)
from music_assistant.models.audio_analysis import AudioAnalysisData


def _track(track_id: str, bpm: float, key: str) -> PlaylistTrack:
    return PlaylistTrack(
        track_id=track_id,
        analysis=AudioAnalysisData(
            bpm=bpm,
            key=key,
            mode="major",
            energy=0.7,
            danceability=0.8,
        ),
    )


def test_reorder_prefers_compatible_bpm_and_key() -> None:
    tracks = [
        _track("a", 120, "C"),
        _track("b", 121, "C"),
        _track("c", 145, "F#"),
    ]
    result = SmartPlaylistReorder(tracks).reorder(start_track_id="a")
    assert result[0] == "a"
    assert result[1] == "b"


def test_reorder_respects_exclusions() -> None:
    tracks = [_track("a", 120, "C"), _track("b", 121, "C")]
    result = SmartPlaylistReorder(tracks).reorder(
        PlaylistRequirements(excluded_ids=("b",)),
        start_track_id="a",
    )
    assert result == ["a"]


def test_reorder_fails_instead_of_breaking_hard_bpm_limit() -> None:
    tracks = [_track("a", 120, "C"), _track("b", 145, "C")]
    try:
        SmartPlaylistReorder(tracks).reorder(
            PlaylistRequirements(max_bpm_jump=5),
            start_track_id="a",
        )
    except ValueError:
        return
    raise AssertionError("expected hard requirement failure")
