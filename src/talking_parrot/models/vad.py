"""VAD (Voice Activity Detection) data models.

Provides immutable value objects for VAD pipeline stages:
- ``RawVadFrame``: per-frame speech probability tagged with the producing
  backend's identifier. Real backends use their ``VADBackend.name`` value
  (e.g., ``"silero_vad"``, ``"ten_vad"``); the unified composite timeline
  emitted by ``VADStage`` uses the literal string ``"composite"``; legacy
  ``.tp`` files loaded without a ``backend`` field are tagged ``"unknown"``
  by the snapshot loader.
- ``VadSegment``: a detected speech segment with per-backend and composite
  statistics.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RawVadFrame:
    """Immutable value object representing a single VAD frame from a backend.

    Attributes:
        time_ms: Start time of the frame in milliseconds (>= 0).
        prob: Speech probability in the range [0.0, 1.0].
        backend: Identifier of the producing backend. For real backends this
            equals the backend's ``name`` attribute (e.g., ``"silero_vad"``,
            ``"ten_vad"``). The literal string ``"composite"`` is reserved
            for the unified composite timeline emitted by ``VADStage``. The
            literal string ``"unknown"`` is reserved for frames loaded from
            legacy ``.tp`` files that predate this field. MUST be a
            non-empty string.
    """

    time_ms: int
    prob: float
    backend: str

    def __post_init__(self) -> None:
        """Validate that ``backend`` is a non-empty string."""
        if not self.backend:
            raise ValueError(
                "RawVadFrame.backend must be a non-empty string (got empty string)."
            )


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
