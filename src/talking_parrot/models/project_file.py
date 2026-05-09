from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectFile:
    """On-disk pipeline DTO serialised by :class:`ProjectFileWriter`.

    The ``vad_frames`` field carries tagged ``RawVadFrame`` items (each with
    a ``backend: str`` tag) so the GUI can return real per-backend
    probability arrays. See the ``pipeline-data-models`` capability spec
    for the full contract.
    """

    version: str
    created_at: str
    media: Any
    config: Any
    vad_frames: list = field(default_factory=list)
    vad_segments: list = field(default_factory=list)
    transcription_results: list = field(default_factory=list)
    subtitles: list = field(default_factory=list)
