"""``ProjectSnapshot`` and ``AudioInfo`` value objects.

``ProjectSnapshot`` is the in-memory aggregate of every pipeline intermediate
consumed by regression, GUI, and MCP tooling. It is intentionally separate from
``ProjectFile`` (the on-disk serialisation DTO under ``models/``) so the on-disk
contract under the ``pipeline-data-models`` capability remains stable while the
in-memory view can carry richer fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from talking_parrot.models.chunk import Chunk
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import TranscriptionResult
from talking_parrot.models.vad import RawVadFrame, VadSegment

if TYPE_CHECKING:
    from talking_parrot.models.project_file import ProjectFile


@dataclass(frozen=True)
class AudioInfo:
    """Aggregate audio statistics carried by a ``ProjectSnapshot``."""

    sample_rate: int
    duration_ms: int
    rms_mean: float
    rms_peak: float


@dataclass(frozen=True)
class ProjectSnapshot:
    """Frozen in-memory aggregate of every pipeline intermediate.

    Downstream regression, GUI, and MCP code MUST depend on this aggregate
    rather than on ``ProjectFile`` or filesystem paths.

    The ``vad_frames`` list contains tagged ``RawVadFrame`` items: each
    frame carries a ``backend: str`` identifier that is one of
    ``"silero_vad"``, ``"ten_vad"``, ``"composite"`` (the synthetic series
    derived from the unified composite timeline emitted by ``VADStage``),
    or ``"unknown"`` (frames loaded from legacy ``.tp`` files that predate
    the per-backend change). Consumers SHOULD filter by ``backend`` when
    they need a per-backend timeline.
    """

    version: str
    created_at: str
    source_path: str
    config_snapshot: dict
    audio_info: AudioInfo
    vad_frames: list[RawVadFrame] = field(default_factory=list)
    vad_segments: list[VadSegment] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    transcription_results: list[TranscriptionResult] = field(default_factory=list)
    pre_postprocess_subtitles: list[Subtitle] = field(default_factory=list)
    subtitles: list[Subtitle] = field(default_factory=list)
    stage_timings: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_project_file(
        cls,
        project_file: ProjectFile,
        *,
        audio_info: AudioInfo,
        vad_frames: list[RawVadFrame] | None = None,
        chunks: list[Chunk] | None = None,
        pre_postprocess_subtitles: list[Subtitle] | None = None,
    ) -> ProjectSnapshot:
        """Bridge a ``ProjectFile`` (on-disk DTO) into a snapshot.

        Scalar fields and the ``vad_segments`` / ``transcription_results`` /
        ``subtitles`` lists are copied from ``project_file``. The richer fields
        not yet emitted by the writer (``vad_frames``, ``chunks``,
        ``pre_postprocess_subtitles``) come from keyword arguments and default
        to empty lists when omitted.
        """
        return cls(
            version=project_file.version,
            created_at=project_file.created_at,
            source_path="",
            config_snapshot=dict(project_file.config)
            if isinstance(project_file.config, dict)
            else {"raw": project_file.config},
            audio_info=audio_info,
            vad_frames=list(vad_frames) if vad_frames is not None else [],
            vad_segments=list(project_file.vad_segments),
            chunks=list(chunks) if chunks is not None else [],
            transcription_results=list(project_file.transcription_results),
            pre_postprocess_subtitles=list(pre_postprocess_subtitles)
            if pre_postprocess_subtitles is not None
            else [],
            subtitles=list(project_file.subtitles),
        )
