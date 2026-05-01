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
    config: "PipelineConfig"
    media_info: "MediaInfo"
    vad_segments: list = field(default_factory=list)
    chunks: list = field(default_factory=list)
    transcription_results: list = field(default_factory=list)
    alignment_status: AlignmentStatus = AlignmentStatus.DISABLED
    alignment_granularity: AlignmentGranularity | None = None
    alignment_results: list = field(default_factory=list)
    subtitles: list = field(default_factory=list)
