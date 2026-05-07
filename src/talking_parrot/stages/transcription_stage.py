"""``TranscriptionStage`` — drives the cascade across ``transcribing[]`` steps.

For each ``Chunk`` in ``ctx.chunks`` the stage:

1. Iterates ``ctx.config.transcribing`` in declared order.
2. Calls ``ConditionEvaluator.evaluate(step.condition, latest_metrics)``;
   on falsy result it stops the cascade for the current chunk.
3. On truthy result it resolves ``factory.create(step.backend)`` and calls
   ``backend.transcribe(...)``, replacing the running result.
4. Bounded fallback: if a non-step-0 backend raises, the stage logs a WARNING
   and keeps the prior result. Step-0 failures propagate.
"""

from __future__ import annotations

import dataclasses
import structlog
from typing import TYPE_CHECKING, Any

from talking_parrot.models.transcription import TranscriptionResult
from talking_parrot.stages.base import PipelineStage

if TYPE_CHECKING:
    from talking_parrot.expression.condition import ConditionEvaluator
    from talking_parrot.models.context import PipelineContext
    from talking_parrot.transcription.factory import TranscriptionBackendFactory

logger = structlog.get_logger(__name__)


class TranscriptionStage(PipelineStage):
    """Pipeline stage that produces one ``TranscriptionResult`` per ``Chunk``.

    The stage drives a cascade across ``ctx.config.transcribing`` for each
    chunk. Each step runs at most once per chunk; the chunk's final result is
    the output of the last step that ran successfully.
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
        whose ``transcription_results`` is the original list extended by one
        ``TranscriptionResult`` per chunk in input order.
        """
        if not ctx.chunks:
            logger.debug("TranscriptionStage: empty chunks, returning ctx unchanged")
            return ctx

        new_results: list[TranscriptionResult] = []
        for chunk in ctx.chunks:
            result = self._process_chunk(ctx, chunk)
            new_results.append(result)

        return dataclasses.replace(
            ctx,
            transcription_results=[*ctx.transcription_results, *new_results],
        )

    def _process_chunk(self, ctx: "PipelineContext", chunk: Any) -> TranscriptionResult:
        """Drive the cascade for a single chunk and return its final result.

        Raises whatever exception step 0's backend raises. Non-step-0 backend
        exceptions are caught, logged at WARNING, and break the cascade for
        the current chunk while preserving the previous step's result.
        """
        latest_result: TranscriptionResult | None = None
        latest_metrics: dict[str, Any] = {}

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
                result = backend.transcribe(
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
                    result = backend.transcribe(
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

            latest_result = result
            latest_metrics = _metrics_to_dict(result.metrics)

        # Step 0 always runs (its condition is the literal "true" enforced by
        # ConfigLoader), so latest_result is never None when we reach this
        # line under normal operation.
        assert latest_result is not None, (
            "TranscriptionStage: step 0 must always run (ConfigLoader enforces "
            "transcribing[0].condition == 'true')"
        )
        return latest_result


def _metrics_to_dict(metrics: Any) -> dict[str, Any]:
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
