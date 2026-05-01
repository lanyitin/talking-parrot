from dataclasses import dataclass


@dataclass(frozen=True)
class VadSegment:
    start_ms: int
    end_ms: int
    confidence: float
