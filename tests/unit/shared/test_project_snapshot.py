"""Tests for ``ProjectSnapshot`` and ``AudioInfo``."""

from __future__ import annotations

import dataclasses

import pytest

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.models.vad import VadSegment
from talking_parrot.shared.project_snapshot import AudioInfo, ProjectSnapshot


def _audio_info() -> AudioInfo:
    return AudioInfo(sample_rate=16000, duration_ms=10000, rms_mean=0.1, rms_peak=0.5)


def _snapshot(**overrides: object) -> ProjectSnapshot:
    base: dict[str, object] = {
        "version": "1",
        "created_at": "2026-05-09T00:00:00Z",
        "source_path": "/tmp/sample.tp",
        "config_snapshot": {},
        "audio_info": _audio_info(),
    }
    base.update(overrides)
    return ProjectSnapshot(**base)  # type: ignore[arg-type]


def test_audio_info_is_frozen() -> None:
    info = _audio_info()
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.sample_rate = 8000  # type: ignore[misc]


def test_default_lists_empty() -> None:
    snap = _snapshot()
    assert snap.vad_frames == []
    assert snap.vad_segments == []
    assert snap.chunks == []
    assert snap.transcription_results == []
    assert snap.pre_postprocess_subtitles == []
    assert snap.subtitles == []


def test_snapshot_is_frozen() -> None:
    snap = _snapshot()
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.subtitles = []  # type: ignore[misc]


def test_subtitle_type_identity() -> None:
    sub = Subtitle(index=0, start_ms=0, end_ms=1000, text="hi")
    snap = _snapshot(subtitles=[sub])
    assert isinstance(snap.subtitles[0], Subtitle)


def _make_transcription_result(idx: int) -> TranscriptionResult:
    return TranscriptionResult(
        chunk_index=idx,
        start_ms=idx * 1000,
        end_ms=(idx + 1) * 1000,
        text=f"text-{idx}",
        language="en",
        model_used="dummy",
        metrics=TranscriptionMetrics(
            avg_logprob=-0.1,
            compression_ratio=1.0,
            no_speech_prob=0.0,
            repetition_ratio=0.0,
        ),
    )


def test_from_project_file_round_trip() -> None:
    from talking_parrot.models.project_file import ProjectFile

    results = [_make_transcription_result(i) for i in range(3)]
    vad_seg = VadSegment(
        start_ms=0,
        end_ms=1000,
        ten_vad_prob=0.9,
        silero_vad_prob=0.8,
        composite_score=0.85,
    )
    pf = ProjectFile(
        version="1",
        created_at="2026-05-09T00:00:00Z",
        media={},
        config={"k": "v"},
        vad_segments=[vad_seg],
        transcription_results=results,
        subtitles=[Subtitle(index=0, start_ms=0, end_ms=1000, text="hi")],
    )

    snap = ProjectSnapshot.from_project_file(pf, audio_info=_audio_info())

    assert snap.transcription_results == results
    assert snap.vad_segments == [vad_seg]
    assert len(snap.subtitles) == 1
    assert snap.vad_frames == []
    assert snap.chunks == []
    assert snap.pre_postprocess_subtitles == []
    assert snap.config_snapshot == {"k": "v"}
    assert snap.version == "1"
    assert snap.created_at == "2026-05-09T00:00:00Z"
