from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaInfo:
    """Metadata describing an input media file used throughout the pipeline."""

    path: Path
    duration_ms: int
    sha256: str
