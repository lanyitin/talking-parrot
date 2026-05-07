"""Unit tests for ``TranscriptionStage``.

The tests use a real ``ConditionEvaluator`` and a stub
``TranscriptionBackendFactory`` so that no third-party libraries are loaded.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from talking_parrot.config.models import PipelineConfig, TranscribingStep
from talking_parrot.expression.condition import ConditionEvaluator
from talking_parrot.models.chunk import Chunk
from talking_parrot.models.context import PipelineContext
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.stages.transcription_stage import TranscriptionStage
from talking_parrot.transcription.backend import TranscriptionBackend

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences emitted by structlog's ConsoleRenderer."""
    return _ANSI_RE.sub("", s)


# ---------------------------------------------------------------------------
# Shared fixtures and fakes (Task 6.1)
# ---------------------------------------------------------------------------


class FakeBackend(TranscriptionBackend):
    """Backend that returns a parametrisable ``TranscriptionResult`` per call.

    The ``result_factory`` is invoked with the chunk and call args so a single
    ``FakeBackend`` instance can be parameterised per-step.
    """

    def __init__(
        self,
        backend_name: str = "fake",
        result_factory=None,
        raise_exc: BaseException | None = None,
    ) -> None:
        """Capture the configurable behaviour for ``transcribe()``."""
        self._backend_name = backend_name
        self._result_factory = result_factory
        self._raise_exc = raise_exc
        self.calls: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        """Return the configured backend identifier."""
        return self._backend_name

    def transcribe(
        self,
        audio_path,
        chunk: Chunk,
        model: str,
        language: str | None,
    ) -> list[TranscriptionResult]:
        """Record the call and either raise or return a parametrised list of results.

        ``result_factory`` may return either a single ``TranscriptionResult``
        (auto-wrapped into a one-element list for legacy callers) or a list.
        """
        self.calls.append(
            {
                "audio_path": audio_path,
                "chunk": chunk,
                "model": model,
                "language": language,
            }
        )
        if self._raise_exc is not None:
            raise self._raise_exc
        if self._result_factory is not None:
            out = self._result_factory(chunk, model, language)
            if isinstance(out, list):
                return out
            return [out]
        # Default: deterministic well-formed single-segment result wrapped in a list.
        return [
            TranscriptionResult(
                chunk_index=chunk.index,
                start_ms=chunk.start_ms,
                end_ms=chunk.end_ms,
                text=f"text-{chunk.index}-{model}",
                language=language or "en",
                model_used=model,
                metrics=TranscriptionMetrics(0.0, 0.0, 0.0, 0.0),
                aligned_tokens=None,
            )
        ]


class StubFactory:
    """Stub ``TranscriptionBackendFactory`` returning per-name ``FakeBackend`` objects.

    ``create()`` returns the same instance per name (so cache identity holds)
    and counts invocations.
    """

    def __init__(self, backends: dict[str, FakeBackend] | None = None) -> None:
        """Capture the per-name backend mapping (default empty)."""
        self.backends = backends or {}
        self.create_call_log: list[str] = []

    def create(self, name: str) -> FakeBackend:
        """Return the registered FakeBackend, raising ``KeyError`` for unknown names."""
        self.create_call_log.append(name)
        if name not in self.backends:
            raise KeyError(name)
        return self.backends[name]


def _make_chunk(index: int, start_ms: int = 0, end_ms: int = 1000) -> Chunk:
    """Helper to construct a Chunk for tests."""
    return Chunk(index=index, start_ms=start_ms, end_ms=end_ms, source_segments=[])


def _make_ctx(
    chunks: list[Chunk],
    transcribing: list[dict],
    *,
    expected_language: str | None = None,
) -> PipelineContext:
    """Construct a PipelineContext for stage tests."""
    cfg = PipelineConfig(
        transcribing=[TranscribingStep(**step) for step in transcribing],
        expected_language=expected_language,
    )
    info = MediaInfo(path=Path("/tmp/test.wav"), duration_ms=60000, sha256="deadbeef")
    return PipelineContext(
        config=cfg,
        media_info=info,
        vad_segments=[],
        chunks=chunks,
        transcription_results=[],
    )


@pytest.fixture()
def evaluator() -> ConditionEvaluator:
    """Return a real ``ConditionEvaluator`` for use across tests."""
    return ConditionEvaluator()


# ---------------------------------------------------------------------------
# Task 6.2 — Empty-chunks short-circuit
# ---------------------------------------------------------------------------


def test_empty_chunks_short_circuits(evaluator: ConditionEvaluator) -> None:
    """``ctx.chunks == []`` returns the same context object; factory.create is never called."""
    factory = StubFactory({})
    stage = TranscriptionStage(factory=factory, evaluator=evaluator)  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[],
        transcribing=[{"condition": "true", "backend": "fake", "model": "base"}],
    )
    out = stage.process(ctx)
    assert out is ctx
    assert factory.create_call_log == []


# ---------------------------------------------------------------------------
# Task 6.3 — One result per chunk in input order
# ---------------------------------------------------------------------------


def test_one_result_per_chunk_in_order(evaluator: ConditionEvaluator) -> None:
    """3 chunks with index=[0,1,2] yield 3 results with chunk_index in order."""
    fake = FakeBackend()
    factory = StubFactory({"fake": fake})
    stage = TranscriptionStage(factory=factory, evaluator=evaluator)  # type: ignore[arg-type]

    chunks = [_make_chunk(i) for i in range(3)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[{"condition": "true", "backend": "fake", "model": "base"}],
    )
    out = stage.process(ctx)
    assert [r.chunk_index for r in out.transcription_results] == [0, 1, 2]
    assert len(out.transcription_results) == 3


# ---------------------------------------------------------------------------
# Task 6.4 — Step 0 evaluator call shape
# ---------------------------------------------------------------------------


def test_step_0_evaluator_invoked_with_empty_variables() -> None:
    """Step 0 MUST be evaluated with ``expression="true"`` and ``variables={}``."""
    spy_evaluator = MagicMock(wraps=ConditionEvaluator())
    fake = FakeBackend()
    factory = StubFactory({"fake": fake})
    stage = TranscriptionStage(factory=factory, evaluator=spy_evaluator)  # type: ignore[arg-type]

    chunks = [_make_chunk(0)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[{"condition": "true", "backend": "fake", "model": "base"}],
    )
    stage.process(ctx)

    first_call = spy_evaluator.evaluate.call_args_list[0]
    assert first_call.args[0] == "true"
    assert first_call.args[1] == {}


# ---------------------------------------------------------------------------
# Task 6.5 — Cascade halts on falsy condition
# ---------------------------------------------------------------------------


def test_cascade_halts_on_falsy_condition() -> None:
    """Step 1 condition False against step 0 metrics: step 1 backend never runs."""

    # Step 0 emits avg_logprob = -0.1 -> step 1 condition "avg_logprob < -2.0" is False.
    def step0_factory(chunk: Chunk, model: str, language: str | None):
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="step0",
            language=language or "en",
            model_used=model,
            metrics=TranscriptionMetrics(
                avg_logprob=-0.1,
                compression_ratio=1.0,
                no_speech_prob=0.0,
                repetition_ratio=0.0,
            ),
            aligned_tokens=None,
        )

    step0 = FakeBackend(backend_name="b0", result_factory=step0_factory)
    step1 = FakeBackend(backend_name="b1")
    step2 = FakeBackend(backend_name="b2")

    spy_evaluator = MagicMock(wraps=ConditionEvaluator())

    factory = StubFactory({"b0": step0, "b1": step1, "b2": step2})
    stage = TranscriptionStage(factory=factory, evaluator=spy_evaluator)  # type: ignore[arg-type]

    chunks = [_make_chunk(0)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0"},
            {"condition": "avg_logprob < -2.0", "backend": "b1", "model": "m1"},
            {"condition": "true", "backend": "b2", "model": "m2"},
        ],
    )
    out = stage.process(ctx)

    assert len(step0.calls) == 1
    assert len(step1.calls) == 0
    assert len(step2.calls) == 0
    # Evaluator was called for step 0 (true) and step 1 (avg_logprob<-2.0); never for step 2.
    expressions = [c.args[0] for c in spy_evaluator.evaluate.call_args_list]
    assert expressions == ["true", "avg_logprob < -2.0"]
    assert out.transcription_results[0].text == "step0"


# ---------------------------------------------------------------------------
# Task 6.6 — Cascade upgrade on truthy condition
# ---------------------------------------------------------------------------


def test_cascade_upgrade_on_truthy_condition() -> None:
    """Step 1 condition True: both backends run; final result is step 1's."""

    def step0_factory(chunk, model, language):
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="step0",
            language="en",
            model_used=model,
            metrics=TranscriptionMetrics(-3.0, 1.0, 0.0, 0.0),
            aligned_tokens=None,
        )

    def step1_factory(chunk, model, language):
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="step1",
            language="en",
            model_used=model,
            metrics=TranscriptionMetrics(-0.5, 1.0, 0.0, 0.0),
            aligned_tokens=None,
        )

    step0 = FakeBackend(backend_name="b0", result_factory=step0_factory)
    step1 = FakeBackend(backend_name="b1", result_factory=step1_factory)

    factory = StubFactory({"b0": step0, "b1": step1})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    chunks = [_make_chunk(0)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0"},
            {"condition": "avg_logprob < -1.0", "backend": "b1", "model": "m1"},
        ],
    )
    out = stage.process(ctx)
    assert len(step0.calls) == 1
    assert len(step1.calls) == 1
    assert out.transcription_results[0].text == "step1"


# ---------------------------------------------------------------------------
# Task 6.7 — Cascade decision table from spec example
# ---------------------------------------------------------------------------


def test_cascade_decision_table_spec_example() -> None:
    """Step 0 -> -1.5/0.2; Step 1 -> -0.5/0.1; expect steps 0 and 1 ran, step 2 skipped."""

    def step0_factory(chunk, model, language):
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="base",
            language="en",
            model_used=model,
            metrics=TranscriptionMetrics(
                avg_logprob=-1.5,
                compression_ratio=1.0,
                no_speech_prob=0.0,
                repetition_ratio=0.2,
            ),
            aligned_tokens=None,
        )

    def step1_factory(chunk, model, language):
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="medium",
            language="en",
            model_used=model,
            metrics=TranscriptionMetrics(
                avg_logprob=-0.5,
                compression_ratio=1.0,
                no_speech_prob=0.0,
                repetition_ratio=0.1,
            ),
            aligned_tokens=None,
        )

    # The same backend name is used for all three; we can't distinguish per-step
    # via the factory. Use a single FakeBackend that returns different results
    # based on model name. (``step0_factory`` is referenced via ``joint_factory``
    # below.)
    call_count = {"n": 0}

    def joint_factory(chunk, model, language):
        if call_count["n"] == 0:
            call_count["n"] += 1
            return step0_factory(chunk, model, language)
        elif call_count["n"] == 1:
            call_count["n"] += 1
            return step1_factory(chunk, model, language)
        raise AssertionError("Step 2 must NOT execute")

    fw_backend = FakeBackend(
        backend_name="faster-whisper", result_factory=joint_factory
    )
    factory = StubFactory({"faster-whisper": fw_backend})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    chunks = [_make_chunk(0)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[
            {"condition": "true", "backend": "faster-whisper", "model": "base"},
            {
                "condition": "avg_logprob < -1.0",
                "backend": "faster-whisper",
                "model": "medium",
            },
            {
                "condition": "repetition_ratio > 0.4",
                "backend": "faster-whisper",
                "model": "large-v3",
            },
        ],
    )
    out = stage.process(ctx)
    assert len(fw_backend.calls) == 2  # only steps 0 and 1 ran
    assert out.transcription_results[0].text == "medium"


# ---------------------------------------------------------------------------
# Task 6.8 — Variable dict shape
# ---------------------------------------------------------------------------


def test_variable_dict_shape_for_step_n_gt_0() -> None:
    """Variable dict for step 1 MUST contain exactly the four metric keys."""

    def step0_factory(chunk, model, language):
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="x",
            language="en",
            model_used=model,
            metrics=TranscriptionMetrics(-0.1, 1.0, 0.0, 0.0),
            aligned_tokens=None,
        )

    step0 = FakeBackend(backend_name="b0", result_factory=step0_factory)
    step1 = FakeBackend(backend_name="b1")
    factory = StubFactory({"b0": step0, "b1": step1})

    spy_evaluator = MagicMock(wraps=ConditionEvaluator())
    stage = TranscriptionStage(factory=factory, evaluator=spy_evaluator)  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0)],
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0"},
            {"condition": "avg_logprob < 0.0", "backend": "b1", "model": "m1"},
        ],
    )
    stage.process(ctx)

    # The second evaluator call corresponds to step 1.
    second_call = spy_evaluator.evaluate.call_args_list[1]
    variables = second_call.args[1]
    assert set(variables.keys()) == {
        "avg_logprob",
        "compression_ratio",
        "no_speech_prob",
        "repetition_ratio",
    }


# ---------------------------------------------------------------------------
# Task 6.9 — Step 1 backend failure preserves step 0 result
# ---------------------------------------------------------------------------


def test_step_1_backend_failure_preserves_step_0_result(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Step 1 backend RuntimeError: final result is step 0's; WARNING references step 1."""

    def step0_factory(chunk, model, language):
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text="step0",
            language="en",
            model_used=model,
            metrics=TranscriptionMetrics(-3.0, 1.0, 0.0, 0.0),
            aligned_tokens=None,
        )

    step0 = FakeBackend(backend_name="b0", result_factory=step0_factory)
    step1 = FakeBackend(backend_name="b1", raise_exc=RuntimeError("boom"))
    step2 = FakeBackend(backend_name="b2")
    factory = StubFactory({"b0": step0, "b1": step1, "b2": step2})

    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0)],
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0"},
            {"condition": "avg_logprob < 0.0", "backend": "b1", "model": "m1"},
            {"condition": "true", "backend": "b2", "model": "m2"},
        ],
    )
    with caplog.at_level(logging.WARNING):
        out = stage.process(ctx)

    assert out.transcription_results[0].text == "step0"
    # WARNING log mentions step index 1
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "transcription step failed" in _strip_ansi(r.getMessage())
        and "step_index=1" in _strip_ansi(r.getMessage())
        for r in warning_records
    )
    assert len(step2.calls) == 0


# ---------------------------------------------------------------------------
# Task 6.10 — Step 0 backend failure propagates
# ---------------------------------------------------------------------------


def test_step_0_backend_failure_propagates() -> None:
    """ImportError from step 0 MUST be re-raised; no transcription results appended."""
    step0 = FakeBackend(backend_name="b0", raise_exc=ImportError("missing"))
    factory = StubFactory({"b0": step0})

    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0)],
        transcribing=[{"condition": "true", "backend": "b0", "model": "m0"}],
    )
    with pytest.raises(ImportError):
        stage.process(ctx)
    # The original ctx is unchanged.
    assert ctx.transcription_results == []


# ---------------------------------------------------------------------------
# Task 6.11 — Language fallback
# ---------------------------------------------------------------------------


def test_language_fallback_uses_expected_language_when_step_language_none() -> None:
    """``step.language=None`` → backend invoked with ``ctx.config.expected_language``."""
    fake = FakeBackend()
    factory = StubFactory({"b0": fake})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0)],
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0", "language": None}
        ],
        expected_language="en",
    )
    stage.process(ctx)
    assert fake.calls[0]["language"] == "en"


def test_language_fallback_step_language_wins_over_expected_language() -> None:
    """``step.language="ja"`` overrides ``ctx.config.expected_language="en"``."""
    fake = FakeBackend()
    factory = StubFactory({"b0": fake})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0)],
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0", "language": "ja"}
        ],
        expected_language="en",
    )
    stage.process(ctx)
    assert fake.calls[0]["language"] == "ja"


# ---------------------------------------------------------------------------
# Task 6.12 — Context immutability
# ---------------------------------------------------------------------------


def test_context_is_replaced_not_mutated() -> None:
    """Original ctx.transcription_results unchanged; output is a new context instance."""
    fake = FakeBackend()
    factory = StubFactory({"b0": fake})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    chunks = [_make_chunk(0), _make_chunk(1)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[{"condition": "true", "backend": "b0", "model": "m0"}],
    )
    original_results = ctx.transcription_results
    out = stage.process(ctx)

    # New PipelineContext (dataclasses.replace) — different object.
    assert out is not ctx
    # The original list reference is unchanged.
    assert original_results == []
    # Sanity: dataclass-replace based context.
    assert dataclasses.is_dataclass(out)
    assert len(out.transcription_results) == 2


# ---------------------------------------------------------------------------
# Task 3.1 — extend per-chunk segment lists into ctx.transcription_results
# ---------------------------------------------------------------------------


def _seg(
    chunk_index: int,
    start_ms: int,
    end_ms: int,
    text: str = "x",
    *,
    avg_logprob: float = 0.0,
    compression_ratio: float = 1.0,
    no_speech_prob: float = 0.0,
    repetition_ratio: float = 0.0,
    model: str = "m",
    language: str = "en",
) -> TranscriptionResult:
    """Build a ``TranscriptionResult`` for a single Whisper segment."""
    return TranscriptionResult(
        chunk_index=chunk_index,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        language=language,
        model_used=model,
        metrics=TranscriptionMetrics(
            avg_logprob=avg_logprob,
            compression_ratio=compression_ratio,
            no_speech_prob=no_speech_prob,
            repetition_ratio=repetition_ratio,
        ),
        aligned_tokens=None,
    )


def test_multiple_results_per_chunk_preserved_in_order() -> None:
    """Stage extends ctx.transcription_results with all per-chunk segments in order."""

    def factory_fn(chunk: Chunk, model: str, language: str | None):
        if chunk.index == 0:
            return [
                _seg(0, 0, 100, text="c0s0"),
                _seg(0, 100, 200, text="c0s1"),
                _seg(0, 200, 300, text="c0s2"),
            ]
        return [
            _seg(1, 1000, 1100, text="c1s0"),
            _seg(1, 1100, 1200, text="c1s1"),
        ]

    fake = FakeBackend(backend_name="b0", result_factory=factory_fn)
    factory = StubFactory({"b0": fake})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    chunks = [_make_chunk(0, 0, 1000), _make_chunk(1, 1000, 2000)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[{"condition": "true", "backend": "b0", "model": "m0"}],
    )
    out = stage.process(ctx)
    assert len(out.transcription_results) == 5
    assert [r.chunk_index for r in out.transcription_results] == [0, 0, 0, 1, 1]
    assert [r.text for r in out.transcription_results] == [
        "c0s0",
        "c0s1",
        "c0s2",
        "c1s0",
        "c1s1",
    ]


def test_empty_backend_result_for_chunk_extends_nothing() -> None:
    """Backend returning [] for a chunk contributes zero rows and does not error."""
    fake = FakeBackend(backend_name="b0", result_factory=lambda c, m, lang: [])
    factory = StubFactory({"b0": fake})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0, 0, 1000)],
        transcribing=[{"condition": "true", "backend": "b0", "model": "m0"}],
    )
    out = stage.process(ctx)
    assert out.transcription_results == []


# ---------------------------------------------------------------------------
# Task 3.2 — cascade aggregator (multi-segment, empty list, non-persistence)
# ---------------------------------------------------------------------------


def test_cascade_aggregate_multi_segment_decision_table() -> None:
    """Step 0: 3 segs (mean avg_logprob=-1.5, rep=0.2); Step 1: 2 segs (mean=-0.5, rep=0.1)."""

    # Step 0: three segments of duration 100 each.
    # Duration-weighted mean of avg_logprob: (-1.0 + -2.0 + -1.5) / 3 = -1.5
    # All three durations equal -> simple mean.
    step0_segs = [
        _seg(0, 0, 100, text="alpha", avg_logprob=-1.0, repetition_ratio=0.2),
        _seg(0, 100, 200, text="beta", avg_logprob=-2.0, repetition_ratio=0.2),
        _seg(0, 200, 300, text="gamma", avg_logprob=-1.5, repetition_ratio=0.2),
    ]
    # Step 1: two segments. Duration-weighted mean avg_logprob = -0.5.
    step1_segs = [
        _seg(0, 0, 100, text="xx", avg_logprob=-0.5, repetition_ratio=0.1),
        _seg(0, 100, 200, text="yy", avg_logprob=-0.5, repetition_ratio=0.1),
    ]

    call_counter = {"n": 0}

    def joint_factory(chunk, model, language):
        n = call_counter["n"]
        call_counter["n"] += 1
        if n == 0:
            return step0_segs
        if n == 1:
            return step1_segs
        raise AssertionError("Step 2 must NOT execute")

    fw = FakeBackend(backend_name="faster-whisper", result_factory=joint_factory)
    factory = StubFactory({"faster-whisper": fw})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0, 0, 1000)],
        transcribing=[
            {"condition": "true", "backend": "faster-whisper", "model": "base"},
            {
                "condition": "avg_logprob < -1.0",
                "backend": "faster-whisper",
                "model": "medium",
            },
            {
                "condition": "repetition_ratio > 0.4",
                "backend": "faster-whisper",
                "model": "large-v3",
            },
        ],
    )
    out = stage.process(ctx)
    assert len(fw.calls) == 2  # only steps 0 and 1
    assert [r.text for r in out.transcription_results] == ["xx", "yy"]


def test_aggregate_not_persisted_on_segments() -> None:
    """Per-segment metrics on output match raw segment values, not the aggregate."""
    step0_segs = [
        _seg(0, 0, 100, avg_logprob=-1.0, repetition_ratio=0.2),
        _seg(0, 100, 200, avg_logprob=-2.0, repetition_ratio=0.2),
    ]

    fake = FakeBackend(backend_name="b0", result_factory=lambda c, m, lang: step0_segs)
    factory = StubFactory({"b0": fake})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0, 0, 1000)],
        transcribing=[{"condition": "true", "backend": "b0", "model": "m0"}],
    )
    out = stage.process(ctx)
    assert out.transcription_results[0].metrics.avg_logprob == -1.0
    assert out.transcription_results[1].metrics.avg_logprob == -2.0


def test_empty_result_list_aggregate_is_all_zeros() -> None:
    """Backend returning [] -> aggregate is all zeros; next-step condition False."""
    step0 = FakeBackend(backend_name="b0", result_factory=lambda c, m, lang: [])
    step1 = FakeBackend(backend_name="b1")
    factory = StubFactory({"b0": step0, "b1": step1})

    spy_evaluator = MagicMock(wraps=ConditionEvaluator())
    stage = TranscriptionStage(factory=factory, evaluator=spy_evaluator)  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0, 0, 1000)],
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0"},
            {"condition": "avg_logprob < -1.0", "backend": "b1", "model": "m1"},
        ],
    )
    out = stage.process(ctx)
    # Step 1 evaluated against all-zero aggregate -> 0.0 < -1.0 == False -> step 1 NOT called.
    assert len(step0.calls) == 1
    assert len(step1.calls) == 0
    assert out.transcription_results == []
    # Verify the aggregate variables passed to step 1's evaluation are all zeros.
    second_call = spy_evaluator.evaluate.call_args_list[1]
    assert second_call.args[0] == "avg_logprob < -1.0"
    assert second_call.args[1] == {
        "avg_logprob": 0.0,
        "compression_ratio": 0.0,
        "no_speech_prob": 0.0,
        "repetition_ratio": 0.0,
    }


# ---------------------------------------------------------------------------
# Task 3.3 — variables dict has exactly four keys (regression)
# ---------------------------------------------------------------------------


def test_variables_dict_exactly_four_keys_against_aggregate() -> None:
    """For step N>0, the variables dict has exactly the four metric keys (no extras)."""
    step0_segs = [
        _seg(0, 0, 100, avg_logprob=-1.5),
        _seg(0, 100, 200, avg_logprob=-1.5),
    ]
    step0 = FakeBackend(backend_name="b0", result_factory=lambda c, m, lang: step0_segs)
    step1 = FakeBackend(backend_name="b1")
    factory = StubFactory({"b0": step0, "b1": step1})

    spy_evaluator = MagicMock(wraps=ConditionEvaluator())
    stage = TranscriptionStage(factory=factory, evaluator=spy_evaluator)  # type: ignore[arg-type]

    ctx = _make_ctx(
        chunks=[_make_chunk(0, 0, 1000)],
        transcribing=[
            {"condition": "true", "backend": "b0", "model": "m0"},
            {"condition": "avg_logprob < 0.0", "backend": "b1", "model": "m1"},
        ],
    )
    stage.process(ctx)
    second_call = spy_evaluator.evaluate.call_args_list[1]
    variables = second_call.args[1]
    assert set(variables.keys()) == {
        "avg_logprob",
        "compression_ratio",
        "no_speech_prob",
        "repetition_ratio",
    }
    assert len(variables) == 4


# ---------------------------------------------------------------------------
# Task 3.4 — segment-bound invariants on stage output
# ---------------------------------------------------------------------------


def test_segment_bounds_within_parent_chunk_invariants() -> None:
    """All per-chunk segments lie within parent chunk, sorted ascending, non-overlapping."""

    def factory_fn(chunk: Chunk, model: str, language: str | None):
        # Chunk is [10000, 20000); produce three non-overlapping ascending segs.
        return [
            _seg(chunk.index, 10000, 13000, text="a"),
            _seg(chunk.index, 13000, 17000, text="b"),
            _seg(chunk.index, 17000, 20000, text="c"),
        ]

    fake = FakeBackend(backend_name="b0", result_factory=factory_fn)
    factory = StubFactory({"b0": fake})
    stage = TranscriptionStage(factory=factory, evaluator=ConditionEvaluator())  # type: ignore[arg-type]

    chunks = [_make_chunk(0, 10000, 20000)]
    ctx = _make_ctx(
        chunks=chunks,
        transcribing=[{"condition": "true", "backend": "b0", "model": "m0"}],
    )
    out = stage.process(ctx)
    parent = chunks[0]

    results_for_chunk = [r for r in out.transcription_results if r.chunk_index == 0]
    assert len(results_for_chunk) == 3

    # Each segment within parent bounds; start < end.
    for r in results_for_chunk:
        assert parent.start_ms <= r.start_ms < r.end_ms <= parent.end_ms

    # Ascending by start_ms.
    starts = [r.start_ms for r in results_for_chunk]
    assert starts == sorted(starts)

    # Non-overlapping (adjacent end <= next start).
    for i in range(len(results_for_chunk) - 1):
        assert results_for_chunk[i].end_ms <= results_for_chunk[i + 1].start_ms
