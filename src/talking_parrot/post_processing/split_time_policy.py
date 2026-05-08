"""Split-time policies used by the cue-split processors.

Spec: ``split-time-policy`` (change ``snap-split-timestamps-to-vad-silence``).

A :class:`SplitTimePolicy` is a structural type with a single method,
:meth:`SplitTimePolicy.adjust`, that the cue-split processors call after
computing a linearly-interpolated candidate timestamp.  Implementations
return the actual millisecond timestamp at which the cue should be sliced.

The default implementation, :class:`LinearSplitTimePolicy`, is a no-op
that returns the candidate unchanged — preserving the historical
linear-interpolation behaviour for non-VAD pipelines.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class SplitTimePolicy(Protocol):
    """Structural type for objects that adjust or pick a cue split timestamp."""

    def adjust(self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int) -> int:
        """Return the timestamp at which to slice the cue."""
        ...

    def pick(self, cue_start_ms: int, cue_end_ms: int) -> int | None:
        """Return the best silence midpoint strictly inside the cue, or ``None``."""
        ...


class LinearSplitTimePolicy:
    """No-op policy that returns the candidate timestamp unchanged."""

    def adjust(self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int) -> int:
        """Return ``candidate_ms`` verbatim, ignoring the cue bounds."""
        return candidate_ms

    def pick(self, cue_start_ms: int, cue_end_ms: int) -> int | None:
        """Always return ``None`` — no silence-driven cut available."""
        return None


class VadAlignedSplitTimePolicy:
    """Snap split timestamps to the nearest VAD silence midpoint."""

    def __init__(
        self,
        silences: Sequence[tuple[int, int]],
        search_radius_ms: int,
    ) -> None:
        """Capture silence intervals and the search radius.

        Args:
            silences: Sequence of ``(silence_start_ms, silence_end_ms)``
                half-open intervals representing pauses between speech.
                Copied internally so caller-side mutation is ignored.
            search_radius_ms: Non-negative half-width of the search window
                in milliseconds. ``0`` means snap only to a midpoint that
                exactly equals the candidate.

        Raises:
            ValueError: If ``search_radius_ms`` is negative.
        """
        if search_radius_ms < 0:
            raise ValueError(f"search_radius_ms ({search_radius_ms}) must be >= 0")
        self._silences: tuple[tuple[int, int], ...] = tuple(silences)
        self._radius_ms = search_radius_ms

    def adjust(self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int) -> int:
        """Snap ``candidate_ms`` to the nearest qualifying silence midpoint."""
        lo = candidate_ms - self._radius_ms
        hi = candidate_ms + self._radius_ms
        best_mid: int | None = None
        best_dist = -1
        for s_start, s_end in self._silences:
            mid = (s_start + s_end) // 2
            if not (lo <= mid <= hi):
                continue
            if not (cue_start_ms < mid < cue_end_ms):
                continue
            dist = abs(mid - candidate_ms)
            if (
                best_mid is None
                or dist < best_dist
                or (dist == best_dist and mid < best_mid)
            ):
                best_mid = mid
                best_dist = dist
        return candidate_ms if best_mid is None else best_mid

    def pick(self, cue_start_ms: int, cue_end_ms: int) -> int | None:
        """Return the silence midpoint nearest the cue's linear center, or ``None``.

        Selects from configured silences whose midpoint ``mid`` satisfies
        ``cue_start_ms < mid < cue_end_ms``. Ties on ``abs(mid - center_ms)``
        are broken by selecting the smaller ``mid``. Returns ``None`` when
        no qualifying silence exists.
        """
        center_ms = (cue_start_ms + cue_end_ms) // 2
        best_mid: int | None = None
        best_dist = -1
        for s_start, s_end in self._silences:
            mid = (s_start + s_end) // 2
            if not (cue_start_ms < mid < cue_end_ms):
                continue
            dist = abs(mid - center_ms)
            if (
                best_mid is None
                or dist < best_dist
                or (dist == best_dist and mid < best_mid)
            ):
                best_mid = mid
                best_dist = dist
        return best_mid
