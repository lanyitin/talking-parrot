from dataclasses import dataclass


@dataclass(frozen=True)
class Subtitle:
    index: int
    start_ms: int
    end_ms: int
    text: str
