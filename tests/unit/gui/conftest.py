"""Shared fixtures for the gui unit tests.

Provides ``make_snapshot`` which builds a fully-populated ``ProjectSnapshot``
backed by temporary audio/video files on disk.
"""

from __future__ import annotations

import struct
import wave
from collections.abc import Callable
from pathlib import Path

import pytest

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import (
    AlignedToken,
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.models.vad import RawVadFrame, VadSegment
from talking_parrot.shared import AudioInfo, ProjectSnapshot


def _write_silent_wav(path: Path, sample_rate: int, duration_ms: int) -> None:
    """Write a silent 16-bit PCM mono WAV file at ``path``."""
    n_frames = int(sample_rate * duration_ms / 1000)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        if n_frames:
            # Write a small repeating ramp so waveform peaks are non-zero.
            samples = [(i % 4096) - 2048 for i in range(n_frames)]
            wf.writeframes(struct.pack(f"<{n_frames}h", *samples))


@pytest.fixture
def make_snapshot(tmp_path: Path) -> Callable[..., ProjectSnapshot]:
    """Return a builder yielding a fully populated ``ProjectSnapshot``."""

    def _factory(
        *,
        sample_rate: int = 16000,
        duration_ms: int = 5000,
        source_suffix: str = ".wav",
        with_video: bool = False,
        n_subtitles: int = 3,
        vad_frames: list[RawVadFrame] | None = None,
    ) -> ProjectSnapshot:
        if source_suffix == ".wav":
            audio_path = tmp_path / "source.wav"
            _write_silent_wav(audio_path, sample_rate, duration_ms)
            source_path = audio_path
        elif with_video:
            source_path = tmp_path / f"source{source_suffix}"
            source_path.write_bytes(b"\x00" * 4096)
        else:
            source_path = tmp_path / f"source{source_suffix}"
            source_path.write_bytes(b"\x00" * 1024)

        audio_info = AudioInfo(
            sample_rate=sample_rate,
            duration_ms=duration_ms,
            rms_mean=0.1,
            rms_peak=0.5,
        )
        if vad_frames is None:
            # Default: tag every fixture frame as "composite" so the GUI
            # endpoint sees them as part of the composite timeline (the
            # only series the legacy zero-fill could populate). Tests that
            # need real per-backend coverage SHOULD pass ``vad_frames=``
            # explicitly with concrete tags.
            vad_frames = [
                RawVadFrame(time_ms=t, prob=0.7, backend="composite")
                for t in range(0, duration_ms, 100)
            ]
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
        subtitles = [
            Subtitle(
                index=i,
                start_ms=i * 1000,
                end_ms=(i + 1) * 1000,
                text=f"line {i}",
            )
            for i in range(n_subtitles)
        ]
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
        return ProjectSnapshot(
            version="1.0",
            created_at="2026-05-09T00:00:00Z",
            source_path=str(source_path),
            config_snapshot={"sample_rate": sample_rate},
            audio_info=audio_info,
            vad_frames=vad_frames,
            vad_segments=vad_segments,
            chunks=[],
            transcription_results=transcription_results,
            pre_postprocess_subtitles=[],
            subtitles=subtitles,
        )

    return _factory


@pytest.fixture(autouse=True)
def _reset_flagged_regions() -> None:
    """Ensure each gui test starts with an empty flagged-region list."""
    from talking_parrot.gui import http_server

    http_server._set_flagged_regions([])
    yield
    http_server._set_flagged_regions([])
