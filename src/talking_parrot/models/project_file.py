from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectFile:
    version: str
    created_at: str
    media: Any
    config: Any
    vad_segments: list = field(default_factory=list)
    transcription_results: list = field(default_factory=list)
    subtitles: list = field(default_factory=list)
