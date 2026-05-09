from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from talking_parrot.config.models import PipelineConfig
    from talking_parrot.models.media import MediaInfo


class AlignmentStatus(enum.Enum):
    DISABLED = "DISABLED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AlignmentGranularity(enum.Enum):
    WORD = "WORD"
    CHARACTER = "CHARACTER"


class GranularityPreference(enum.Enum):
    WORD = "WORD"
    CHARACTER = "CHARACTER"
    AUTO = "AUTO"


@dataclass(frozen=True)
class AlignmentResult:
    chunk_index: int
    tokens: list  # list[AlignedToken] — avoid circular import at module level


@dataclass(frozen=True)
class PipelineContext:
    """Frozen pipeline context threaded through every stage.

    The ``vad_frames`` field carries tagged per-backend frames plus a
    synthetic ``"composite"`` series produced by ``VADStage``. See the
    ``pipeline-data-models`` capability spec for the full contract.
    """

    config: "PipelineConfig"
    media_info: "MediaInfo"
    vad_frames: list = field(default_factory=list)
    vad_segments: list = field(default_factory=list)
    chunks: list = field(default_factory=list)
    transcription_results: list = field(default_factory=list)
    alignment_status: AlignmentStatus = AlignmentStatus.DISABLED
    alignment_granularity: AlignmentGranularity | None = None
    alignment_results: list = field(default_factory=list)
    subtitles: list = field(default_factory=list)
