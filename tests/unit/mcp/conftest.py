"""Shared fixtures for ``tests/unit/mcp``.

Exposes a ``make_snapshot`` factory that yields a fully populated
:class:`ProjectSnapshot` purely from in-memory dataclasses — no FastMCP
import, no filesystem audio files. The MCP unit tests target the pure
helpers in :mod:`talking_parrot.mcp.server`, which depend on
:class:`ProjectSnapshot` only (DIP).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import (
    AlignedToken,
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.models.vad import RawVadFrame, VadSegment
from talking_parrot.shared import AudioInfo, ProjectSnapshot


@pytest.fixture
def make_snapshot() -> Callable[..., ProjectSnapshot]:
    """Return a builder that yields a fully populated :class:`ProjectSnapshot`.

    Defaults produce a 5-second snapshot with three subtitles, three
    transcription results (one per chunk), two VAD segments, and a
    composite VAD frame every 100 ms. Tests override individual fields
    via keyword arguments to express the scenario under test.
    """

    def _factory(
        *,
        sample_rate: int = 16000,
        duration_ms: int = 5000,
        n_subtitles: int = 3,
        vad_segments: list[VadSegment] | None = None,
        vad_frames: list[RawVadFrame] | None = None,
        subtitles: list[Subtitle] | None = None,
        pre_postprocess_subtitles: list[Subtitle] | None = None,
        transcription_results: list[TranscriptionResult] | None = None,
        config_snapshot: dict | None = None,
    ) -> ProjectSnapshot:
        audio_info = AudioInfo(
            sample_rate=sample_rate,
            duration_ms=duration_ms,
            rms_mean=0.1,
            rms_peak=0.5,
        )

        if vad_frames is None:
            vad_frames = [
                RawVadFrame(time_ms=t, prob=0.7, backend="composite")
                for t in range(0, duration_ms, 100)
            ]
        if vad_segments is None:
            vad_segments = [
                VadSegment(
                    start_ms=500,
                    end_ms=1500,
                    ten_vad_prob=0.8,
                    silero_vad_prob=0.7,
                    composite_score=0.75,
                ),
                VadSegment(
                    start_ms=2000,
                    end_ms=3000,
                    ten_vad_prob=0.9,
                    silero_vad_prob=0.85,
                    composite_score=0.87,
                ),
            ]
        if subtitles is None:
            subtitles = [
                Subtitle(
                    index=i,
                    start_ms=i * 1000,
                    end_ms=(i + 1) * 1000,
                    text=f"line {i}",
                )
                for i in range(n_subtitles)
            ]
        if pre_postprocess_subtitles is None:
            pre_postprocess_subtitles = []
        if transcription_results is None:
            transcription_results = [
                TranscriptionResult(
                    chunk_index=i,
                    start_ms=i * 1000,
                    end_ms=(i + 1) * 1000,
                    text=f"line {i}",
                    language="en",
                    model_used="test",
                    metrics=TranscriptionMetrics(
                        avg_logprob=-0.3,
                        compression_ratio=1.2,
                        no_speech_prob=0.05,
                        repetition_ratio=0.0,
                    ),
                    aligned_tokens=[
                        AlignedToken(
                            word=f"word{i}",
                            start_ms=float(i * 1000 + 100),
                            end_ms=float(i * 1000 + 500),
                            score=0.9,
                        )
                    ],
                )
                for i in range(n_subtitles)
            ]
        if config_snapshot is None:
            config_snapshot = {"sample_rate": sample_rate}

        return ProjectSnapshot(
            version="1.0",
            created_at="2026-05-09T00:00:00Z",
            source_path="",
            config_snapshot=config_snapshot,
            audio_info=audio_info,
            vad_frames=vad_frames,
            vad_segments=vad_segments,
            chunks=[],
            transcription_results=transcription_results,
            pre_postprocess_subtitles=pre_postprocess_subtitles,
            subtitles=subtitles,
        )

    return _factory


@pytest.fixture(autouse=True)
def _reset_mcp_snapshot_binding() -> None:
    """Ensure each MCP test starts with no installed snapshot binding.

    The server holds the binding at module level on purpose; to keep tests
    independent we reset the binding before and after every test.
    """
    from talking_parrot.mcp import server as mcp_server

    mcp_server._reset_snapshot_for_tests()
    yield
    mcp_server._reset_snapshot_for_tests()
