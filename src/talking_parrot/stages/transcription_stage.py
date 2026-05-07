"""``TranscriptionStage`` — drives the cascade across ``transcribing[]`` steps.

For each ``Chunk`` in ``ctx.chunks`` the stage:

1. Iterates ``ctx.config.transcribing`` in declared order.
2. Calls ``ConditionEvaluator.evaluate(step.condition, latest_metrics)`` where
   ``latest_metrics`` is a chunk-level aggregate computed locally from the
   running step's per-segment results. On falsy result it stops the cascade
   for the current chunk.
3. On truthy result it resolves ``factory.create(step.backend)`` and calls
   ``backend.transcribe(...)``, replacing the running per-segment list.
4. Bounded fallback: if a non-step-0 backend raises, the stage logs a WARNING
   and keeps the prior step's running list. Step-0 failures propagate.

After the cascade for a chunk completes, the per-segment results from the
winning backend are extended into ``ctx.transcription_results``. The
chunk-level aggregate is never persisted on any ``TranscriptionResult``; it
exists solely for cascade condition evaluation.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import structlog

from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.stages.base import PipelineStage

if TYPE_CHECKING:
    from talking_parrot.expression.condition import ConditionEvaluator
    from talking_parrot.models.context import PipelineContext
    from talking_parrot.transcription.factory import TranscriptionBackendFactory

logger = structlog.get_logger(__name__)


class TranscriptionStage(PipelineStage):
    """Pipeline stage that produces per-segment ``TranscriptionResult`` rows.

    The stage drives a cascade across ``ctx.config.transcribing`` for each
    chunk. Each step runs at most once per chunk; the chunk's final results
    are the per-segment outputs of the last step that ran successfully.
    """

    def __init__(
        self,
        factory: "TranscriptionBackendFactory",
        evaluator: "ConditionEvaluator",
    ) -> None:
        """Store the dependencies; no work is done at construction time."""
        self._factory = factory
        self._evaluator = evaluator

    @property
    def name(self) -> str:
        """Return the stage name."""
        return "transcription"

    def process(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run the cascade across all chunks and return an updated context.

        Returns the input context unchanged when ``ctx.chunks`` is empty.
        Otherwise returns a new ``PipelineContext`` (via ``dataclasses.replace``)
        whose ``transcription_results`` is the original list extended by the
        per-segment results of every chunk in input order.
        """
        if not ctx.chunks:
            logger.debug("TranscriptionStage: empty chunks, returning ctx unchanged")
            return ctx

        new_results: list[TranscriptionResult] = []
        for chunk in ctx.chunks:
            chunk_results = self._process_chunk(ctx, chunk)
            new_results.extend(chunk_results)

        return dataclasses.replace(
            ctx,
            transcription_results=[*ctx.transcription_results, *new_results],
        )

    def _process_chunk(
        self, ctx: "PipelineContext", chunk: Any
    ) -> list[TranscriptionResult]:
        """Drive the cascade for a single chunk and return its final per-segment list.

        Raises whatever exception step 0's backend raises. Non-step-0 backend
        exceptions are caught, logged at WARNING, and break the cascade for
        the current chunk while preserving the previous step's running list.
        """
        running_results: list[TranscriptionResult] = []
        latest_metrics: dict[str, float] = {}

        for idx, step in enumerate(ctx.config.transcribing):
            if idx == 0:
                # Per the transcription-stage spec, the evaluator MUST be
                # called with ``expression="true"`` and ``variables={}`` for
                # step 0, AND step 0 always runs (its condition is the literal
                # ``"true"`` enforced by ConfigLoader). The call is performed
                # for observability; any error is swallowed because step 0 is
                # unconditional.
                try:
                    self._evaluator.evaluate(step.condition, latest_metrics)
                except Exception:
                    logger.debug(
                        "TranscriptionStage: step 0 evaluator raised; "
                        "step 0 always runs regardless",
                        condition=step.condition,
                        chunk_index=chunk.index,
                    )
            else:
                condition_value = self._evaluator.evaluate(
                    step.condition, latest_metrics
                )
                if not condition_value:
                    logger.debug(
                        "TranscriptionStage: cascade halted on falsy condition",
                        chunk_index=chunk.index,
                        step_index=idx,
                        condition=step.condition,
                    )
                    break

            assert (
                step.backend is not None
            )  # filled by ConfigLoader._resolve_transcribing_backends
            backend = self._factory.create(step.backend)
            language = step.language or ctx.config.expected_language

            if idx == 0:
                # Step 0 exceptions propagate — no prior result to fall back to.
                logger.debug(
                    "TranscriptionStage: invoking step 0 backend",
                    chunk_index=chunk.index,
                    backend=step.backend,
                    model=step.model,
                )
                step_results = backend.transcribe(
                    ctx.media_info.path, chunk, step.model, language
                )
            else:
                try:
                    logger.debug(
                        "TranscriptionStage: invoking cascade step backend",
                        chunk_index=chunk.index,
                        step_index=idx,
                        backend=step.backend,
                        model=step.model,
                    )
                    step_results = backend.transcribe(
                        ctx.media_info.path, chunk, step.model, language
                    )
                except Exception as exc:
                    logger.warning(
                        "transcription step failed",
                        step_index=idx,
                        backend=step.backend,
                        model=step.model,
                        error=type(exc).__name__,
                    )
                    break

            assert isinstance(step_results, list), (
                f"TranscriptionBackend.transcribe must return list[TranscriptionResult], "
                f"got {type(step_results)!r}. Check whether the backend was updated to "
                "the per-segment contract."
            )
            logger.debug(
                "TranscriptionStage: backend returned segment results",
                chunk_index=chunk.index,
                step_index=idx,
                segment_count=len(step_results),
            )

            running_results = step_results
            aggregate = _aggregate_metrics(running_results)
            latest_metrics = _metrics_to_dict(aggregate)

        return running_results


def _aggregate_metrics(
    results: list[TranscriptionResult],
) -> TranscriptionMetrics:
    """Compute the chunk-level cascade aggregate over a list of segment results.

    Rules (from the ``transcription-stage`` spec, "Cascade aggregate"):

    - ``avg_logprob`` = duration-weighted mean of segment ``avg_logprob``.
    - ``compression_ratio`` = duration-weighted mean of segment
      ``compression_ratio``.
    - ``no_speech_prob`` = max of segment ``no_speech_prob``.
    - ``repetition_ratio`` = ``1 - unique_tokens / total_tokens`` over the
      whitespace-split concatenation of segment texts joined by single space.
      ``0.0`` when ``total_tokens == 0``.
    - When ``results`` is empty, all four fields are ``0.0``.
    """
    if not results:
        return TranscriptionMetrics(
            avg_logprob=0.0,
            compression_ratio=0.0,
            no_speech_prob=0.0,
            repetition_ratio=0.0,
        )

    durations = [max(0, r.end_ms - r.start_ms) for r in results]
    total_duration = sum(durations)

    if total_duration > 0:
        avg_logprob = (
            sum(r.metrics.avg_logprob * d for r, d in zip(results, durations))
            / total_duration
        )
        compression_ratio = (
            sum(r.metrics.compression_ratio * d for r, d in zip(results, durations))
            / total_duration
        )
    else:
        # All zero-duration segments — fall back to plain mean to avoid
        # division by zero, but keep the value defined.
        avg_logprob = 0.0
        compression_ratio = 0.0

    no_speech_prob = max(r.metrics.no_speech_prob for r in results)

    joined_text = " ".join(r.text for r in results)
    tokens = joined_text.split()
    total_tokens = len(tokens)
    if total_tokens == 0:
        repetition_ratio = 0.0
    else:
        unique_tokens = len(set(tokens))
        repetition_ratio = 1.0 - (unique_tokens / total_tokens)

    return TranscriptionMetrics(
        avg_logprob=float(avg_logprob),
        compression_ratio=float(compression_ratio),
        no_speech_prob=float(no_speech_prob),
        repetition_ratio=float(repetition_ratio),
    )


def _metrics_to_dict(metrics: TranscriptionMetrics) -> dict[str, float]:
    """Project ``TranscriptionMetrics`` to the exact 4-key dict for the evaluator.

    No other state is exposed to the evaluator (per the
    ``transcription-stage`` spec).
    """
    return {
        "avg_logprob": metrics.avg_logprob,
        "compression_ratio": metrics.compression_ratio,
        "no_speech_prob": metrics.no_speech_prob,
        "repetition_ratio": metrics.repetition_ratio,
    }
