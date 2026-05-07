"""Unit tests for :class:`AlignmentStage`.

All ``torch`` / ``torchaudio`` / ``transformers`` interactions are bypassed by
using a :class:`_FakeAlignmentBackend` and a :class:`_FakeFactory`. The
``AudioReader`` dependency is replaced by :class:`_StubAudioReader`. No heavy
ML libraries are loaded.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pytest

from talking_parrot.alignment.backend import AlignmentBackend
from talking_parrot.config.models import (
    AlignConfig,
    PipelineConfig,
    TranscribingStep,
)
from talking_parrot.io.audio_reader import AudioReader
from talking_parrot.models.chunk import Chunk
from talking_parrot.models.context import (
    AlignmentGranularity,
    AlignmentStatus,
    GranularityPreference,
    PipelineContext,
)
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.transcription import (
    AlignedToken,
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.stages.alignment_stage import AlignmentStage

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences emitted by structlog's ConsoleRenderer."""
    return _ANSI_RE.sub("", s)


# ---------------------------------------------------------------------------
# Shared fixtures and fakes (Task 8.1)
# ---------------------------------------------------------------------------


class _FakeAlignmentBackend(AlignmentBackend):
    """Backend with parametrisable language, granularity, and align behaviour."""

    def __init__(
        self,
        language: str = "en",
        granularity: AlignmentGranularity = AlignmentGranularity.WORD,
        tokens_per_call: list[list[AlignedToken]] | None = None,
        exception_per_call: list[Exception | None] | None = None,
    ) -> None:
        """Configure the parametrisable behaviour."""
        self._language = language
        self._granularity = granularity
        self._tokens_per_call = tokens_per_call or []
        self._exception_per_call = exception_per_call or []
        self._call_idx = 0
        self.calls: list[dict[str, Any]] = []

    @property
    def language(self) -> str:
        """Return the configured language."""
        return self._language

    @property
    def granularity(self) -> AlignmentGranularity:
        """Return the configured granularity."""
        return self._granularity

    def align(
        self, audio_data: bytes, sample_rate: int, transcript: str
    ) -> list[AlignedToken]:
        """Record the call; raise or return per-call configured value."""
        idx = self._call_idx
        self._call_idx += 1
        self.calls.append(
            {
                "audio_data_len": len(audio_data),
                "sample_rate": sample_rate,
                "transcript": transcript,
            }
        )
        if (
            idx < len(self._exception_per_call)
            and self._exception_per_call[idx] is not None
        ):
            raise self._exception_per_call[idx]  # type: ignore[misc]
        if idx < len(self._tokens_per_call):
            return self._tokens_per_call[idx]
        return []


class _StubAudioReader(AudioReader):
    """Audio reader that returns a fixed-size silence buffer per ``read`` call."""

    def __init__(self, sample_rate: int = 16000) -> None:
        """Capture the sample rate."""
        self._sample_rate = sample_rate
        self.read_calls: list[tuple[int, int]] = []

    @property
    def sample_rate(self) -> int:
        """Return the configured sample rate."""
        return self._sample_rate

    def read(self, start_ms: int, end_ms: int) -> bytes:
        """Return a silence buffer sized to the requested window."""
        self.read_calls.append((start_ms, end_ms))
        num_samples = int((end_ms - start_ms) * self._sample_rate / 1000)
        return b"\x00\x00" * max(num_samples, 1)


class _FakeFactory:
    """Factory whose ``create`` returns a parametrisable backend or raises."""

    def __init__(
        self,
        backend: _FakeAlignmentBackend | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        """Configure the create behaviour."""
        self._backend = backend
        self._raise_exc = raise_exc
        self.create_calls: list[tuple[str, GranularityPreference]] = []

    def create(
        self,
        language: str,
        granularity_pref: GranularityPreference = GranularityPreference.AUTO,
    ) -> AlignmentBackend:
        """Record the call and either raise or return the configured backend."""
        self.create_calls.append((language, granularity_pref))
        if self._raise_exc is not None:
            raise self._raise_exc
        assert self._backend is not None, "FakeFactory has no backend configured"
        return self._backend


def _make_metrics() -> TranscriptionMetrics:
    """Return a deterministic ``TranscriptionMetrics`` value."""
    return TranscriptionMetrics(
        avg_logprob=-0.1,
        compression_ratio=1.0,
        no_speech_prob=0.0,
        repetition_ratio=1.0,
    )


def _make_result(
    chunk_index: int, start_ms: int, end_ms: int, text: str
) -> TranscriptionResult:
    """Return a deterministic ``TranscriptionResult``."""
    return TranscriptionResult(
        chunk_index=chunk_index,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        language="en",
        model_used="fake",
        metrics=_make_metrics(),
        aligned_tokens=None,
    )


def _make_ctx(
    *,
    align: AlignConfig | None = AlignConfig(enabled=True, granularity="AUTO"),
    expected_language: str | None = "en",
    chunks: list[Chunk] | None = None,
    transcription_results: list[TranscriptionResult] | None = None,
) -> PipelineContext:
    """Build a :class:`PipelineContext` for use in the stage tests."""
    config = PipelineConfig(
        expected_language=expected_language,
        transcribing=[TranscribingStep(condition="true", backend="fake")],
        align=align,
    )
    media_info = MediaInfo(
        path=Path("/tmp/fake.wav"), duration_ms=60_000, sha256="0" * 64
    )
    return PipelineContext(
        config=config,
        media_info=media_info,
        chunks=chunks or [],
        transcription_results=transcription_results or [],
    )


# ---------------------------------------------------------------------------
# Task 8.2 — name property and disabled-path tests
# ---------------------------------------------------------------------------


def test_name_property_returns_alignment() -> None:
    """``AlignmentStage.name`` MUST equal ``"alignment"``."""
    stage = AlignmentStage(_FakeFactory(), _StubAudioReader())
    assert stage.name == "alignment"


def test_disabled_when_align_config_is_none() -> None:
    """``ctx.config.align is None`` MUST yield DISABLED with empty results."""
    factory = _FakeFactory()
    stage = AlignmentStage(factory, _StubAudioReader())
    ctx = _make_ctx(align=None)
    out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.DISABLED
    assert out.alignment_granularity is None
    assert out.alignment_results == []
    assert factory.create_calls == []


def test_disabled_when_align_enabled_false_does_not_call_factory() -> None:
    """``align.enabled=False`` MUST short-circuit without calling factory.create."""
    factory = _FakeFactory()
    stage = AlignmentStage(factory, _StubAudioReader())
    ctx = _make_ctx(align=AlignConfig(enabled=False, granularity="AUTO"))
    out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.DISABLED
    assert factory.create_calls == []


# ---------------------------------------------------------------------------
# Task 8.3 — factory ValueError fallback
# ---------------------------------------------------------------------------


def test_factory_value_error_yields_failed_status_and_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A factory ValueError MUST yield FAILED + WARNING and leave inputs untouched."""
    factory = _FakeFactory(
        raise_exc=ValueError("No alignment backend for language: fr")
    )
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [Chunk(index=0, start_ms=0, end_ms=1000)]
    results = [_make_result(chunk_index=0, start_ms=0, end_ms=1000, text="hi")]
    ctx = _make_ctx(
        expected_language="fr", chunks=chunks, transcription_results=results
    )
    with caplog.at_level(logging.WARNING):
        out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.FAILED
    assert out.alignment_granularity is None
    assert out.alignment_results == []
    # Original transcription_results are unchanged.
    assert out.transcription_results is ctx.transcription_results
    assert any("WARNING" == rec.levelname for rec in caplog.records)


# ---------------------------------------------------------------------------
# Task 8.4 — granularity parsing is case-insensitive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("auto", GranularityPreference.AUTO),
        ("WORD", GranularityPreference.WORD),
        ("character", GranularityPreference.CHARACTER),
    ],
)
def test_granularity_string_parsed_case_insensitively(
    raw: str, expected: GranularityPreference
) -> None:
    """Lower / upper / mixed case all resolve to the corresponding preference."""
    backend = _FakeAlignmentBackend(tokens_per_call=[[]])
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [Chunk(index=0, start_ms=0, end_ms=1000)]
    results = [_make_result(0, 0, 1000, "hi")]
    ctx = _make_ctx(
        align=AlignConfig(enabled=True, granularity=raw),
        chunks=chunks,
        transcription_results=results,
    )
    stage.process(ctx)
    assert factory.create_calls == [("en", expected)]


# ---------------------------------------------------------------------------
# Task 8.5 — absolute timestamp shift
# ---------------------------------------------------------------------------


def test_timestamps_shifted_by_chunk_start() -> None:
    """A chunk at start_ms=10000 with token (100..500) MUST yield (10100..10500)."""
    backend = _FakeAlignmentBackend(
        tokens_per_call=[[AlignedToken(word="hi", start_ms=100, end_ms=500, score=0.9)]]
    )
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [Chunk(index=0, start_ms=10_000, end_ms=12_000)]
    results = [_make_result(0, 10_000, 12_000, "hi")]
    ctx = _make_ctx(chunks=chunks, transcription_results=results)
    out = stage.process(ctx)
    tok = out.transcription_results[0].aligned_tokens[0]
    assert tok.start_ms == 10_100
    assert tok.end_ms == 10_500


# ---------------------------------------------------------------------------
# Task 8.6 — mixed success/failure → SUCCESS
# ---------------------------------------------------------------------------


def test_one_chunk_fails_one_succeeds_yields_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A run with one failing and one successful chunk MUST yield SUCCESS."""
    backend = _FakeAlignmentBackend(
        tokens_per_call=[
            [],  # placeholder; chunk 0 raises before reading this
            [AlignedToken(word="b", start_ms=0, end_ms=100, score=0.9)],
        ],
        exception_per_call=[RuntimeError("boom"), None],
    )
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [
        Chunk(index=0, start_ms=0, end_ms=1000),
        Chunk(index=1, start_ms=1000, end_ms=2000),
    ]
    results = [
        _make_result(0, 0, 1000, "a"),
        _make_result(1, 1000, 2000, "b"),
    ]
    ctx = _make_ctx(chunks=chunks, transcription_results=results)
    with caplog.at_level(logging.WARNING):
        out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.SUCCESS
    assert out.alignment_results[0].tokens == []
    assert out.alignment_results[1].tokens != []
    assert any(
        "alignment failed for chunk" in _strip_ansi(rec.getMessage())
        and "chunk_index=0" in _strip_ansi(rec.getMessage())
        for rec in caplog.records
    )


# ---------------------------------------------------------------------------
# Task 8.7 — all chunks fail → FAILED
# ---------------------------------------------------------------------------


def test_all_chunks_fail_yields_failed() -> None:
    """When every chunk's backend call raises, status MUST be FAILED."""
    backend = _FakeAlignmentBackend(
        exception_per_call=[RuntimeError("boom"), RuntimeError("boom")]
    )
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [
        Chunk(index=0, start_ms=0, end_ms=1000),
        Chunk(index=1, start_ms=1000, end_ms=2000),
    ]
    results = [
        _make_result(0, 0, 1000, "a"),
        _make_result(1, 1000, 2000, "b"),
    ]
    ctx = _make_ctx(chunks=chunks, transcription_results=results)
    out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.FAILED
    for r in out.transcription_results:
        assert r.aligned_tokens == []


# ---------------------------------------------------------------------------
# Task 8.8 — empty transcription_results with alignment enabled → FAILED
# ---------------------------------------------------------------------------


def test_empty_transcription_results_with_alignment_enabled_yields_failed() -> None:
    """No transcription results + alignment enabled MUST yield FAILED."""
    backend = _FakeAlignmentBackend()
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    ctx = _make_ctx(chunks=[], transcription_results=[])
    out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.FAILED
    assert out.alignment_results == []
    assert out.alignment_granularity is None


# ---------------------------------------------------------------------------
# Task 8.9 — SUCCESS records backend granularity (WORD)
# ---------------------------------------------------------------------------


def test_success_records_backend_granularity_word() -> None:
    """A successful English run MUST yield ``alignment_granularity == WORD``."""
    backend = _FakeAlignmentBackend(
        granularity=AlignmentGranularity.WORD,
        tokens_per_call=[[AlignedToken(word="hi", start_ms=0, end_ms=100, score=0.9)]],
    )
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [Chunk(index=0, start_ms=0, end_ms=1000)]
    results = [_make_result(0, 0, 1000, "hi")]
    ctx = _make_ctx(chunks=chunks, transcription_results=results)
    out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.SUCCESS
    assert out.alignment_granularity is AlignmentGranularity.WORD


# ---------------------------------------------------------------------------
# Task 8.10 — FAILED returns None granularity
# ---------------------------------------------------------------------------


def test_failed_returns_none_granularity() -> None:
    """Factory ValueError → ``alignment_granularity is None``."""
    factory = _FakeFactory(
        raise_exc=ValueError("No alignment backend for language: fr")
    )
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [Chunk(index=0, start_ms=0, end_ms=1000)]
    results = [_make_result(0, 0, 1000, "hi")]
    ctx = _make_ctx(
        expected_language="fr", chunks=chunks, transcription_results=results
    )
    out = stage.process(ctx)
    assert out.alignment_status is AlignmentStatus.FAILED
    assert out.alignment_granularity is None


# ---------------------------------------------------------------------------
# Task 8.11 — ordering preservation across 3 successful chunks
# ---------------------------------------------------------------------------


def test_three_successful_chunks_preserve_ordering_and_populate_aligned_tokens() -> (
    None
):
    """Three successful chunks MUST yield aligned_tokens for each in input order."""
    tokens_for = [
        [AlignedToken(word="a", start_ms=0, end_ms=100, score=0.9)],
        [AlignedToken(word="b", start_ms=0, end_ms=100, score=0.9)],
        [AlignedToken(word="c", start_ms=0, end_ms=100, score=0.9)],
    ]
    backend = _FakeAlignmentBackend(tokens_per_call=tokens_for)
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [
        Chunk(index=0, start_ms=0, end_ms=1000),
        Chunk(index=1, start_ms=1000, end_ms=2000),
        Chunk(index=2, start_ms=2000, end_ms=3000),
    ]
    results = [
        _make_result(0, 0, 1000, "a"),
        _make_result(1, 1000, 2000, "b"),
        _make_result(2, 2000, 3000, "c"),
    ]
    ctx = _make_ctx(chunks=chunks, transcription_results=results)
    out = stage.process(ctx)
    assert len(out.transcription_results) == 3
    assert [r.chunk_index for r in out.transcription_results] == [0, 1, 2]
    for r in out.transcription_results:
        assert r.aligned_tokens, f"chunk {r.chunk_index} has empty aligned_tokens"


# ---------------------------------------------------------------------------
# Task 8.12 — context immutability
# ---------------------------------------------------------------------------


def test_context_immutability_returns_new_instance() -> None:
    """The original ctx.transcription_results list MUST be unchanged."""
    backend = _FakeAlignmentBackend(
        tokens_per_call=[[AlignedToken(word="a", start_ms=0, end_ms=100, score=0.9)]]
    )
    factory = _FakeFactory(backend=backend)
    stage = AlignmentStage(factory, _StubAudioReader())
    chunks = [Chunk(index=0, start_ms=0, end_ms=1000)]
    results = [_make_result(0, 0, 1000, "a")]
    ctx = _make_ctx(chunks=chunks, transcription_results=results)
    original_results_id = id(ctx.transcription_results)
    original_first = ctx.transcription_results[0]

    out = stage.process(ctx)

    # New context object
    assert out is not ctx
    # Original list reference and contents preserved
    assert id(ctx.transcription_results) == original_results_id
    assert ctx.transcription_results[0] is original_first
    # The returned transcription_results is a new list with replaced entries.
    assert out.transcription_results is not ctx.transcription_results
    assert out.transcription_results[0] is not original_first
