"""Unit tests for :class:`HallucinationFilterStage`.

These tests verify the four spec requirements added in change
``segment-level-postprocessing-pipeline``:

* Stage shape (name property, returns new context).
* Six independently toggleable filter rules + thresholds + ordering.
* INFO summary log and DEBUG per-drop log entries.
* Frozen-context contract: only ``transcription_results`` is rewritten.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from pathlib import Path

import pytest

from talking_parrot.config.models import (
    AlignConfig,
    HallucinationFilterConfig,
    PipelineConfig,
    TranscribingStep,
)
from talking_parrot.models.chunk import Chunk
from talking_parrot.models.context import (
    AlignmentStatus,
    PipelineContext,
)
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.stages.hallucination_filter_stage import (
    HallucinationFilterStage,
)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences emitted by structlog's ConsoleRenderer."""
    return _ANSI_RE.sub("", s)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _metrics(
    *,
    avg_logprob: float = -0.3,
    no_speech_prob: float = 0.1,
    compression_ratio: float = 1.6,
    repetition_ratio: float = 0.05,
) -> TranscriptionMetrics:
    """Build a TranscriptionMetrics with metric defaults that pass all rules."""
    return TranscriptionMetrics(
        avg_logprob=avg_logprob,
        compression_ratio=compression_ratio,
        no_speech_prob=no_speech_prob,
        repetition_ratio=repetition_ratio,
    )


def _result(
    text: str,
    *,
    chunk_index: int = 0,
    start_ms: int = 0,
    end_ms: int = 1000,
    metrics: TranscriptionMetrics | None = None,
) -> TranscriptionResult:
    """Construct a TranscriptionResult, defaulting to clean metrics."""
    return TranscriptionResult(
        chunk_index=chunk_index,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        language="ja",
        model_used="fake",
        metrics=metrics if metrics is not None else _metrics(),
        aligned_tokens=None,
    )


def _make_ctx(
    transcription_results: list[TranscriptionResult],
    *,
    chunks: list[Chunk] | None = None,
) -> PipelineContext:
    """Build a minimal PipelineContext for the stage."""
    cfg = PipelineConfig(
        transcribing=[TranscribingStep(condition="true", backend="fake")],
        align=AlignConfig(enabled=True, granularity="AUTO"),
    )
    info = MediaInfo(path=Path("/tmp/x.wav"), duration_ms=1000, sha256="0" * 64)
    return PipelineContext(
        config=cfg,
        media_info=info,
        chunks=chunks or [],
        transcription_results=transcription_results,
    )


# ---------------------------------------------------------------------------
# Task 4.1 — name + returns new context
# ---------------------------------------------------------------------------


def test_name_property_returns_hallucination_filter() -> None:
    """``HallucinationFilterStage.name`` MUST equal ``"hallucination_filter"``."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    assert stage.name == "hallucination_filter"


def test_process_returns_new_context_object() -> None:
    """Stage MUST return a PipelineContext distinct from its input (different identity)."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([_result("hello")])
    out = stage.process(ctx)
    assert isinstance(out, PipelineContext)
    assert out is not ctx


# ---------------------------------------------------------------------------
# Task 4.2 — Disabled
# ---------------------------------------------------------------------------


def test_disabled_stage_returns_transcription_results_unchanged() -> None:
    """When ``enabled=False``, the output's transcription_results MUST be the same list reference."""
    cfg = HallucinationFilterConfig(enabled=False)
    stage = HallucinationFilterStage(cfg)
    inputs = [
        _result("[音楽]"),
        _result("ご視聴ありがとうございました"),
        _result("あああああ"),
    ]
    ctx = _make_ctx(inputs)
    out = stage.process(ctx)
    assert out.transcription_results is ctx.transcription_results


# ---------------------------------------------------------------------------
# Task 4.2 — Bracket rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "[音楽]",
        "(applause)",
        "（拍手）",
        "【字幕】",
    ],
)
def test_bracket_only_text_dropped(text: str) -> None:
    """All four bracket variants — ASCII & full-width — are dropped by the bracket rule."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([_result(text)])
    out = stage.process(ctx)
    assert out.transcription_results == []


def test_bracket_rule_disabled_keeps_bracket_text() -> None:
    """When ``bracket_match_enabled=False``, bracket-only text passes through."""
    cfg = HallucinationFilterConfig(bracket_match_enabled=False)
    stage = HallucinationFilterStage(cfg)
    ctx = _make_ctx([_result("[音楽]")])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1
    assert out.transcription_results[0].text == "[音楽]"


# ---------------------------------------------------------------------------
# Task 4.2 — Phrase rule
# ---------------------------------------------------------------------------


def test_phrase_exact_match_dropped() -> None:
    """A result whose stripped text exactly matches a known phrase is dropped."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([_result("  ご視聴ありがとうございました  ")])
    out = stage.process(ctx)
    assert out.transcription_results == []


def test_phrase_rule_disabled_keeps_known_phrase() -> None:
    """When ``phrase_match_enabled=False``, known hallucination phrases pass through."""
    cfg = HallucinationFilterConfig(phrase_match_enabled=False)
    stage = HallucinationFilterStage(cfg)
    ctx = _make_ctx([_result("ご視聴ありがとうございました")])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1


# ---------------------------------------------------------------------------
# Task 4.2 — Long character repetition rule
# ---------------------------------------------------------------------------


def test_long_repeat_five_chars_dropped() -> None:
    """Five identical non-whitespace characters in a row trigger the repeat rule."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([_result("あああああ")])
    out = stage.process(ctx)
    assert out.transcription_results == []


def test_short_repeat_two_chars_kept() -> None:
    """Two identical chars are below the regex threshold of five and survive."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([_result("ああ")])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1


def test_repeat_rule_disabled_keeps_long_repeat() -> None:
    """When ``repeat_match_enabled=False``, long repeats pass through."""
    cfg = HallucinationFilterConfig(repeat_match_enabled=False)
    stage = HallucinationFilterStage(cfg)
    ctx = _make_ctx([_result("あああああ")])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1


# ---------------------------------------------------------------------------
# Task 4.2 — Threshold decision table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "avg_logprob,no_speech_prob,compression_ratio,repetition_ratio,expected_dropped",
    [
        (-0.3, 0.1, 1.6, 0.05, False),
        (-1.5, 0.7, 1.8, 0.05, True),  # low_logprob + no_speech
        (-0.3, 0.1, 3.5, 0.05, True),  # compression
        (-0.3, 0.1, 1.6, 0.6, True),  # repetition
    ],
)
def test_threshold_decision_table(
    avg_logprob: float,
    no_speech_prob: float,
    compression_ratio: float,
    repetition_ratio: float,
    expected_dropped: bool,
) -> None:
    """Exercise the threshold decision table from the spec at default thresholds."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    metrics = _metrics(
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        compression_ratio=compression_ratio,
        repetition_ratio=repetition_ratio,
    )
    ctx = _make_ctx([_result("clean text", metrics=metrics)])
    out = stage.process(ctx)
    if expected_dropped:
        assert out.transcription_results == []
    else:
        assert len(out.transcription_results) == 1


def test_low_logprob_requires_both_conditions() -> None:
    """Rule 4 needs BOTH low avg_logprob AND high no_speech_prob; isolation from rules 5/6."""
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    # avg_logprob below threshold but no_speech_prob below threshold → not dropped.
    metrics = _metrics(avg_logprob=-1.5, no_speech_prob=0.1)
    ctx = _make_ctx([_result("clean text", metrics=metrics)])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1


# ---------------------------------------------------------------------------
# Task 4.2 — Per-rule independent toggles for metric rules
# ---------------------------------------------------------------------------


def test_low_logprob_rule_disabled_keeps_result() -> None:
    """When ``low_logprob_match_enabled=False``, the rule must not fire."""
    cfg = HallucinationFilterConfig(low_logprob_match_enabled=False)
    stage = HallucinationFilterStage(cfg)
    metrics = _metrics(avg_logprob=-1.5, no_speech_prob=0.7)
    ctx = _make_ctx([_result("clean text", metrics=metrics)])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1


def test_compression_rule_disabled_keeps_result() -> None:
    """When ``compression_match_enabled=False``, the rule must not fire."""
    cfg = HallucinationFilterConfig(compression_match_enabled=False)
    stage = HallucinationFilterStage(cfg)
    metrics = _metrics(compression_ratio=3.5)
    ctx = _make_ctx([_result("clean text", metrics=metrics)])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1


def test_repetition_rule_disabled_keeps_result() -> None:
    """When ``repetition_match_enabled=False``, the rule must not fire."""
    cfg = HallucinationFilterConfig(repetition_match_enabled=False)
    stage = HallucinationFilterStage(cfg)
    metrics = _metrics(repetition_ratio=0.6)
    ctx = _make_ctx([_result("clean text", metrics=metrics)])
    out = stage.process(ctx)
    assert len(out.transcription_results) == 1


# ---------------------------------------------------------------------------
# Task 4.2 — Order preserved across drops
# ---------------------------------------------------------------------------


def test_order_preserved_across_drops() -> None:
    """A (kept), B (drop: bracket), C (kept), D (drop: long repeat) → [A, C]."""
    a = _result("hello A", chunk_index=0)
    b = _result("[音楽]", chunk_index=1)
    c = _result("hello C", chunk_index=2)
    d = _result("んんんんん", chunk_index=3)
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([a, b, c, d])
    out = stage.process(ctx)
    assert out.transcription_results == [a, c]


# ---------------------------------------------------------------------------
# Task 4.3 — Logging
# ---------------------------------------------------------------------------


def test_summary_log_emitted_with_before_after_dropped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An INFO log line MUST contain before=5, after=3, dropped=2."""
    a = _result("clean a", chunk_index=0)
    b = _result("[音楽]", chunk_index=1)
    c = _result("clean c", chunk_index=2)
    d = _result("あああああ", chunk_index=3)
    e = _result("clean e", chunk_index=4)
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([a, b, c, d, e])

    with caplog.at_level(logging.INFO, logger="talking_parrot.stages"):
        stage.process(ctx)

    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    assert any(
        "before=5" in _strip_ansi(r.getMessage())
        and "after=3" in _strip_ansi(r.getMessage())
        and "dropped=2" in _strip_ansi(r.getMessage())
        for r in info_records
    ), [_strip_ansi(r.getMessage()) for r in info_records]


def test_debug_per_drop_log_includes_chunk_index_and_rule(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """For each dropped result a DEBUG log entry includes chunk_index and rule."""
    bracket = _result("[音楽]", chunk_index=7)
    repeat = _result("ぬぬぬぬぬ", chunk_index=11)
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    ctx = _make_ctx([bracket, repeat])

    with caplog.at_level(logging.DEBUG, logger="talking_parrot.stages"):
        stage.process(ctx)

    debug_msgs = [
        _strip_ansi(r.getMessage())
        for r in caplog.records
        if r.levelno == logging.DEBUG
    ]
    assert any("chunk_index=7" in m and "rule=bracket" in m for m in debug_msgs), (
        debug_msgs
    )
    assert any("chunk_index=11" in m and "rule=repeat" in m for m in debug_msgs), (
        debug_msgs
    )


def test_disabled_stage_does_not_emit_summary_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When disabled, no INFO summary line is emitted (per-spec gating)."""
    cfg = HallucinationFilterConfig(enabled=False)
    stage = HallucinationFilterStage(cfg)
    ctx = _make_ctx([_result("[音楽]")])
    with caplog.at_level(logging.INFO, logger="talking_parrot.stages"):
        stage.process(ctx)
    info_msgs = [
        _strip_ansi(r.getMessage()) for r in caplog.records if r.levelno == logging.INFO
    ]
    assert not any("dropped=" in m for m in info_msgs)


# ---------------------------------------------------------------------------
# Task 4.4 — Frozen-context contract
# ---------------------------------------------------------------------------


def test_only_transcription_results_changes_other_fields_untouched() -> None:
    """All non-transcription_results fields are reference-equal to the input."""
    chunks = [Chunk(index=0, start_ms=0, end_ms=1000)]
    a = _result("clean a", chunk_index=0)
    b = _result("[音楽]", chunk_index=0)
    cfg = PipelineConfig(
        transcribing=[TranscribingStep(condition="true", backend="fake")],
        align=AlignConfig(enabled=True, granularity="AUTO"),
    )
    info = MediaInfo(path=Path("/tmp/x.wav"), duration_ms=1000, sha256="0" * 64)
    ctx = PipelineContext(
        config=cfg,
        media_info=info,
        vad_segments=["seg-marker"],
        chunks=chunks,
        transcription_results=[a, b],
        alignment_status=AlignmentStatus.DISABLED,
        alignment_granularity=None,
        alignment_results=["align-marker"],
        subtitles=["sub-marker"],
    )
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    out = stage.process(ctx)

    assert out.config is ctx.config
    assert out.media_info is ctx.media_info
    assert out.vad_segments is ctx.vad_segments
    assert out.chunks is ctx.chunks
    assert out.alignment_status is ctx.alignment_status
    assert out.alignment_granularity is ctx.alignment_granularity
    assert out.alignment_results is ctx.alignment_results
    assert out.subtitles is ctx.subtitles


def test_returns_new_context_with_new_transcription_list() -> None:
    """``dataclasses.replace`` semantics: new ctx, new list (not mutating input)."""
    a = _result("clean a", chunk_index=0)
    b = _result("[音楽]", chunk_index=0)
    ctx = _make_ctx([a, b])
    stage = HallucinationFilterStage(HallucinationFilterConfig())
    out = stage.process(ctx)
    assert out is not ctx
    assert out.transcription_results is not ctx.transcription_results
    # Sanity: the input list reference is unchanged in length.
    assert len(ctx.transcription_results) == 2
    assert dataclasses.is_dataclass(out)
