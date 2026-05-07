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
    ) -> TranscriptionResult:
        """Record the call and either raise or return a parametrised result."""
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
            return self._result_factory(chunk, model, language)
        # Default: deterministic well-formed result.
        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text=f"text-{chunk.index}-{model}",
            language=language or "en",
            model_used=model,
            metrics=TranscriptionMetrics(0.0, 0.0, 0.0, 0.0),
            aligned_tokens=None,
        )


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
