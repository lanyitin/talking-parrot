"""Pure-function endpoint dispatcher for the GUI backend.

Per the ``Endpoint Routing`` Architectural Decision in the gui-backend design,
this module defines:

- ``ApiResponse``: frozen dataclass envelope returned by every endpoint.
- ``dispatch``: flat ``(method, path)`` router that delegates to one private
  function per endpoint (ISP).

Every endpoint function takes only the snapshot, the parsed query mapping,
and (for POST) the request body bytes — no network I/O, no snapshot mutation.
The ``Forbidden weasel words excluded from JSON keys`` requirement is honored
by using snake_case keys exclusively in every payload below.

# Waveform downsampling complexity follow-up
#
# The pure-Python ``_endpoint_waveform`` handler walks the requested PCM slice
# in O(N) where N = (end_ms - start_ms) * sample_rate / 1000, computing per-bin
# min/max in a single pass. For a 60-minute, 16 kHz recording rendered at
# width=8192 this is ~57.6M samples per request and may dominate latency.
#
# A future change MAY promote ``numpy`` (already declared in the ``[align]``
# extra) to a base dependency for ``talking_parrot.gui`` so the downsampler can
# vectorise via ``numpy.frombuffer`` + ``reshape`` + ``min/max`` along axis 1.
# That promotion requires explicit user approval per CLAUDE.md.
#
# /api/vad_probs returns true per-backend arrays (vad-frames-per-backend
# change): the previous zero-fill workaround for ``silero`` and ``ten_vad``
# has been removed now that ``ProjectSnapshot.vad_frames`` carries each
# frame's ``backend`` tag. ``_endpoint_vad_probs`` groups frames by tag and
# nearest-neighbour-fills each backend column with a 50 ms tolerance window
# matching ``VADStage._align_frames``.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import re
import struct
import wave
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from talking_parrot.shared import ProjectSnapshot

_logger = logging.getLogger("talking_parrot.gui.api")

_BROWSER_PLAYABLE_VIDEO_MIMES = frozenset({"video/mp4", "video/webm", "video/ogg"})

_VIDEO_SUFFIXES = frozenset(
    {".mp4", ".m4v", ".mov", ".webm", ".ogg", ".ogv", ".mkv", ".avi"}
)

_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_FORBIDDEN_KEY_SUBSTRINGS = ("tbd", "todo", "tktk")

# Mirror of ``VADStage._align_frames`` tolerance. If that constant changes,
# this one MUST be revisited in lockstep so per-backend nearest-neighbour
# alignment in the GUI stays consistent with the pipeline.
_ALIGN_TOLERANCE_MS = 50

# Backends recognised by ``/api/vad_probs``. Frames whose ``backend`` is not
# one of these (e.g., ``"unknown"`` from legacy files) are silently dropped.
_VAD_PROBS_BACKENDS = ("silero_vad", "ten_vad", "composite")


@dataclass(frozen=True, slots=True)
class ApiResponse:
    """Envelope returned by every endpoint function and the dispatcher."""

    status: int
    content_type: str
    body: bytes
    headers: dict[str, str]


def dispatch(
    method: str,
    path: str,
    query: Mapping[str, str],
    snapshot: ProjectSnapshot,
    body: bytes | None,
) -> ApiResponse:
    """Route an HTTP request to the matching pure-function endpoint.

    Returns an :class:`ApiResponse`. ``404`` for unknown paths,
    ``405`` for known paths invoked with the wrong method.
    """
    if path == "/api/summary":
        if method == "GET":
            return _endpoint_summary(snapshot, query)
        return _method_not_allowed()
    if path == "/api/waveform":
        if method == "GET":
            return _endpoint_waveform(snapshot, query)
        return _method_not_allowed()
    if path == "/api/vad_probs":
        if method == "GET":
            return _endpoint_vad_probs(snapshot, query)
        return _method_not_allowed()
    if path == "/api/vad_segments":
        if method == "GET":
            return _endpoint_vad_segments(snapshot, query)
        return _method_not_allowed()
    if path == "/api/subtitles":
        if method == "GET":
            return _endpoint_subtitles(snapshot, query)
        return _method_not_allowed()
    if path == "/api/subtitle_tokens":
        if method == "GET":
            return _endpoint_subtitle_tokens(snapshot, query)
        return _method_not_allowed()
    if path == "/api/video_info":
        if method == "GET":
            return _endpoint_video_info(snapshot, query)
        return _method_not_allowed()
    if path == "/api/audio":
        if method == "GET":
            return _endpoint_audio(snapshot, query)
        return _method_not_allowed()
    if path == "/api/flagged_regions":
        if method == "GET":
            return _endpoint_get_flagged_regions(snapshot, query)
        if method == "POST":
            return _endpoint_post_flagged_regions(snapshot, query, body)
        return _method_not_allowed()
    return _not_found()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(status: int, payload: Any) -> ApiResponse:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return ApiResponse(
        status=status,
        content_type="application/json; charset=utf-8",
        body=body,
        headers={},
    )


def _error(status: int, message: str) -> ApiResponse:
    return _json_response(status, {"error": message})


def _not_found() -> ApiResponse:
    return _error(404, "not found")


def _method_not_allowed() -> ApiResponse:
    return _error(405, "method not allowed")


def _parse_int(query: Mapping[str, str], key: str) -> int | None:
    raw = query.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _endpoint_summary(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """Return aggregate scalars + quality distribution + hotspots."""
    audio = snapshot.audio_info
    accepted = 0
    low_confidence = 0
    detected_language: str | None = None
    for tr in snapshot.transcription_results:
        if tr.metrics.no_speech_prob < 0.5 and tr.metrics.avg_logprob > -1.0:
            accepted += 1
        else:
            low_confidence += 1
        if detected_language is None and tr.language:
            detected_language = tr.language

    hotspots: list[dict[str, Any]] = []
    for tr in snapshot.transcription_results:
        if tr.metrics.no_speech_prob >= 0.5:
            hotspots.append(
                {
                    "time_ms": int(tr.start_ms),
                    "type": "high_no_speech",
                    "text": tr.text or None,
                }
            )

    payload = {
        "duration_ms": int(audio.duration_ms),
        "sample_rate": int(audio.sample_rate),
        "rms_mean": float(audio.rms_mean),
        "rms_peak": float(audio.rms_peak),
        "subtitle_count": len(snapshot.subtitles),
        "quality_distribution": {
            "accepted": accepted,
            "low_confidence": low_confidence,
        },
        "detected_language": detected_language,
        "hotspots": hotspots,
    }
    _assert_keys_clean(payload)
    return _json_response(200, payload)


def _assert_keys_clean(payload: Mapping[str, Any]) -> None:
    """Defensive guard that response keys obey the snake_case + weasel rule."""
    for key in payload.keys():
        assert _SNAKE_CASE_RE.match(key), f"non snake_case key {key!r}"
        for forbidden in _FORBIDDEN_KEY_SUBSTRINGS:
            assert forbidden not in key, f"forbidden substring {forbidden!r} in {key!r}"


def _endpoint_waveform(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """Pure-Python min/max downsample of the requested PCM interval."""
    start_ms = _parse_int(query, "start_ms")
    end_ms = _parse_int(query, "end_ms")
    width = _parse_int(query, "width")
    if start_ms is None or end_ms is None or width is None:
        return _error(400, "missing or non-integer query parameter")
    if start_ms < 0 or end_ms <= start_ms:
        return _error(400, "invalid interval")
    if width < 1 or width > 8192:
        return _error(400, "width out of range")

    duration_ms = snapshot.audio_info.duration_ms
    if duration_ms <= 0 or start_ms >= duration_ms:
        return _error(404, "interval outside audio")

    # Even when the source file is unavailable, we honour the contract by
    # producing a flat waveform so the SPA renders zeros rather than 500ing.
    samples = _read_pcm_slice(snapshot, start_ms, end_ms)
    bins: list[dict[str, float]] = []
    if not samples:
        bins = [{"peak_pos": 0.0, "peak_neg": 0.0} for _ in range(width)]
    else:
        n = len(samples)
        for i in range(width):
            lo = (i * n) // width
            hi = ((i + 1) * n) // width
            if hi <= lo:
                hi = lo + 1
            window = samples[lo:hi]
            if not window:
                bins.append({"peak_pos": 0.0, "peak_neg": 0.0})
                continue
            peak_pos = max(window)
            peak_neg = min(window)
            bins.append(
                {
                    "peak_pos": float(peak_pos) / 32768.0,
                    "peak_neg": float(peak_neg) / 32768.0,
                }
            )
    return _json_response(200, bins)


def _read_pcm_slice(snapshot: ProjectSnapshot, start_ms: int, end_ms: int) -> list[int]:
    """Read a 16-bit mono PCM slice from ``snapshot.source_path``.

    Returns an empty list if the file is missing or not a WAV — the waveform
    handler treats that as "render zeros" rather than failing.
    """
    path = Path(snapshot.source_path) if snapshot.source_path else None
    if path is None or not path.exists() or path.suffix.lower() != ".wav":
        return []
    sample_rate = snapshot.audio_info.sample_rate
    start_frame = (start_ms * sample_rate) // 1000
    end_frame = (end_ms * sample_rate) // 1000
    n_frames = max(0, end_frame - start_frame)
    if n_frames <= 0:
        return []
    _logger.debug("calling wave.open path=%s mode=rb", path)
    try:
        with wave.open(str(path), "rb") as wf:
            assert isinstance(wf, wave.Wave_read), (
                "wave.open did not return Wave_read; check stdlib wave API"
            )
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            assert isinstance(channels, int), "wave.getnchannels not int"
            assert isinstance(sampwidth, int), "wave.getsampwidth not int"
            wf.setpos(min(start_frame, wf.getnframes()))
            raw = wf.readframes(n_frames)
            assert isinstance(raw, bytes), "wave.readframes did not return bytes"
    except (wave.Error, OSError) as exc:
        _logger.debug("wave.open failed: %r", exc)
        return []
    if sampwidth != 2:
        return []
    count = len(raw) // 2
    if count == 0:
        return []
    samples = list(struct.unpack(f"<{count}h", raw))
    if channels > 1:
        samples = samples[::channels]
    return samples


def _endpoint_vad_probs(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """Return per-backend VAD probability arrays over ``[start_ms, end_ms)``.

    Frames are bucketed by ``frame.backend`` and aligned onto the union of
    all in-range timestamps using nearest-neighbour fill within
    ``_ALIGN_TOLERANCE_MS``. Frames whose backend is not in
    ``_VAD_PROBS_BACKENDS`` (e.g., ``"unknown"`` from legacy ``.tp`` files)
    are dropped from the response.
    """
    start_ms = _parse_int(query, "start_ms")
    end_ms = _parse_int(query, "end_ms")
    downsample_raw = query.get("downsample")
    downsample = 1
    if downsample_raw is not None:
        try:
            downsample = int(downsample_raw)
        except ValueError:
            return _error(400, "downsample must be int")
        if downsample < 1 or downsample > 64:
            return _error(400, "downsample out of range")
    if start_ms is None or end_ms is None:
        return _error(400, "missing or non-integer query parameter")
    if start_ms < 0 or end_ms <= start_ms:
        return _error(400, "invalid interval")

    # Bucket frames by backend, keeping only those in the requested
    # interval and whose backend is recognised.
    buckets: dict[str, list[tuple[int, float]]] = {b: [] for b in _VAD_PROBS_BACKENDS}
    for frame in snapshot.vad_frames:
        if frame.backend not in buckets:
            continue
        if start_ms <= frame.time_ms < end_ms:
            buckets[frame.backend].append((int(frame.time_ms), float(frame.prob)))

    # Build the unified time axis: union of every recognised backend's
    # in-range timestamps, sorted ascending.
    unified_times: set[int] = set()
    for entries in buckets.values():
        for t, _prob in entries:
            unified_times.add(t)
    times = sorted(unified_times)

    silero = _nearest_neighbour_fill(times, buckets["silero_vad"])
    ten = _nearest_neighbour_fill(times, buckets["ten_vad"])
    composite = _nearest_neighbour_fill(times, buckets["composite"])

    if downsample > 1:
        times = times[::downsample]
        silero = silero[::downsample]
        ten = ten[::downsample]
        composite = composite[::downsample]

    payload = {
        "times_ms": times,
        "silero": silero,
        "ten_vad": ten,
        "composite": composite,
    }
    return _json_response(200, payload)


def _nearest_neighbour_fill(
    target_times: list[int], frames: list[tuple[int, float]]
) -> list[float]:
    """Nearest-neighbour-fill ``target_times`` from ``frames``.

    For each entry in ``target_times``, return the ``prob`` of the closest
    frame whose ``|time - target| <= _ALIGN_TOLERANCE_MS``. If no frame
    falls within tolerance (or ``frames`` is empty), the position is
    filled with ``0.0``. This mirrors ``VADStage._align_frames``.
    """
    if not frames:
        return [0.0 for _ in target_times]
    out: list[float] = []
    for t in target_times:
        best: tuple[int, float] | None = None
        best_delta: int = _ALIGN_TOLERANCE_MS + 1
        for frame_t, prob in frames:
            delta = abs(frame_t - t)
            if delta <= _ALIGN_TOLERANCE_MS and delta < best_delta:
                best_delta = delta
                best = (frame_t, prob)
        out.append(best[1] if best is not None else 0.0)
    return out


def _endpoint_vad_segments(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """Return ``VadSegment`` entries overlapping ``[start_ms, end_ms)``."""
    start_ms = _parse_int(query, "start_ms")
    end_ms = _parse_int(query, "end_ms")
    if start_ms is None or end_ms is None:
        return _error(400, "missing or non-integer query parameter")
    if start_ms < 0 or end_ms <= start_ms:
        return _error(400, "invalid interval")
    out: list[dict[str, Any]] = []
    for seg in snapshot.vad_segments:
        if seg.start_ms < end_ms and seg.end_ms > start_ms:
            out.append(
                {
                    "start_ms": int(seg.start_ms),
                    "end_ms": int(seg.end_ms),
                    "composite_score": float(seg.composite_score),
                }
            )
    return _json_response(200, out)


def _quality_status(no_speech_prob: float, avg_logprob: float) -> str:
    if no_speech_prob >= 0.5 or avg_logprob <= -1.0:
        return "low_confidence"
    return "accepted"


def _lookup_metrics(
    snapshot: ProjectSnapshot, start_ms: int, end_ms: int
) -> tuple[float, float]:
    """Return (avg_logprob, no_speech_prob) from any overlapping transcription."""
    for tr in snapshot.transcription_results:
        if tr.start_ms < end_ms and tr.end_ms > start_ms:
            return (
                float(tr.metrics.avg_logprob),
                float(tr.metrics.no_speech_prob),
            )
    return (0.0, 0.0)


def _endpoint_subtitles(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """Return subtitles overlapping ``[start_ms, end_ms)`` preserving snapshot index."""
    start_ms = _parse_int(query, "start_ms")
    end_ms = _parse_int(query, "end_ms")
    if start_ms is None or end_ms is None:
        return _error(400, "missing or non-integer query parameter")
    if start_ms < 0 or end_ms <= start_ms:
        return _error(400, "invalid interval")
    out: list[dict[str, Any]] = []
    for idx, sub in enumerate(snapshot.subtitles):
        if sub.start_ms < end_ms and sub.end_ms > start_ms:
            avg_logprob, no_speech_prob = _lookup_metrics(
                snapshot, sub.start_ms, sub.end_ms
            )
            out.append(
                {
                    "index": idx,
                    "start_ms": int(sub.start_ms),
                    "end_ms": int(sub.end_ms),
                    "text": sub.text,
                    "avg_logprob": avg_logprob,
                    "no_speech_prob": no_speech_prob,
                    "quality_status": _quality_status(no_speech_prob, avg_logprob),
                }
            )
    return _json_response(200, out)


def _endpoint_subtitle_tokens(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """Return a single subtitle plus its aligned tokens (or 404)."""
    if "index" not in query:
        return _error(400, "index is required")
    index = _parse_int(query, "index")
    if index is None or index < 0:
        return _error(400, "index must be a non-negative integer")
    if index >= len(snapshot.subtitles):
        return _error(404, "subtitle index out of range")

    sub = snapshot.subtitles[index]
    avg_logprob, no_speech_prob = _lookup_metrics(snapshot, sub.start_ms, sub.end_ms)
    tokens: list[dict[str, Any]] = []
    for tr in snapshot.transcription_results:
        if tr.aligned_tokens and tr.start_ms < sub.end_ms and tr.end_ms > sub.start_ms:
            for tok in tr.aligned_tokens:
                if tok.start_ms < sub.end_ms and tok.end_ms > sub.start_ms:
                    tokens.append(
                        {
                            "word": tok.word,
                            "start_ms": float(tok.start_ms),
                            "end_ms": float(tok.end_ms),
                            "score": float(tok.score),
                        }
                    )
    payload = {
        "subtitle": {
            "index": index,
            "start_ms": int(sub.start_ms),
            "end_ms": int(sub.end_ms),
            "text": sub.text,
            "avg_logprob": avg_logprob,
            "no_speech_prob": no_speech_prob,
        },
        "tokens": tokens,
    }
    return _json_response(200, payload)


def _endpoint_video_info(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """Report whether the source file is a video and whether browsers can play it."""
    source = snapshot.source_path or ""
    suffix = Path(source).suffix.lower() if source else ""
    is_video = suffix in _VIDEO_SUFFIXES
    _logger.debug("calling mimetypes.guess_type path=%r", source)
    mime_guess, _enc = mimetypes.guess_type(source) if source else (None, None)
    assert mime_guess is None or isinstance(mime_guess, str), (
        "mimetypes.guess_type returned non-str mime — stdlib API may have changed"
    )
    mime_type = mime_guess or (
        "application/octet-stream" if not is_video else "video/x-unknown"
    )
    container = suffix.lstrip(".") if suffix else None
    browser_playable = is_video and (mime_type in _BROWSER_PLAYABLE_VIDEO_MIMES)
    payload = {
        "is_video": bool(is_video),
        "container": container,
        "browser_playable": bool(browser_playable),
        "mime_type": mime_type,
        "duration_ms": int(snapshot.audio_info.duration_ms),
    }
    return _json_response(200, payload)


def _endpoint_audio(snapshot: ProjectSnapshot, query: Mapping[str, str]) -> ApiResponse:
    """Assemble a 16-bit PCM mono WAV slice via stdlib ``wave``."""
    start_ms = _parse_int(query, "start_ms")
    end_ms = _parse_int(query, "end_ms")
    if start_ms is None or end_ms is None:
        return _error(400, "missing or non-integer query parameter")
    if start_ms < 0 or end_ms <= start_ms:
        return _error(400, "invalid interval")
    if not snapshot.source_path or not Path(snapshot.source_path).exists():
        return _error(404, "source audio missing")
    samples = _read_pcm_slice(snapshot, start_ms, end_ms)
    sample_rate = snapshot.audio_info.sample_rate
    body = _encode_wav(samples, sample_rate)
    return ApiResponse(
        status=200,
        content_type="audio/wav",
        body=body,
        headers={},
    )


def _encode_wav(samples: list[int], sample_rate: int) -> bytes:
    """Encode a list of 16-bit PCM samples as an in-memory WAV file."""
    import io

    buf = io.BytesIO()
    _logger.debug("calling wave.open mode=wb sample_rate=%d", sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        if samples:
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        else:
            wf.writeframes(b"")
    out = buf.getvalue()
    assert isinstance(out, bytes), "wave.open(BytesIO) did not produce bytes"
    assert out.startswith(b"RIFF"), "encoded WAV does not begin with RIFF header"
    return out


# ---------------------------------------------------------------------------
# Flagged regions
# ---------------------------------------------------------------------------


def _endpoint_get_flagged_regions(
    snapshot: ProjectSnapshot, query: Mapping[str, str]
) -> ApiResponse:
    """GET handler — read via the http_server module's accessor."""
    from talking_parrot.gui import http_server

    regions = http_server.get_flagged_regions()
    payload = {
        "status": "ok" if regions else "empty",
        "regions": [
            {
                "start_ms": int(r.start_ms),
                "end_ms": int(r.end_ms),
                "label": r.label,
            }
            for r in regions
        ],
    }
    return _json_response(200, payload)


def _endpoint_post_flagged_regions(
    snapshot: ProjectSnapshot,
    query: Mapping[str, str],
    body: bytes | None,
) -> ApiResponse:
    """POST handler — atomic replacement of the flagged-region list."""
    from talking_parrot.gui import http_server

    if body is None:
        return _error(400, "missing request body")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _error(400, "malformed JSON")
    if not isinstance(payload, dict) or "regions" not in payload:
        return _error(400, "missing 'regions' key")
    raw_regions = payload["regions"]
    if not isinstance(raw_regions, list):
        return _error(400, "'regions' must be a list")
    parsed: list[http_server.FlaggedRegion] = []
    for entry in raw_regions:
        if not isinstance(entry, dict):
            return _error(400, "region entries must be objects")
        if "start_ms" not in entry or "end_ms" not in entry:
            return _error(400, "region missing start_ms/end_ms")
        try:
            start_ms = int(entry["start_ms"])
            end_ms = int(entry["end_ms"])
        except (TypeError, ValueError):
            return _error(400, "start_ms/end_ms must be integers")
        if start_ms < 0 or end_ms <= start_ms:
            return _error(400, "invalid region interval")
        label_value = entry.get("label")
        if label_value is not None and not isinstance(label_value, str):
            return _error(400, "label must be string or null")
        parsed.append(
            http_server.FlaggedRegion(
                start_ms=start_ms, end_ms=end_ms, label=label_value
            )
        )
    http_server._set_flagged_regions(parsed)
    return _json_response(200, {"status": "ok"})


# A module-level lock is intentionally NOT defined here; the lock lives in
# ``http_server`` per the design's "module-level singleton" requirement.
__all__ = ["ApiResponse", "dispatch"]
