"""Shared fixtures for regression unit tests.

Provides factory helpers that construct minimal :class:`ProjectSnapshot`
and :class:`SampleDescriptor` instances without exercising real audio.
"""

from __future__ import annotations

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.shared import AudioInfo, ProjectSnapshot

from talking_parrot.regression import SampleDescriptor, SampleVariant


def make_snapshot(
    *,
    subtitles: list[Subtitle] | None = None,
    transcription_results: list[TranscriptionResult] | None = None,
) -> ProjectSnapshot:
    """Build a minimal :class:`ProjectSnapshot` for tests."""
    return ProjectSnapshot(
        version="1",
        created_at="2026-05-09T00:00:00Z",
        source_path="",
        config_snapshot={},
        audio_info=AudioInfo(
            sample_rate=16000, duration_ms=0, rms_mean=0.0, rms_peak=0.0
        ),
        vad_frames=[],
        vad_segments=[],
        chunks=[],
        transcription_results=transcription_results or [],
        pre_postprocess_subtitles=[],
        subtitles=subtitles or [],
    )


def make_descriptor(
    *,
    sample_id: str = "sample1",
    base_file: str = "base.mp3",
    reference_text: str = "hello",
    variants: tuple[SampleVariant, ...] = (),
) -> SampleDescriptor:
    """Build a :class:`SampleDescriptor` for tests."""
    return SampleDescriptor(
        sample_id=sample_id,
        base_file=base_file,
        reference_text=reference_text,
        variants=variants,
    )


def make_metrics(
    *,
    avg_logprob: float = -0.5,
    no_speech_prob: float = 0.05,
    repetition_ratio: float = 0.0,
) -> TranscriptionMetrics:
    """Build a :class:`TranscriptionMetrics` for tests."""
    return TranscriptionMetrics(
        avg_logprob=avg_logprob,
        compression_ratio=1.0,
        no_speech_prob=no_speech_prob,
        repetition_ratio=repetition_ratio,
    )


def make_result(
    *,
    chunk_index: int = 0,
    text: str = "hello",
    avg_logprob: float = -0.5,
    no_speech_prob: float = 0.05,
    repetition_ratio: float = 0.0,
) -> TranscriptionResult:
    """Build a :class:`TranscriptionResult` for tests."""
    return TranscriptionResult(
        chunk_index=chunk_index,
        start_ms=0,
        end_ms=1000,
        text=text,
        language="ja",
        model_used="test",
        metrics=make_metrics(
            avg_logprob=avg_logprob,
            no_speech_prob=no_speech_prob,
            repetition_ratio=repetition_ratio,
        ),
    )
