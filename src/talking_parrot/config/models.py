from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class VadConfig(BaseModel):
    """Configuration for the VAD (Voice Activity Detection) stage.

    Attributes:
        enabled: Whether the VAD stage is active.
        activity_threshold: Score at or above which a frame is considered speech onset.
        neg_threshold: Score below which an active speech segment ends (hysteresis).
        min_speech_duration_ms: Segments shorter than this are discarded after merging.
        max_speech_duration_ms: Segments longer than this are split at the midpoint.
        min_silence_duration_ms: Silent gaps shorter than this cause adjacent segments to merge.
        speech_pad_ms: Milliseconds added before and after each segment (clamped to audio bounds).
        formula: Arithmetic formula used by FormulaEvaluator to compute the composite VAD score.
            Variable names follow the pattern ``{backend_name}_prob`` (e.g. ``ten_vad_prob``).
    """

    model_config = {"extra": "forbid"}

    enabled: bool = True
    activity_threshold: float = 0.5
    neg_threshold: float = 0.35
    min_speech_duration_ms: int = 250
    max_speech_duration_ms: int = 30000
    min_silence_duration_ms: int = 100
    speech_pad_ms: int = 30
    formula: str = "(ten_vad_prob + silero_vad_prob) / 2"


class ChunkingConfig(BaseModel):
    """Configuration for the chunking stage.

    Attributes:
        enabled: Whether the chunking stage is active.
        max_chunk_seconds: Maximum duration in seconds for a single chunk.
        overlap_ms: Overlap in milliseconds between adjacent chunks.
        silence_pad_ms: Milliseconds of silence added around each chunk boundary.
            Must be non-negative.
    """

    model_config = {"extra": "forbid"}

    enabled: bool = True
    max_chunk_seconds: int = 30
    overlap_ms: int = 200
    silence_pad_ms: int = 50

    @field_validator("silence_pad_ms")
    @classmethod
    def silence_pad_ms_must_be_non_negative(cls, v: int) -> int:
        """Validate that silence_pad_ms is not negative."""
        if v < 0:
            raise ValueError("silence_pad_ms must be non-negative")
        return v


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
    """Configuration for the post-processing stage.

    Attributes:
        enabled: Whether the post-processing stage is active.
        max_line_length: Maximum number of characters per subtitle line
            (interpreted as Python ``len()``).
        max_lines_per_subtitle: Maximum number of lines per subtitle cue.
        merge_gap_threshold_ms: Two adjacent cues whose inter-cue gap is at most
            this many milliseconds are eligible for merging.
        merge_max_duration_ms: A merged cue's total duration MUST NOT exceed
            this many milliseconds. Per ADR-0003 / D7, this MUST be less than or
            equal to ``split_max_duration_ms`` so that Merge cannot produce a
            cue that Split would then need to break apart.
        split_max_duration_ms: A cue whose duration exceeds this many
            milliseconds is split into multiple cues.
    """

    model_config = {"extra": "forbid"}

    enabled: bool = True
    max_line_length: int = 42
    max_lines_per_subtitle: int = 2
    merge_gap_threshold_ms: int = 200
    merge_max_duration_ms: int = 6000
    split_max_duration_ms: int = 6000

    @model_validator(mode="after")
    def _validate_merge_le_split(self) -> "PostProcessingConfig":
        """Enforce ``merge_max_duration_ms <= split_max_duration_ms`` (D7)."""
        if self.merge_max_duration_ms > self.split_max_duration_ms:
            raise ValueError(
                "merge_max_duration_ms "
                f"({self.merge_max_duration_ms}) must be <= "
                f"split_max_duration_ms ({self.split_max_duration_ms})"
            )
        return self


class ExportConfig(BaseModel):
    """Configuration for the subtitle-export step (Stage 6).

    Attributes:
        format: Subtitle format identifier — must be ``"srt"`` or ``"webvtt"``.
        output_path: Filesystem path where the subtitle file SHALL be written.
            Must be non-empty after ``strip()``.
    """

    model_config = {"extra": "forbid"}

    format: Literal["srt", "webvtt"]
    output_path: str

    @field_validator("output_path")
    @classmethod
    def output_path_must_be_non_empty(cls, v: str) -> str:
        """Reject empty or whitespace-only ``output_path`` values."""
        if not v.strip():
            raise ValueError("output_path must be non-empty")
        return v


class PipelineConfig(BaseModel):
    model_config = {"extra": "forbid"}

    expected_language: Optional[str] = None
    vad: Optional[VadConfig] = None
    chunking: Optional[ChunkingConfig] = None
    transcribing: list[TranscribingStep]
    align: Optional[AlignConfig] = None
    post_processing: Optional[PostProcessingConfig] = None
    export: Optional[ExportConfig] = None

    @field_validator("transcribing")
    @classmethod
    def transcribing_must_be_non_empty(
        cls, v: list[TranscribingStep]
    ) -> list[TranscribingStep]:
        if not v:
            raise ValueError("transcribing must be a non-empty list")
        return v
