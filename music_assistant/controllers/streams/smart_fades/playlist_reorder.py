"""Playlist intelligence for Smart Fades.

Ranks candidate next tracks by musical transition quality while enforcing hard
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
    artist_id: str | None = None


class SmartPlaylistReorder:
    """Heuristic optimizer for playlist flow.

    This is intentionally deterministic. Hard requirements are filtered first;
    the remaining choices are scored using transition quality plus optional
    user preferences. A one-step lookahead reduces greedy dead-ends.
    """

    def __init__(self, tracks: Iterable[PlaylistTrack]) -> None:
        self.tracks = tuple(tracks)
        self.by_id = {track.track_id: track for track in self.tracks}

    @staticmethod
    def _compatibility(a: AudioAnalysisData, b: AudioAnalysisData) -> float:
        """Return a 0..1 estimate of musical transition compatibility."""
        if not a.bpm or not b.bpm:
            bpm_score = 0.0
        else:
            bpm_score = exp(-abs(a.bpm - b.bpm) / 12.0)

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

        return 0.40 * bpm_score + 0.30 * key_score + 0.20 * energy_score + 0.10 * dance_score

    def _artist_ok(self, candidate: PlaylistTrack, ordered: list[PlaylistTrack], distance: int) -> bool:
        if not distance or not candidate.artist_id:
            return True
        return all(
            previous.artist_id != candidate.artist_id
            for previous in ordered[max(0, len(ordered) - distance):]
        )

    def _allowed(
        self,
        candidate: PlaylistTrack,
        ordered: list[PlaylistTrack],
        position: int,
        req: PlaylistRequirements,
    ) -> bool:
        if candidate.track_id in req.excluded_ids:
            return False
        fixed = req.fixed_positions.get(position)
        if fixed is not None and fixed != candidate.track_id:
            return False
        if req.allowed_modes and candidate.analysis.mode not in req.allowed_modes:
            return False
        if not self._artist_ok(candidate, ordered, req.keep_artist_separation):
            return False

        if ordered and req.max_bpm_jump is not None:
            previous = ordered[-1]
            if previous.analysis.bpm and candidate.analysis.bpm:
                if abs(previous.analysis.bpm - candidate.analysis.bpm) > req.max_bpm_jump:
                    return False
        return True

    def _score(
        self,
        previous: PlaylistTrack | None,
        candidate: PlaylistTrack,
        following: PlaylistTrack | None,
        req: PlaylistRequirements,
    ) -> float:
        weights = {
            "transition": 1.0,
            "bpm": 0.10,
            "key": 0.10,
            "energy": 0.05,
            "danceability": 0.05,
            **req.custom_weights,
        }

        transition = (
            self._compatibility(previous.analysis, candidate.analysis)
            if previous
            else 0.5
        )
        lookahead = (
            self._compatibility(candidate.analysis, following.analysis)
            if following
            else 0.0
        )

        score = weights["transition"] * transition + 0.25 * lookahead

        if req.target_bpm and candidate.analysis.bpm:
            score += weights["bpm"] * exp(
                -abs(candidate.analysis.bpm - req.target_bpm) / 15.0
            )
        if req.target_key and candidate.analysis.key:
            score += weights["key"] * (
                1.0 if candidate.analysis.key == req.target_key else 0.0
            )
        if req.prefer_instrumental:
            score += 0.05 * (candidate.analysis.instrumentalness or 0.0)

        return score

    def reorder(
        self,
        requirements: PlaylistRequirements | None = None,
        start_track_id: str | None = None,
    ) -> list[str]:
        """Build a valid flow; never silently violate a hard requirement."""
        req = requirements or PlaylistRequirements()
        excluded = set(req.excluded_ids)

        if not req.required_ids or all(track_id in self.by_id for track_id in req.required_ids):
            pass
        else:
            missing = [track_id for track_id in req.required_ids if track_id not in self.by_id]
            raise ValueError(f"Required track(s) not found: {', '.join(missing)}")

        if any(track_id in excluded for track_id in req.required_ids):
            raise ValueError("A required track is also excluded")

        for position, track_id in req.fixed_positions.items():
            if track_id not in self.by_id:
                raise ValueError(f"Fixed-position track not found: {track_id}")
            if track_id in excluded:
                raise ValueError(f"Fixed-position track is excluded: {track_id}")

        candidates = [t for t in self.tracks if t.track_id not in excluded]
        ordered: list[PlaylistTrack] = []
        remaining = {t.track_id: t for t in candidates}

        if start_track_id is not None:
            start = self.by_id.get(start_track_id)
            if start is None or start.track_id in excluded:
                raise ValueError("Invalid start track")
            if req.fixed_positions.get(0) not in (None, start.track_id):
                raise ValueError("Start track conflicts with fixed position 0")
            ordered.append(start)
            remaining.pop(start.track_id, None)

        while remaining:
            position = len(ordered)
            fixed_id = req.fixed_positions.get(position)

            if fixed_id is not None:
                candidate = remaining.get(fixed_id)
                if candidate is None:
                    raise ValueError(f"Fixed-position track unavailable at position {position}")
                if not self._allowed(candidate, ordered, position, req):
                    raise ValueError(f"Fixed-position track violates requirements at position {position}")
                ordered.append(candidate)
                remaining.pop(candidate.track_id)
                continue

            pool = [
                track for track in remaining.values()
                if self._allowed(track, ordered, position, req)
            ]
            if not pool:
                raise ValueError(f"No valid next track at playlist position {position}")

            def candidate_score(track: PlaylistTrack) -> float:
                alternatives = [
                    other for other in remaining.values()
                    if other.track_id != track.track_id
                    and self._allowed(other, ordered + [track], position + 1, req)
                ]
                following = max(
                    alternatives,
                    key=lambda item: self._compatibility(track.analysis, item.analysis),
                    default=None,
                )
                return self._score(
                    ordered[-1] if ordered else None,
                    track,
                    following,
                    req,
                )

            candidate = max(pool, key=candidate_score)
            ordered.append(candidate)
            remaining.pop(candidate.track_id)

        missing_required = set(req.required_ids) - {track.track_id for track in ordered}
        if missing_required:
            raise ValueError(
                "Required track(s) could not be placed: " + ", ".join(sorted(missing_required))
            )

        return [track.track_id for track in ordered]
