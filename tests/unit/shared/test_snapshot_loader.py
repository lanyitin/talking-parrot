"""Tests for ``SnapshotLoader`` protocol and ``FileSnapshotLoader``."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from talking_parrot.shared.project_snapshot import AudioInfo, ProjectSnapshot
from talking_parrot.shared.snapshot_loader import FileSnapshotLoader, SnapshotLoader


def _well_formed_payload() -> dict:
    return {
        "version": "1",
        "created_at": "2026-05-09T00:00:00Z",
        "source_path": "/tmp/sample.tp",
        "config_snapshot": {"sample_rate": 16000},
        "audio_info": {
            "sample_rate": 16000,
            "duration_ms": 10000,
            "rms_mean": 0.1,
            "rms_peak": 0.5,
        },
        "vad_frames": [],
        "vad_segments": [],
        "chunks": [],
        "transcription_results": [],
        "pre_postprocess_subtitles": [],
        "subtitles": [],
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "sample.tp"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_duck_typed_loader_satisfies_protocol() -> None:
    class Stub:
        def load(self, source: str | Path) -> ProjectSnapshot:  # noqa: ARG002
            raise NotImplementedError

    assert isinstance(Stub(), SnapshotLoader)


def test_load_well_formed_file(tmp_path: Path) -> None:
    p = _write(tmp_path, _well_formed_payload())

    snap = FileSnapshotLoader().load(p)

    assert isinstance(snap, ProjectSnapshot)
    assert snap.version == "1"
    assert snap.created_at == "2026-05-09T00:00:00Z"
    assert snap.source_path == "/tmp/sample.tp"
    assert snap.config_snapshot == {"sample_rate": 16000}
    assert snap.audio_info == AudioInfo(
        sample_rate=16000, duration_ms=10000, rms_mean=0.1, rms_peak=0.5
    )


def test_missing_list_defaults_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    payload = _well_formed_payload()
    del payload["vad_frames"]
    p = _write(tmp_path, payload)

    with caplog.at_level(logging.DEBUG, logger="talking_parrot.shared.snapshot_loader"):
        snap = FileSnapshotLoader().load(p)

    assert snap.vad_frames == []
    assert any("vad_frames" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize(
    "missing_field",
    ["version", "created_at", "source_path", "config_snapshot", "audio_info"],
)
def test_missing_required_raises_keyerror(tmp_path: Path, missing_field: str) -> None:
    payload = _well_formed_payload()
    del payload[missing_field]
    p = _write(tmp_path, payload)

    with pytest.raises(KeyError) as exc:
        FileSnapshotLoader().load(p)

    assert missing_field in str(exc.value)


def test_missing_file_raises_filenotfound(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        FileSnapshotLoader().load(tmp_path / "does-not-exist.tp")


def test_malformed_json_raises_decodeerror(tmp_path: Path) -> None:
    p = tmp_path / "broken.tp"
    p.write_text("{not json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        FileSnapshotLoader().load(p)


# ---------------------------------------------------------------------------
# vad-frames-per-backend — legacy backend tag fallback
# ---------------------------------------------------------------------------


_LEGACY_WARNING_FRAGMENT = "legacy vad_frames without 'backend' tag"


def test_legacy_vad_frames_default_backend_unknown(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Legacy ``.tp`` files without ``backend`` keys load with ``"unknown"`` tag."""
    payload = _well_formed_payload()
    payload["vad_frames"] = [
        {"time_ms": 0, "prob": 0.1},
        {"time_ms": 16, "prob": 0.2},
    ]
    p = _write(tmp_path, payload)

    with caplog.at_level(
        logging.WARNING, logger="talking_parrot.shared.snapshot_loader"
    ):
        snap = FileSnapshotLoader().load(p)

    assert len(snap.vad_frames) == 2
    assert all(frame.backend == "unknown" for frame in snap.vad_frames)
    legacy_warnings = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and _LEGACY_WARNING_FRAGMENT in r.getMessage()
    ]
    assert len(legacy_warnings) == 1
    msg = legacy_warnings[0].getMessage()
    assert str(p) in msg
    assert _LEGACY_WARNING_FRAGMENT in msg


def test_modern_vad_frames_no_legacy_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Modern files (with ``backend`` keys) MUST NOT emit the legacy warning."""
    payload = _well_formed_payload()
    payload["vad_frames"] = [
        {"time_ms": 0, "prob": 0.1, "backend": "silero_vad"},
        {"time_ms": 16, "prob": 0.2, "backend": "ten_vad"},
    ]
    p = _write(tmp_path, payload)

    with caplog.at_level(
        logging.WARNING, logger="talking_parrot.shared.snapshot_loader"
    ):
        snap = FileSnapshotLoader().load(p)

    assert snap.vad_frames[0].backend == "silero_vad"
    assert snap.vad_frames[1].backend == "ten_vad"
    legacy_warnings = [
        r for r in caplog.records if _LEGACY_WARNING_FRAGMENT in r.getMessage()
    ]
    assert legacy_warnings == []


def test_mixed_vad_frames_emit_one_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A file with mixed legacy + modern frames emits exactly one warning."""
    payload = _well_formed_payload()
    payload["vad_frames"] = [
        {"time_ms": 0, "prob": 0.1, "backend": "silero_vad"},
        {"time_ms": 16, "prob": 0.2},
        {"time_ms": 32, "prob": 0.3},
        {"time_ms": 48, "prob": 0.4, "backend": "ten_vad"},
        {"time_ms": 64, "prob": 0.5},
    ]
    p = _write(tmp_path, payload)

    with caplog.at_level(
        logging.WARNING, logger="talking_parrot.shared.snapshot_loader"
    ):
        snap = FileSnapshotLoader().load(p)

    backends = [frame.backend for frame in snap.vad_frames]
    assert backends == ["silero_vad", "unknown", "unknown", "ten_vad", "unknown"]
    legacy_warnings = [
        r for r in caplog.records if _LEGACY_WARNING_FRAGMENT in r.getMessage()
    ]
    assert len(legacy_warnings) == 1
