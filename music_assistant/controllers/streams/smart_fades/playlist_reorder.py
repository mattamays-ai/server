"""Playlist intelligence for Smart Fades.

Ranks candidate next tracks by transition quality while enforcing hard
playlist requirements before optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Iterable

from music_assistant.models.audio_analysis import AudioAnalysisData


@dataclass(frozen=True, kw_only=True)
class PlaylistRequirements:
    """Hard and soft requirements for Smart Reorder."""

    required_ids: tuple[str, ...] = ()
    excluded_ids: tuple[str, ...] = ()
    fixed_positions: dict[int, str] = field(default_factory=dict)
    max_bpm_jump: float | None = None
    allowed_modes: tuple[str, ...] = ()
    target_bpm: float | None = None
    target_key: str | None = None
    prefer_instrumental: bool = False
    keep_artist_separation: int = 0
    custom_weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class PlaylistTrack:
    """A track plus its analysis metadata."""

    track_id: str
    analysis: AudioAnalysisData


class SmartPlaylistReorder:
    """Optimize playlist order for musical flow and user requirements."""

    def __init__(self, tracks: Iterable[PlaylistTrack]) -> None:
        self.tracks = tuple(tracks)

    @staticmethod
    def _compatibility(a: AudioAnalysisData, b: AudioAnalysisData) -> float:
        """Return 0..1 transition compatibility."""
        if not a.bpm or not b.bpm:
            return 0.0

        bpm_delta = abs(a.bpm - b.bpm)
        bpm_score = exp(-bpm_delta / 12.0)

        key_score = 0.5
        if a.key and b.key:
            key_score = 1.0 if a.key == b.key else 0.35
            if a.mode and b.mode and a.mode != b.mode:
                key_score *= 0.8

        energy_score = 1.0
        if a.energy is not None and b.energy is not None:
            energy_score = 1.0 - min(abs(a.energy - b.energy), 1.0)

        dance_score = 1.0
        if a.danceability is not None and b.danceability is not None:
            dance_score = 1.0 - min(abs(a.danceability - b.danceability), 1.0)

        return (
            0.40 * bpm_score
            + 0.30 * key_score
            + 0.20 * energy_score
            + 0.10 * dance_score
        )

    def _allowed(self, track: PlaylistTrack, used: set[str], position: int, req: PlaylistRequirements) -> bool:
        if track.track_id in req.excluded_ids or track.track_id in used:
            return False
        fixed = req.fixed_positions.get(position)
        if fixed is not None and fixed != track.track_id:
            return False
        if req.allowed_modes and track.analysis.mode not in req.allowed_modes:
            return False
        if req.max_bpm_jump is not None and used:
            previous = self._last_track(used)
            if previous and previous.analysis.bpm and track.analysis.bpm:
                if abs(previous.analysis.bpm - track.analysis.bpm) > req.max_bpm_jump:
                    return False
        return True

    def _last_track(self, used: set[str]) -> PlaylistTrack | None:
        for track in reversed(self.tracks):
            if track.track_id in used:
                return track
        return None

    def reorder(
        self,
        requirements: PlaylistRequirements | None = None,
        start_track_id: str | None = None,
    ) -> list[str]:
        """Greedily build a valid flow, honoring hard requirements first."""
        req = requirements or PlaylistRequirements()
        by_id = {track.track_id: track for track in self.tracks}
        remaining = [track for track in self.tracks if track.track_id not in req.excluded_ids]
        if start_track_id and start_track_id in by_id:
            current = by_id[start_track_id]
            ordered = [current.track_id]
            used = {current.track_id}
        else:
            ordered = []
            used = set()
            current = None

        while len(ordered) < len(remaining):
            position = len(ordered)
            candidates = [
                t for t in remaining
                if self._allowed(t, used, position, req)
            ]
            if not candidates:
                # Never silently violate a hard constraint.
                raise ValueError(f"No valid next track at playlist position {position}")

            def score(candidate: PlaylistTrack) -> float:
                transition = 0.0 if current is None else self._compatibility(current.analysis, candidate.analysis)
                target = 0.0
                if req.target_bpm and candidate.analysis.bpm:
                    target = exp(-abs(candidate.analysis.bpm - req.target_bpm) / 15.0)
                if req.target_key and candidate.analysis.key:
                    target = max(target, 1.0 if candidate.analysis.key == req.target_key else 0.0)
                instrumental = candidate.analysis.instrumentalness or 0.0
                separation = 0.0
                if req.keep_artist_separation:
                    artist = getattr(candidate, "artist", None)
                    separation = 0.0 if artist else 1.0
                return (
                    transition
                    + 0.10 * target
                    + (0.05 * instrumental if req.prefer_instrumental else 0.0)
                    + separation
                )

            current = max(candidates, key=score)
            ordered.append(current.track_id)
            used.add(current.track_id)

        return ordered
