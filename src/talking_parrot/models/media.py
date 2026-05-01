from dataclasses import dataclass


@dataclass(frozen=True)
class MediaInfo:
    path: str
    duration_ms: int
    sha256: str
