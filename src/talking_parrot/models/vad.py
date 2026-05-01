"""VAD (Voice Activity Detection) data models.

Provides immutable value objects for VAD pipeline stages:
- ``RawVadFrame``: per-frame speech probability from a single VAD backend.
- ``VadSegment``: a detected speech segment with per-backend and composite statistics.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RawVadFrame:
    """Immutable value object representing a single VAD frame from a backend.

    Attributes:
        time_ms: Start time of the frame in milliseconds (>= 0).
        prob: Speech probability in the range [0.0, 1.0].
    """

    time_ms: int
    prob: float


@dataclass(frozen=True)
class VadSegment:
    """An identified speech segment produced by VADStage.

    Attributes:
        start_ms: Segment start time in milliseconds.
        end_ms: Segment end time in milliseconds.
        ten_vad_prob: Mean TEN VAD probability across all frames in this segment.
        silero_vad_prob: Mean Silero VAD probability across all frames in this segment.
        composite_score: Mean composite score across all frames in this segment.
    """

    start_ms: int
    end_ms: int
    ten_vad_prob: float
    silero_vad_prob: float
    composite_score: float
