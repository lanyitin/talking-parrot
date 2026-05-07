"""``HallucinationFilterStage`` — drops Whisper hallucinations after transcription.

The stage consumes ``ctx.transcription_results`` (one
:class:`TranscriptionResult` per Whisper segment after task 2/3) and returns a
new :class:`PipelineContext` whose ``transcription_results`` has all
hallucinated rows removed.

Six rules, each independently toggleable via the corresponding
:class:`HallucinationFilterConfig` field, are evaluated in this fixed order
(first match wins):

1. ``phrase``      — exact match against ``known_hallucination_phrases``.
2. ``bracket``     — text wholly wrapped in ASCII or full-width brackets.
3. ``repeat``      — five or more consecutive identical non-whitespace chars.
4. ``low_logprob`` — ``avg_logprob < min_avg_logprob`` AND
                     ``no_speech_prob > max_no_speech_prob``.
5. ``compression`` — ``compression_ratio > max_compression_ratio``.
6. ``repetition``  — ``repetition_ratio > max_repetition_ratio``.

When ``enabled`` is ``False``, the stage returns a new context whose
``transcription_results`` is reference-equal to the input's and emits no
summary log line.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

import structlog

from talking_parrot.stages.base import PipelineStage

if TYPE_CHECKING:
    from talking_parrot.config.models import HallucinationFilterConfig
    from talking_parrot.models.context import PipelineContext
    from talking_parrot.models.transcription import TranscriptionResult

logger = structlog.get_logger(__name__)

# Module-level compiled regexes — compile once, reuse for the lifetime of the
# process. The bracket regex matches the *entire* stripped text (anchored).
_BRACKET_RE = re.compile(r"^[\[\(（【][^\]\)）】]*[\]\)）】]$")
_REPEAT_RE = re.compile(r"(\S)\1{4,}")


class HallucinationFilterStage(PipelineStage):
    """Pipeline stage that drops hallucinated transcription results."""

    def __init__(self, config: "HallucinationFilterConfig") -> None:
        """Store the config; no work is done at construction time."""
        self._config = config

    @property
    def name(self) -> str:
        """Return the stage name."""
        return "hallucination_filter"

    def process(self, ctx: "PipelineContext") -> "PipelineContext":
        """Filter ``ctx.transcription_results`` by the configured rules.

        Returns a new :class:`PipelineContext` (via ``dataclasses.replace``).
        When the stage is disabled, the new context's ``transcription_results``
        is reference-equal to the input's, and no INFO summary log is emitted.
        """
        cfg = self._config
        if not cfg.enabled:
            logger.debug(
                "HallucinationFilterStage: disabled — returning context unchanged"
            )
            return dataclasses.replace(ctx)

        before = len(ctx.transcription_results)
        kept: list[TranscriptionResult] = []
        for result in ctx.transcription_results:
            rule = self._match_rule(result)
            if rule is None:
                kept.append(result)
                continue
            logger.debug(
                "HallucinationFilterStage: dropping result",
                chunk_index=result.chunk_index,
                rule=rule,
            )

        after = len(kept)
        dropped = before - after
        logger.info(
            "HallucinationFilterStage: filter summary",
            before=before,
            after=after,
            dropped=dropped,
        )

        return dataclasses.replace(ctx, transcription_results=kept)

    # ------------------------------------------------------------------
    # Rule evaluation
    # ------------------------------------------------------------------

    def _match_rule(self, result: "TranscriptionResult") -> str | None:
        """Return the first matching rule's name or ``None`` if no rule fires.

        Rules are evaluated in spec order; each rule is gated on its
        ``*_match_enabled`` toggle so a disabled rule MUST NOT contribute to a
        drop decision.
        """
        cfg = self._config
        text = result.text
        stripped = text.strip()

        if cfg.phrase_match_enabled and stripped in cfg.known_hallucination_phrases:
            return "phrase"

        if cfg.bracket_match_enabled and _BRACKET_RE.match(stripped):
            return "bracket"

        if cfg.repeat_match_enabled and _REPEAT_RE.search(text):
            return "repeat"

        metrics = result.metrics
        if (
            cfg.low_logprob_match_enabled
            and metrics.avg_logprob < cfg.min_avg_logprob
            and metrics.no_speech_prob > cfg.max_no_speech_prob
        ):
            return "low_logprob"

        if (
            cfg.compression_match_enabled
            and metrics.compression_ratio > cfg.max_compression_ratio
        ):
            return "compression"

        if (
            cfg.repetition_match_enabled
            and metrics.repetition_ratio > cfg.max_repetition_ratio
        ):
            return "repetition"

        return None
