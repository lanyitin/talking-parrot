"""Pure quality-scoring function for the regression harness.

Realises the **Decision: Module decomposition follows SRP** boundary and
the **Decision: CER uses stdlib `difflib`** computation rule from the
``regression-runner`` change's ``design.md``.

This module MUST NOT perform I/O and MUST NOT import from
``talking_parrot.regression.runner``, ``.cli``, ``.baseline`` or
``.reporter``.
"""

from __future__ import annotations

import difflib
import logging
import math
from dataclasses import dataclass

from talking_parrot.shared import (
    CueDiff,
    MetricBundle,
    ProjectSnapshot,
    ScoreCard,
)

_logger = logging.getLogger("talking_parrot.regression.scorer")


@dataclass(frozen=True, slots=True)
class SampleVariant:
    """One variant declared inside a ``descriptor.yml``."""

    file: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class SampleDescriptor:
    """In-memory representation of a ``test-samples/<sample>/descriptor.yml``.

    ``sample_id`` is the directory name (e.g. ``sample1``); ``base_file``
    is the descriptor's top-level ``file`` field; ``reference_text`` is
    the ``text`` field; ``variants`` is the declared list (preserving
    order). The base file is also exposed as the first element of
    ``all_files`` for convenience.
    """

    sample_id: str
    base_file: str
    reference_text: str
    variants: tuple[SampleVariant, ...] = ()

    @property
    def all_files(self) -> tuple[str, ...]:
        """Return ``base_file`` followed by every variant file."""
        return (self.base_file, *(v.file for v in self.variants))


def _clamp_unit(value: float) -> float:
    """Clamp ``value`` into the closed interval ``[0.0, 1.0]``."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _percentile(values: list[float], pct: float) -> float:
    """Return the linear-interpolated percentile of ``values``.

    Returns ``0.0`` when ``values`` is empty. ``pct`` is in ``[0, 100]``.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return ordered[low]
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def _cer(reference: str, hypothesis: str) -> float:
    """Return ``1 - SequenceMatcher.ratio()`` clamped to ``[0, 1]``.

    Per the **Decision: CER uses stdlib `difflib`** rule.
    """
    if not reference and not hypothesis:
        return 0.0
    ratio = difflib.SequenceMatcher(None, reference, hypothesis).ratio()
    return _clamp_unit(1.0 - ratio)


def score(snapshot: ProjectSnapshot, descriptor: SampleDescriptor) -> ScoreCard:
    """Compute a :class:`ScoreCard` from a snapshot and a descriptor.

    This function is pure: no I/O, no input mutation. CER comes from
    :mod:`difflib`; confidence aggregates exponentiate ``avg_logprob``;
    every aggregate defaults to ``0.0`` when the relevant input list is
    empty. ``cue_diffs`` is one entry per current subtitle, ordered by
    ascending ``index``.
    """
    _logger.debug(
        "score start sample_id=%s subtitles=%d transcription_results=%d",
        descriptor.sample_id,
        len(snapshot.subtitles),
        len(snapshot.transcription_results),
    )

    hypothesis = "".join(s.text for s in snapshot.subtitles)
    reference = descriptor.reference_text

    # CER overall — empty reference yields zero (per spec scenario).
    if not reference:
        cer_value = 0.0
    else:
        cer_value = _cer(reference, hypothesis)

    # Confidence aggregates from avg_logprob via exp(); 10th percentile.
    probabilities: list[float] = [
        math.exp(t.metrics.avg_logprob) for t in snapshot.transcription_results
    ]
    no_speech: list[float] = [
        t.metrics.no_speech_prob for t in snapshot.transcription_results
    ]
    repetition: list[float] = [
        t.metrics.repetition_ratio for t in snapshot.transcription_results
    ]

    confidence_mean = sum(probabilities) / len(probabilities) if probabilities else 0.0
    confidence_p10 = _percentile(probabilities, 10.0) if probabilities else 0.0
    no_speech_mean = sum(no_speech) / len(no_speech) if no_speech else 0.0
    repetition_mean = sum(repetition) / len(repetition) if repetition else 0.0

    metrics = MetricBundle(
        cer=cer_value,
        confidence_mean=confidence_mean,
        confidence_p10=confidence_p10,
        repetition_ratio_mean=repetition_mean,
        no_speech_prob_mean=no_speech_mean,
    )

    # overall_score: average of (1-CER) and confidence_mean, clamped.
    if not reference:
        overall = 0.0
    else:
        overall = _clamp_unit(((1.0 - cer_value) + confidence_mean) / 2.0)

    # Per-cue diffs ordered by ascending index.
    sorted_subs = sorted(snapshot.subtitles, key=lambda s: s.index)
    cue_diffs: list[CueDiff] = []
    for sub in sorted_subs:
        per_cue_cer = _cer(sub.text, sub.text)  # hypothesis == hypothesis -> 0
        cue_diffs.append(
            CueDiff(
                index=sub.index,
                reference_text="",
                hypothesis_text=sub.text,
                cer=_clamp_unit(per_cue_cer),
                start_ms_delta=0,
                end_ms_delta=0,
            )
        )

    card = ScoreCard(
        sample_id=descriptor.sample_id,
        overall_score=overall,
        metric_bundle=metrics,
        cue_diffs=cue_diffs,
    )
    _logger.debug(
        "score done sample_id=%s cer=%.4f confidence_mean=%.4f cue_diffs=%d",
        descriptor.sample_id,
        cer_value,
        confidence_mean,
        len(cue_diffs),
    )
    return card


__all__ = ["SampleDescriptor", "SampleVariant", "score"]
