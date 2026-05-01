from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionMetrics:
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float
    repetition_ratio: float


@dataclass(frozen=True)
class AlignedToken:
    word: str
    start_ms: int
    end_ms: int
    score: float


@dataclass(frozen=True)
class TranscriptionResult:
    chunk_index: int
    start_ms: int
    end_ms: int
    text: str
    language: str
    model_used: str
    metrics: TranscriptionMetrics
    aligned_tokens: list[AlignedToken] | None = None
