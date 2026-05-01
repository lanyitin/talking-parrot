from __future__ import annotations

from dataclasses import dataclass, field

from talking_parrot.models.vad import VadSegment


@dataclass(frozen=True)
class Chunk:
    index: int
    start_ms: int
    end_ms: int
    source_segments: list[VadSegment] = field(default_factory=list)
