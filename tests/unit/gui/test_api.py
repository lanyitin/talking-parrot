"""Unit tests for ``talking_parrot.gui.api``."""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from talking_parrot.gui import api as gui_api
from talking_parrot.gui import http_server
from talking_parrot.shared import ProjectSnapshot


# ---------------------------------------------------------------------------
# Module-level invariants
# ---------------------------------------------------------------------------


def test_api_response_frozen() -> None:
    """``ApiResponse`` is a frozen dataclass."""
    response = gui_api.ApiResponse(
        status=200, content_type="text/plain", body=b"", headers={}
    )
    assert dataclasses.is_dataclass(response)
    with pytest.raises(dataclasses.FrozenInstanceError):
        response.status = 500  # type: ignore[misc]


def test_api_module_lists_numpy_followup() -> None:
    """The api.py top-of-file comment must name numpy as the future swap."""
    source = Path(gui_api.__file__).read_text(encoding="utf-8")
    # Inspect only the leading module docstring + comment block.
    head_text = "\n".join(source.splitlines()[:60]).lower()
    assert "numpy" in head_text
    assert "downsampl" in head_text


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def test_dispatch_unknown_route(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch("GET", "/api/does_not_exist", {}, snap, None)
    assert response.status == 404


def test_dispatch_method_not_allowed(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch("DELETE", "/api/summary", {}, snap, None)
    assert response.status == 405


# ---------------------------------------------------------------------------
# /api/summary
# ---------------------------------------------------------------------------


def test_summary_returns_audio_info_keys(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot(sample_rate=16000, duration_ms=42000)
    response = gui_api.dispatch("GET", "/api/summary", {}, snap, None)
    assert response.status == 200
    body = json.loads(response.body)
    assert body["sample_rate"] == 16000
    assert body["duration_ms"] == 42000
    assert "quality_distribution" in body
    assert {"accepted", "low_confidence"} <= set(body["quality_distribution"])


def test_summary_keys_are_snake_case(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch("GET", "/api/summary", {}, snap, None)
    body = json.loads(response.body)
    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for key in body.keys():
        assert pattern.match(key), f"non snake_case top-level key: {key!r}"
        for forbidden in ("tbd", "todo", "tktk"):
            assert forbidden not in key


# ---------------------------------------------------------------------------
# /api/waveform
# ---------------------------------------------------------------------------


def test_waveform_length_matches_width(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch(
        "GET",
        "/api/waveform",
        {"start_ms": "0", "end_ms": "1000", "width": "200"},
        snap,
        None,
    )
    assert response.status == 200
    body = json.loads(response.body)
    assert isinstance(body, list)
    assert len(body) == 200
    for entry in body:
        assert "peak_pos" in entry and "peak_neg" in entry


def test_waveform_rejects_missing_width(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch(
        "GET",
        "/api/waveform",
        {"start_ms": "0", "end_ms": "1000"},
        snap,
        None,
    )
    assert response.status == 400


def test_waveform_rejects_oversized_width(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch(
        "GET",
        "/api/waveform",
        {"start_ms": "0", "end_ms": "1000", "width": "9000"},
        snap,
        None,
    )
    assert response.status == 400


# ---------------------------------------------------------------------------
# /api/vad_probs
# ---------------------------------------------------------------------------


def test_vad_probs_filters_by_interval(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Frames at 500/1500/2500 ms with [1000, 2000) keep only 1500 ms."""
    from talking_parrot.models.vad import RawVadFrame

    snap = make_snapshot()
    snap = dataclasses.replace(
        snap,
        vad_frames=[
            RawVadFrame(time_ms=500, prob=0.1, backend="composite"),
            RawVadFrame(time_ms=1500, prob=0.5, backend="composite"),
            RawVadFrame(time_ms=2500, prob=0.9, backend="composite"),
        ],
    )
    response = gui_api.dispatch(
        "GET",
        "/api/vad_probs",
        {"start_ms": "1000", "end_ms": "2000"},
        snap,
        None,
    )
    assert response.status == 200
    body = json.loads(response.body)
    assert body["times_ms"] == [1500]


def test_vad_probs_returns_real_per_backend_arrays(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Tagged frames for silero/ten/composite produce three non-zero arrays."""
    from talking_parrot.models.vad import RawVadFrame

    snap = make_snapshot()
    snap = dataclasses.replace(
        snap,
        vad_frames=[
            RawVadFrame(time_ms=1000, prob=0.85, backend="silero_vad"),
            RawVadFrame(time_ms=1000, prob=0.9, backend="ten_vad"),
            RawVadFrame(time_ms=1000, prob=0.875, backend="composite"),
            RawVadFrame(time_ms=2000, prob=0.75, backend="silero_vad"),
            RawVadFrame(time_ms=2000, prob=0.8, backend="ten_vad"),
            RawVadFrame(time_ms=2000, prob=0.775, backend="composite"),
        ],
    )
    response = gui_api.dispatch(
        "GET",
        "/api/vad_probs",
        {"start_ms": "0", "end_ms": "5000"},
        snap,
        None,
    )
    assert response.status == 200
    body = json.loads(response.body)
    assert body["times_ms"] == [1000, 2000]
    assert body["silero"] == [pytest.approx(0.85), pytest.approx(0.75)]
    assert body["ten_vad"] == [pytest.approx(0.9), pytest.approx(0.8)]
    assert body["composite"] == [pytest.approx(0.875), pytest.approx(0.775)]


def test_vad_probs_ignores_unknown_backend_frames(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """Frames with ``backend="unknown"`` MUST NOT appear in any column."""
    from talking_parrot.models.vad import RawVadFrame

    snap = make_snapshot()
    snap = dataclasses.replace(
        snap,
        vad_frames=[
            RawVadFrame(time_ms=1000, prob=0.42, backend="unknown"),
            RawVadFrame(time_ms=2000, prob=0.99, backend="unknown"),
        ],
    )
    response = gui_api.dispatch(
        "GET",
        "/api/vad_probs",
        {"start_ms": "0", "end_ms": "5000"},
        snap,
        None,
    )
    assert response.status == 200
    body = json.loads(response.body)
    # No recognised-backend frames in range → empty unified axis.
    assert body["times_ms"] == []
    assert body["silero"] == []
    assert body["ten_vad"] == []
    assert body["composite"] == []


def test_vad_probs_arrays_equal_length(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch(
        "GET",
        "/api/vad_probs",
        {"start_ms": "0", "end_ms": "5000"},
        snap,
        None,
    )
    body = json.loads(response.body)
    n = len(body["times_ms"])
    assert n > 0
    assert n == len(body["silero"]) == len(body["ten_vad"]) == len(body["composite"])


# ---------------------------------------------------------------------------
# /api/vad_segments
# ---------------------------------------------------------------------------


def test_vad_segments_overlap_filter(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    from talking_parrot.models.vad import VadSegment

    snap = make_snapshot()
    snap = dataclasses.replace(
        snap,
        vad_segments=[
            VadSegment(
                start_ms=1500,
                end_ms=2500,
                ten_vad_prob=0.5,
                silero_vad_prob=0.5,
                composite_score=0.5,
            )
        ],
    )
    response = gui_api.dispatch(
        "GET",
        "/api/vad_segments",
        {"start_ms": "1000", "end_ms": "2000"},
        snap,
        None,
    )
    body = json.loads(response.body)
    assert len(body) == 1
    assert body[0]["start_ms"] == 1500
    assert body[0]["end_ms"] == 2500


# ---------------------------------------------------------------------------
# /api/subtitles
# ---------------------------------------------------------------------------


def test_subtitles_preserve_index(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot(n_subtitles=3)
    response = gui_api.dispatch(
        "GET",
        "/api/subtitles",
        {"start_ms": "0", "end_ms": "10000"},
        snap,
        None,
    )
    body = json.loads(response.body)
    assert [entry["index"] for entry in body] == [0, 1, 2]


# ---------------------------------------------------------------------------
# /api/subtitle_tokens
# ---------------------------------------------------------------------------


def test_subtitle_tokens_index_required(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch("GET", "/api/subtitle_tokens", {}, snap, None)
    assert response.status == 400


def test_subtitle_tokens_out_of_range(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot(n_subtitles=2)
    response = gui_api.dispatch(
        "GET", "/api/subtitle_tokens", {"index": "99"}, snap, None
    )
    assert response.status == 404


# ---------------------------------------------------------------------------
# /api/video_info
# ---------------------------------------------------------------------------


def test_video_info_mkv_not_browser_playable(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot(source_suffix=".mkv", with_video=True)
    response = gui_api.dispatch("GET", "/api/video_info", {}, snap, None)
    assert response.status == 200
    body = json.loads(response.body)
    assert body["is_video"] is True
    assert body["browser_playable"] is False


# ---------------------------------------------------------------------------
# /api/audio
# ---------------------------------------------------------------------------


def test_audio_response_starts_with_riff_header(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch(
        "GET",
        "/api/audio",
        {"start_ms": "0", "end_ms": "1000"},
        snap,
        None,
    )
    assert response.status == 200
    assert response.content_type == "audio/wav"
    assert response.body.startswith(b"RIFF")


def test_audio_404_when_source_missing(
    make_snapshot: Callable[..., ProjectSnapshot], tmp_path: Path
) -> None:
    snap = make_snapshot()
    snap = dataclasses.replace(snap, source_path=str(tmp_path / "missing.wav"))
    response = gui_api.dispatch(
        "GET",
        "/api/audio",
        {"start_ms": "0", "end_ms": "1000"},
        snap,
        None,
    )
    assert response.status == 404


# ---------------------------------------------------------------------------
# Flagged regions endpoints
# ---------------------------------------------------------------------------


def test_flagged_regions_empty_status(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch("GET", "/api/flagged_regions", {}, snap, None)
    body = json.loads(response.body)
    assert body == {"status": "empty", "regions": []}


def test_flagged_regions_after_post(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    payload = json.dumps(
        {"regions": [{"start_ms": 100, "end_ms": 200, "label": "x"}]}
    ).encode("utf-8")
    post = gui_api.dispatch("POST", "/api/flagged_regions", {}, snap, payload)
    assert post.status == 200
    get = gui_api.dispatch("GET", "/api/flagged_regions", {}, snap, None)
    body = json.loads(get.body)
    assert body["status"] == "ok"
    assert body["regions"] == [{"start_ms": 100, "end_ms": 200, "label": "x"}]


def test_post_flagged_regions_rejects_malformed_json(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    response = gui_api.dispatch("POST", "/api/flagged_regions", {}, snap, b"not-json")
    assert response.status == 400


def test_post_flagged_regions_replaces_atomically(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    first = json.dumps(
        {
            "regions": [
                {"start_ms": 0, "end_ms": 100, "label": "a"},
                {"start_ms": 100, "end_ms": 200, "label": "b"},
                {"start_ms": 200, "end_ms": 300, "label": "c"},
            ]
        }
    ).encode("utf-8")
    second = json.dumps(
        {
            "regions": [
                {"start_ms": 500, "end_ms": 600, "label": "z"},
                {"start_ms": 600, "end_ms": 700, "label": "y"},
            ]
        }
    ).encode("utf-8")
    gui_api.dispatch("POST", "/api/flagged_regions", {}, snap, first)
    gui_api.dispatch("POST", "/api/flagged_regions", {}, snap, second)
    response = gui_api.dispatch("GET", "/api/flagged_regions", {}, snap, None)
    body = json.loads(response.body)
    assert len(body["regions"]) == 2
    assert body["regions"][0]["label"] == "z"


def test_post_empty_list_clears_regions(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    populated = json.dumps(
        {"regions": [{"start_ms": 0, "end_ms": 100, "label": "a"}]}
    ).encode("utf-8")
    gui_api.dispatch("POST", "/api/flagged_regions", {}, snap, populated)
    cleared = b'{"regions": []}'
    gui_api.dispatch("POST", "/api/flagged_regions", {}, snap, cleared)
    assert http_server.get_flagged_regions() == ()
    body = json.loads(
        gui_api.dispatch("GET", "/api/flagged_regions", {}, snap, None).body
    )
    assert body["status"] == "empty"


# ---------------------------------------------------------------------------
# Fixture sanity
# ---------------------------------------------------------------------------


def test_fixture_builder_produces_valid_snapshot(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    assert isinstance(snap, ProjectSnapshot)
    assert snap.audio_info.sample_rate > 0
    assert snap.audio_info.duration_ms > 0
    assert Path(snap.source_path).exists()
