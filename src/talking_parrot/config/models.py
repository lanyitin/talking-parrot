from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class VadConfig(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = True
    activity_threshold: float = 0.5
    min_speech_duration_ms: int = 250
    max_speech_duration_ms: int = 30000
    min_silence_duration_ms: int = 100
    speech_pad_ms: int = 30


class ChunkingConfig(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = True
    max_chunk_seconds: int = 30
    overlap_ms: int = 200


class TranscribingStep(BaseModel):
    model_config = {"extra": "forbid"}

    condition: str
    backend: str
    model: str = "base"
    language: Optional[str] = None


class AlignConfig(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = True
    granularity: str = "AUTO"


class PostProcessingConfig(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = True
    max_line_length: int = 42
    max_lines_per_subtitle: int = 2


class PipelineConfig(BaseModel):
    model_config = {"extra": "forbid"}

    expected_language: Optional[str] = None
    vad: Optional[VadConfig] = None
    chunking: Optional[ChunkingConfig] = None
    transcribing: list[TranscribingStep]
    align: Optional[AlignConfig] = None
    post_processing: Optional[PostProcessingConfig] = None

    @field_validator("transcribing")
    @classmethod
    def transcribing_must_be_non_empty(
        cls, v: list[TranscribingStep]
    ) -> list[TranscribingStep]:
        if not v:
            raise ValueError("transcribing must be a non-empty list")
        return v
