"""Module-level snapshot binding and pure tool helpers for the MCP server.

Per the ``mcp-core`` change:

- **Decision: Module-level read-only snapshot, no global mutable state.** A
  single module-level binding holds the loaded :class:`ProjectSnapshot`. The
  one-shot installer :func:`install_snapshot` raises if called twice; the
  pure accessor :func:`get_snapshot` returns the installed snapshot. Tools
  SHALL NOT reassign or mutate this binding (audio2subtitle's mutable
  ``_project`` global is the explicit anti-pattern this avoids).
- **Decision: One decorated function per tool (ISP)** + **Decision: Tool
  catalogue and time-range filtering.** The seven pure helpers below
  (``summary_from_snapshot``, ``vad_segments_in_range``,
  ``vad_frames_in_range``, ``subtitles_in_range``,
  ``pre_postprocess_subtitles_in_range``, ``transcription_results_for_chunk``,
  ``diagnostics_from_snapshot``) take a :class:`ProjectSnapshot` plus small
  primitive args and return JSON-serialisable values. They never read from
  the filesystem and depend only on the snapshot (DIP).
- **Decision: Diagnostics are derived purely from snapshot.** The
  :func:`diagnostics_from_snapshot` helper computes low-confidence /
  repetition / no-speech flags purely from
  :attr:`ProjectSnapshot.transcription_results` and
  :attr:`ProjectSnapshot.subtitles`. Thresholds are read from
  :attr:`ProjectSnapshot.config_snapshot` when present, falling back to
  documented defaults otherwise.

Time-range helpers use the half-open ``[start_ms, end_ms)`` semantics
established in :mod:`talking_parrot.gui.api` so the MCP and GUI surfaces
stay consistent. When both bounds are ``None`` the helpers return the
full collection.

The ``@mcp.tool()`` decorators that wire these helpers into a FastMCP
instance are added in a later task that is gated on operator approval to
run ``uv add mcp``; this module does not import ``mcp`` itself.
"""

from __future__ import annotations

from typing import Any

from talking_parrot.shared import ProjectSnapshot

# Default thresholds for ``diagnostics_from_snapshot``. Documented here so the
# tests and the docstring stay in lockstep with the implementation.
_DEFAULT_LOW_CONFIDENCE_AVG_LOGPROB = -1.0
_DEFAULT_NO_SPEECH_PROB_THRESHOLD = 0.5
_DEFAULT_REPETITION_RATIO_THRESHOLD = 0.5

# Module-level snapshot binding. ``None`` until ``install_snapshot`` is
# called exactly once during entry-point setup. Tools SHALL read it via
# ``get_snapshot``; they SHALL NOT reassign it.
_snapshot: ProjectSnapshot | None = None


def install_snapshot(snapshot: ProjectSnapshot) -> None:
    """Install the module-level snapshot binding exactly once.

    Raises:
        RuntimeError: A snapshot is already installed. Restart the process
            to load a different project — runtime reload is unsupported per
            the **Reload at runtime is unsupported** scenario.
        TypeError: ``snapshot`` is not a :class:`ProjectSnapshot`.
    """
    global _snapshot
    if not isinstance(snapshot, ProjectSnapshot):
        raise TypeError(
            f"install_snapshot expected ProjectSnapshot, got {type(snapshot).__name__}"
        )
    if _snapshot is not None:
        raise RuntimeError(
            "MCP server snapshot already installed; restart the process to "
            "load a different project (runtime reload is unsupported per "
            "the mcp-server-lifecycle spec)."
        )
    _snapshot = snapshot


def get_snapshot() -> ProjectSnapshot:
    """Return the installed snapshot.

    Raises:
        RuntimeError: No snapshot has been installed yet.
    """
    if _snapshot is None:
        raise RuntimeError(
            "MCP server snapshot not installed; call install_snapshot() "
            "during entry-point setup before invoking tools."
        )
    return _snapshot


def _reset_snapshot_for_tests() -> None:
    """Test-only hook to clear the module-level binding.

    Production code SHALL NOT call this. The MCP server holds a single
    snapshot for its process lifetime by design.
    """
    global _snapshot
    _snapshot = None


# ---------------------------------------------------------------------------
# Pure tool helpers
# ---------------------------------------------------------------------------


def summary_from_snapshot(snapshot: ProjectSnapshot) -> dict[str, Any]:
    """Return aggregate counts and ``audio_duration_ms`` for the snapshot.

    Realises the ``summary`` tool. The returned dict is JSON-serialisable
    and contains:

    - ``n_vad_segments``, ``n_vad_frames``, ``n_chunks``,
      ``n_transcription_results``, ``n_subtitles``,
      ``n_pre_postprocess_subtitles``: aggregate counts.
    - ``audio_duration_ms``: mirrors ``snapshot.audio_info.duration_ms``.
    """
    return {
        "n_vad_segments": len(snapshot.vad_segments),
        "n_vad_frames": len(snapshot.vad_frames),
        "n_chunks": len(snapshot.chunks),
        "n_transcription_results": len(snapshot.transcription_results),
        "n_subtitles": len(snapshot.subtitles),
        "n_pre_postprocess_subtitles": len(snapshot.pre_postprocess_subtitles),
        "audio_duration_ms": int(snapshot.audio_info.duration_ms),
    }


def _overlaps(item_start: int, item_end: int, lo: int | None, hi: int | None) -> bool:
    """Return whether ``[item_start, item_end)`` intersects ``[lo, hi)``.

    Mirrors :mod:`talking_parrot.gui.api`'s half-open semantics. When both
    ``lo`` and ``hi`` are ``None`` the predicate returns ``True``. When only
    one bound is supplied the other defaults to "unbounded".
    """
    if lo is None and hi is None:
        return True
    if lo is None:
        assert hi is not None
        return item_start < hi
    if hi is None:
        return item_end > lo
    return item_start < hi and item_end > lo


def vad_segments_in_range(
    snapshot: ProjectSnapshot,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Return VAD segments overlapping ``[start_ms, end_ms)`` (ms).

    When both bounds are ``None`` the full collection is returned.
    """
    out: list[dict[str, Any]] = []
    for seg in snapshot.vad_segments:
        if _overlaps(seg.start_ms, seg.end_ms, start_ms, end_ms):
            out.append(
                {
                    "start_ms": int(seg.start_ms),
                    "end_ms": int(seg.end_ms),
                    "ten_vad_prob": float(seg.ten_vad_prob),
                    "silero_vad_prob": float(seg.silero_vad_prob),
                    "composite_score": float(seg.composite_score),
                }
            )
    return out


def vad_frames_in_range(
    snapshot: ProjectSnapshot,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Return VAD frames overlapping ``[start_ms, end_ms)`` (ms).

    Each frame is a point in time, so ``time_ms`` is treated as both the
    start and end of the item for overlap purposes. When both bounds are
    ``None`` the full collection is returned.
    """
    out: list[dict[str, Any]] = []
    for frame in snapshot.vad_frames:
        if _overlaps(frame.time_ms, frame.time_ms + 1, start_ms, end_ms):
            out.append(
                {
                    "time_ms": int(frame.time_ms),
                    "prob": float(frame.prob),
                    "backend": str(frame.backend),
                }
            )
    return out


def _subtitle_to_dict(idx: int, subtitle: Any) -> dict[str, Any]:
    return {
        "index": idx,
        "start_ms": int(subtitle.start_ms),
        "end_ms": int(subtitle.end_ms),
        "text": str(subtitle.text),
    }


def subtitles_in_range(
    snapshot: ProjectSnapshot,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Return subtitles overlapping ``[start_ms, end_ms)`` (ms).

    Subtitle ``index`` reflects the position in :attr:`snapshot.subtitles`
    so callers can correlate with other tools. When both bounds are
    ``None`` the full collection is returned.
    """
    out: list[dict[str, Any]] = []
    for idx, sub in enumerate(snapshot.subtitles):
        if _overlaps(sub.start_ms, sub.end_ms, start_ms, end_ms):
            out.append(_subtitle_to_dict(idx, sub))
    return out


def pre_postprocess_subtitles_in_range(
    snapshot: ProjectSnapshot,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Return pre-postprocessing subtitles overlapping ``[start_ms, end_ms)``.

    Time bounds are in milliseconds. When both bounds are ``None`` the full
    collection is returned.
    """
    out: list[dict[str, Any]] = []
    for idx, sub in enumerate(snapshot.pre_postprocess_subtitles):
        if _overlaps(sub.start_ms, sub.end_ms, start_ms, end_ms):
            out.append(_subtitle_to_dict(idx, sub))
    return out


def _transcription_to_dict(tr: Any) -> dict[str, Any]:
    aligned: list[dict[str, Any]] | None = None
    if tr.aligned_tokens is not None:
        aligned = [
            {
                "word": str(tok.word),
                "start_ms": float(tok.start_ms),
                "end_ms": float(tok.end_ms),
                "score": float(tok.score),
            }
            for tok in tr.aligned_tokens
        ]
    return {
        "chunk_index": int(tr.chunk_index),
        "start_ms": int(tr.start_ms),
        "end_ms": int(tr.end_ms),
        "text": str(tr.text),
        "language": str(tr.language),
        "model_used": str(tr.model_used),
        "metrics": {
            "avg_logprob": float(tr.metrics.avg_logprob),
            "compression_ratio": float(tr.metrics.compression_ratio),
            "no_speech_prob": float(tr.metrics.no_speech_prob),
            "repetition_ratio": float(tr.metrics.repetition_ratio),
        },
        "aligned_tokens": aligned,
    }


def transcription_results_for_chunk(
    snapshot: ProjectSnapshot,
    chunk_index: int | None = None,
) -> list[dict[str, Any]]:
    """Return transcription results, optionally filtered to ``chunk_index``.

    When ``chunk_index`` is ``None`` every transcription result is returned.
    When provided, only the result whose ``chunk_index`` matches is
    returned. An unknown ``chunk_index`` yields an empty list.
    """
    if chunk_index is None:
        return [_transcription_to_dict(tr) for tr in snapshot.transcription_results]
    return [
        _transcription_to_dict(tr)
        for tr in snapshot.transcription_results
        if int(tr.chunk_index) == int(chunk_index)
    ]


def _threshold(config: dict[str, Any], key: str, default: float) -> float:
    """Read a numeric threshold from ``config`` falling back to ``default``."""
    if not isinstance(config, dict):
        return default
    raw = config.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def diagnostics_from_snapshot(snapshot: ProjectSnapshot) -> dict[str, Any]:
    """Compute low-confidence / repetition / no-speech flags from the snapshot.

    Pure function — no I/O. Thresholds are read from
    :attr:`ProjectSnapshot.config_snapshot` when present, falling back to
    the documented defaults:

    - ``low_confidence_avg_logprob``: ``-1.0``
    - ``no_speech_prob_threshold``: ``0.5``
    - ``repetition_ratio_threshold``: ``0.5``

    Returns a dict with three lists: ``low_confidence``, ``repetition``,
    and ``no_speech``. Each entry names the responsible ``chunk_index``,
    the time interval, the metric value, and a ``reason`` field naming
    the metric that tripped the flag.
    """
    cfg = snapshot.config_snapshot if isinstance(snapshot.config_snapshot, dict) else {}
    avg_logprob_threshold = _threshold(
        cfg, "low_confidence_avg_logprob", _DEFAULT_LOW_CONFIDENCE_AVG_LOGPROB
    )
    no_speech_threshold = _threshold(
        cfg, "no_speech_prob_threshold", _DEFAULT_NO_SPEECH_PROB_THRESHOLD
    )
    repetition_threshold = _threshold(
        cfg, "repetition_ratio_threshold", _DEFAULT_REPETITION_RATIO_THRESHOLD
    )

    low_confidence: list[dict[str, Any]] = []
    repetition: list[dict[str, Any]] = []
    no_speech: list[dict[str, Any]] = []

    for tr in snapshot.transcription_results:
        avg_logprob = float(tr.metrics.avg_logprob)
        no_speech_prob = float(tr.metrics.no_speech_prob)
        repetition_ratio = float(tr.metrics.repetition_ratio)
        if avg_logprob < avg_logprob_threshold:
            low_confidence.append(
                {
                    "chunk_index": int(tr.chunk_index),
                    "start_ms": int(tr.start_ms),
                    "end_ms": int(tr.end_ms),
                    "avg_logprob": avg_logprob,
                    "reason": "avg_logprob",
                }
            )
        if no_speech_prob >= no_speech_threshold:
            no_speech.append(
                {
                    "chunk_index": int(tr.chunk_index),
                    "start_ms": int(tr.start_ms),
                    "end_ms": int(tr.end_ms),
                    "no_speech_prob": no_speech_prob,
                    "reason": "no_speech_prob",
                }
            )
        if repetition_ratio >= repetition_threshold:
            repetition.append(
                {
                    "chunk_index": int(tr.chunk_index),
                    "start_ms": int(tr.start_ms),
                    "end_ms": int(tr.end_ms),
                    "repetition_ratio": repetition_ratio,
                    "reason": "repetition_ratio",
                }
            )

    return {
        "low_confidence": low_confidence,
        "repetition": repetition,
        "no_speech": no_speech,
        "thresholds": {
            "low_confidence_avg_logprob": avg_logprob_threshold,
            "no_speech_prob_threshold": no_speech_threshold,
            "repetition_ratio_threshold": repetition_threshold,
        },
    }


# ---------------------------------------------------------------------------
# FastMCP application factory
# ---------------------------------------------------------------------------


def build_mcp_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    streamable_http_path: str = "/mcp",
) -> Any:
    """Construct a :class:`FastMCP` app with the seven tools registered.

    Realises the **Decision: One decorated function per tool (ISP)**: each
    tool is its own ``@mcp.tool()``-decorated function delegating to a pure
    helper from this module. Tools read the loaded snapshot via the
    module-level :func:`get_snapshot` accessor.

    The ``host``, ``port``, and ``streamable_http_path`` keyword arguments
    are forwarded to FastMCP's settings so the streamable-HTTP runner binds
    to the resolved address. Defaults match the **Default bind is loopback
    host and port 8765** and **MCP endpoint path is ``/mcp``** requirements.
    """
    # Import lazily so the no-dep portion of the package (pure helpers) does
    # not require ``mcp`` to be installed for unrelated unit tests.
    import logging as _logging

    from mcp.server.fastmcp import FastMCP

    _log = _logging.getLogger("talking_parrot.mcp")
    _log.debug(
        "calling FastMCP.__init__ host=%s port=%s streamable_http_path=%s",
        host,
        port,
        streamable_http_path,
    )
    mcp = FastMCP(
        "talking-parrot",
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
    )
    assert hasattr(mcp, "tool"), (
        "FastMCP instance missing 'tool' decorator — mcp library API may have changed"
    )
    assert hasattr(mcp, "run"), (
        "FastMCP instance missing 'run' method — mcp library API may have changed"
    )

    @mcp.tool()
    def summary() -> dict[str, Any]:
        """Return aggregate counts and ``audio_duration_ms`` (milliseconds)."""
        return summary_from_snapshot(get_snapshot())

    @mcp.tool()
    def get_vad_segments(
        start_ms: int | None = None, end_ms: int | None = None
    ) -> list[dict[str, Any]]:
        """Return VAD segments overlapping ``[start_ms, end_ms)`` (milliseconds)."""
        return vad_segments_in_range(get_snapshot(), start_ms, end_ms)

    @mcp.tool()
    def get_vad_frames(
        start_ms: int | None = None, end_ms: int | None = None
    ) -> list[dict[str, Any]]:
        """Return VAD frames overlapping ``[start_ms, end_ms)`` (milliseconds)."""
        return vad_frames_in_range(get_snapshot(), start_ms, end_ms)

    @mcp.tool()
    def get_subtitles(
        start_ms: int | None = None, end_ms: int | None = None
    ) -> list[dict[str, Any]]:
        """Return subtitles overlapping ``[start_ms, end_ms)`` (milliseconds)."""
        return subtitles_in_range(get_snapshot(), start_ms, end_ms)

    @mcp.tool()
    def get_pre_postprocess_subtitles(
        start_ms: int | None = None, end_ms: int | None = None
    ) -> list[dict[str, Any]]:
        """Return pre-postprocessing subtitles in range (milliseconds)."""
        return pre_postprocess_subtitles_in_range(get_snapshot(), start_ms, end_ms)

    @mcp.tool()
    def get_transcription_results(
        chunk_index: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return transcription results, optionally filtered by ``chunk_index``."""
        return transcription_results_for_chunk(get_snapshot(), chunk_index)

    @mcp.tool()
    def diagnostics() -> dict[str, Any]:
        """Return low-confidence / repetition / no-speech flags from the snapshot."""
        return diagnostics_from_snapshot(get_snapshot())

    return mcp


__all__ = [
    "build_mcp_app",
    "diagnostics_from_snapshot",
    "get_snapshot",
    "install_snapshot",
    "pre_postprocess_subtitles_in_range",
    "subtitles_in_range",
    "summary_from_snapshot",
    "transcription_results_for_chunk",
    "vad_frames_in_range",
    "vad_segments_in_range",
]
