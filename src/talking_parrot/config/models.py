from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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
    backend: Optional[str] = None
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
        dedup_enabled: Toggle for the segment-level deduplication sub-stage.
        dedup_similarity_threshold: Similarity ratio in the closed interval
            ``[0.0, 1.0]`` above which two adjacent segments are considered
            near-duplicates and eligible for deduplication.
        dedup_max_gap_ms: Maximum inter-segment gap (in milliseconds, must be
            ``>= 0``) within which two near-duplicate segments may be merged
            by the dedup sub-stage.
        japanese_filler_enabled: Toggle for the Japanese filler-word stripping
            sub-stage.
        japanese_repetition_enabled: Toggle for the Japanese intra-segment
            repetition collapsing sub-stage.
        japanese_filler_words: List of Japanese filler tokens to strip when
            ``japanese_filler_enabled`` is true.
        japanese_onomatopoeia_whitelist: Onomatopoeia tokens that are exempt
            from the Japanese repetition collapsing rule.
        japanese_split_search_radius: Half-width (in characters) of the
            window the Japanese split-boundary policy searches around the
            linearly-interpolated candidate index. Must be in ``[0, 20]``.
        japanese_split_no_split_units: Configured multi-character units
            (typically Japanese auxiliaries) that the policy refuses to cut
            through.
        japanese_split_no_leading_particles: Particles that may not appear
            as the first character of a post-split cue (would orphan them).
        japanese_split_no_leading_finals: Sentence-final / inflection
            characters that may not appear as the first character of a
            post-split cue when preceded by hiragana / kanji.
        split_time_snap_radius_ms: Search radius (in milliseconds) used by
            ``VadAlignedSplitTimePolicy`` when nudging split-cue timestamps
            toward the nearest VAD silence midpoint. Must be in
            ``[0, 2000]``. ``0`` disables snapping (factory selects
            ``LinearSplitTimePolicy``).
        vad_grammar_search_radius: Half-width (in characters) of the
            window used by ``CharacterBoundarySplitProcessor`` when
            snapping a VAD-derived ``char_idx`` to the nearest
            grammar-valid boundary (sanity-gate sub-path 3b in
            ``character-boundary-processors``; see ADR-0004). Must be
            ``>= 0``.
    """

    model_config = {"extra": "forbid"}

    enabled: bool = True
    max_line_length: int = 42
    max_lines_per_subtitle: int = 2
    merge_gap_threshold_ms: int = 200
    merge_max_duration_ms: int = 6000
    split_max_duration_ms: int = 6000
    dedup_enabled: bool = True
    dedup_similarity_threshold: float = 0.9
    dedup_max_gap_ms: int = 600
    japanese_filler_enabled: bool = True
    japanese_repetition_enabled: bool = True
    japanese_filler_words: list[str] = Field(
        default_factory=lambda: [
            "あのー",
            "えーと",
            "えー",
            "そのー",
        ]
    )
    japanese_onomatopoeia_whitelist: list[str] = Field(
        default_factory=lambda: [
            "どきどき",
            "わくわく",
            "きらきら",
            "ぴかぴか",
        ]
    )
    japanese_split_search_radius: int = 4
    japanese_split_no_split_units: list[str] = Field(
        default_factory=lambda: [
            "ます",
            "ません",
            "まし",
            "です",
            "でし",
            "だっ",
            "った",
            "ない",
            "なかっ",
            "たい",
            "よう",
            "そう",
            "という",
            "について",
        ]
    )
    japanese_split_no_leading_particles: list[str] = Field(
        default_factory=lambda: [
            "て",
            "で",
            "に",
            "を",
            "が",
            "は",
            "も",
            "と",
            "から",
            "まで",
            "より",
            "へ",
            "や",
            "か",
            "の",
            "ね",
            "よ",
        ]
    )
    japanese_split_no_leading_finals: list[str] = Field(
        default_factory=lambda: ["た", "だ", "る", "い"]
    )
    split_time_snap_radius_ms: int = 250
    vad_grammar_search_radius: int = 2

    @field_validator("vad_grammar_search_radius")
    @classmethod
    def _vad_grammar_search_radius_non_negative(cls, v: int) -> int:
        """Validate that ``vad_grammar_search_radius`` is non-negative."""
        if v < 0:
            raise ValueError(f"vad_grammar_search_radius ({v}) must be >= 0")
        return v

    @field_validator("split_time_snap_radius_ms")
    @classmethod
    def _split_time_snap_radius_ms_in_range(cls, v: int) -> int:
        """Validate that ``split_time_snap_radius_ms`` lies in ``[0, 2000]``."""
        if not (0 <= v <= 2000):
            raise ValueError(
                f"split_time_snap_radius_ms ({v}) must be in the closed "
                "interval [0, 2000]"
            )
        return v

    @field_validator("japanese_split_search_radius")
    @classmethod
    def _japanese_split_search_radius_in_range(cls, v: int) -> int:
        """Validate that ``japanese_split_search_radius`` lies in ``[0, 20]``."""
        if not (0 <= v <= 20):
            raise ValueError(
                f"japanese_split_search_radius ({v}) must be in the closed "
                "interval [0, 20]"
            )
        return v

    @field_validator(
        "japanese_split_no_split_units",
        "japanese_split_no_leading_particles",
        "japanese_split_no_leading_finals",
    )
    @classmethod
    def _japanese_split_lists_no_empty_entries(cls, v: list[str]) -> list[str]:
        """Reject empty-string entries in any Japanese split list."""
        if any(not entry for entry in v):
            raise ValueError(
                "japanese_split_* lists must not contain empty-string entries"
            )
        return v

    @field_validator("dedup_similarity_threshold")
    @classmethod
    def _dedup_similarity_threshold_in_unit_interval(cls, v: float) -> float:
        """Validate that ``dedup_similarity_threshold`` lies in ``[0.0, 1.0]``."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"dedup_similarity_threshold ({v}) must be in the closed "
                "interval [0.0, 1.0]"
            )
        return v

    @field_validator("dedup_max_gap_ms")
    @classmethod
    def _dedup_max_gap_ms_non_negative(cls, v: int) -> int:
        """Validate that ``dedup_max_gap_ms`` is in ``[0, 60_000]`` ms.

        Lower bound guards against negative gaps. Upper bound guards
        against typos like ``600000`` (10 min) where the operator likely
        meant ``600`` ms — without a cap, the dedup stage would merge
        cues across huge silences.
        """
        if v < 0:
            raise ValueError(f"dedup_max_gap_ms ({v}) must be >= 0")
        if v > 60_000:
            raise ValueError(f"dedup_max_gap_ms must be <= 60000 (1 minute); got {v}")
        return v

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


class HallucinationFilterConfig(BaseModel):
    """Configuration for the hallucination-filter post-processing stage.

    Attributes:
        enabled: Whether the hallucination-filter stage is active.
        min_avg_logprob: Segments whose ``avg_logprob`` falls below this threshold
            are flagged by the low-logprob rule.
        max_no_speech_prob: Segments whose ``no_speech_prob`` exceeds this threshold
            are flagged by the no-speech rule.
        max_compression_ratio: Segments whose ``compression_ratio`` exceeds this
            threshold are flagged by the compression rule.
        max_repetition_ratio: Segments whose intra-segment repetition ratio exceeds
            this threshold are flagged by the repetition rule.
        known_hallucination_phrases: Exact-match phrases known to be Whisper
            hallucinations. Default list copied from the audio2subtitle reference;
            project allows override via YAML.
        phrase_match_enabled: Toggle for the known-phrase exact-match rule.
        bracket_match_enabled: Toggle for the bracket-content rule.
        repeat_match_enabled: Toggle for the cross-segment repeat rule.
        low_logprob_match_enabled: Toggle for the low-logprob rule.
        compression_match_enabled: Toggle for the compression-ratio rule.
        repetition_match_enabled: Toggle for the intra-segment repetition rule.
    """

    model_config = {"extra": "forbid"}

    enabled: bool = True
    min_avg_logprob: float = -1.0
    max_no_speech_prob: float = 0.6
    max_compression_ratio: float = 2.4
    max_repetition_ratio: float = 0.5
    known_hallucination_phrases: list[str] = Field(
        default_factory=lambda: [
            "ご視聴ありがとうございました",
            "ご視聴ありがとうございます",
            "おやすみなさい",
        ]
    )
    phrase_match_enabled: bool = True
    bracket_match_enabled: bool = True
    repeat_match_enabled: bool = True
    low_logprob_match_enabled: bool = True
    compression_match_enabled: bool = True
    repetition_match_enabled: bool = True

    @field_validator("known_hallucination_phrases")
    @classmethod
    def _strip_and_drop_empty_phrases(cls, v: list[str]) -> list[str]:
        """Strip surrounding whitespace and drop empty/whitespace-only entries.

        Empty entries in the phrase list are almost always config typos and
        would cause the phrase rule to flag any cue whose text strips to
        empty. Silently filter them out rather than raising — a stray empty
        string in a long phrase list shouldn't blow up the whole load.
        """
        return [stripped for entry in v if (stripped := entry.strip())]

    @model_validator(mode="after")
    def _validate_at_least_one_rule_when_enabled(
        self,
    ) -> "HallucinationFilterConfig":
        """Reject ``enabled=True`` while every per-rule toggle is False.

        Such a configuration produces a stage that emits "filter ran" logs
        but drops nothing — a silent no-op. The user almost certainly meant
        either to disable the stage entirely (``enabled=False``) or to
        leave at least one rule on.
        """
        if self.enabled and not (
            self.phrase_match_enabled
            or self.bracket_match_enabled
            or self.repeat_match_enabled
            or self.low_logprob_match_enabled
            or self.compression_match_enabled
            or self.repetition_match_enabled
        ):
            raise ValueError(
                "HallucinationFilterConfig.enabled is True but all six "
                "per-rule toggles are False — at least one of "
                "phrase_match_enabled / bracket_match_enabled / "
                "repeat_match_enabled / low_logprob_match_enabled / "
                "compression_match_enabled / repetition_match_enabled "
                "must be True (or set enabled=False to disable the stage "
                "entirely)."
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
    hallucination_filter: Optional[HallucinationFilterConfig] = None
    export: Optional[ExportConfig] = None

    @field_validator("transcribing")
    @classmethod
    def transcribing_must_be_non_empty(
        cls, v: list[TranscribingStep]
    ) -> list[TranscribingStep]:
        if not v:
            raise ValueError("transcribing must be a non-empty list")
        return v

    @field_validator("expected_language")
    @classmethod
    def _normalise_expected_language(cls, v: Optional[str]) -> Optional[str]:
        """Normalise to canonical lowercase BCP-47 base tag.

        - ``None`` passes through unchanged.
        - Surrounding whitespace is stripped.
        - The value is lowercased.
        - Only the part before the first ``-`` is kept (e.g. ``ja-JP`` ->
          ``ja``).

        Whole-word strings like ``japanese`` are NOT mapped to ``ja``;
        callers MUST use BCP-47 base tags. The normalisation here is
        idempotent — re-validating an already-normalised value is a no-op.
        """
        if v is None:
            return None
        return v.strip().lower().split("-", 1)[0]
