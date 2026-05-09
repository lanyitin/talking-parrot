"""Empty-shape value objects used by future regression scoring.

This module declares only field shapes — ``ScoreCard``, ``MetricBundle``,
``CueDiff``. Scoring algorithms (CER, confidence aggregation, etc.) belong to
a future regression-runner change and MUST NOT be added here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricBundle:
    """Aggregate quality metrics computed for one transcribed sample."""

    cer: float
    confidence_mean: float
    confidence_p10: float
    repetition_ratio_mean: float
    no_speech_prob_mean: float


@dataclass(frozen=True)
class CueDiff:
    """Per-cue diff between reference and hypothesis subtitle entries."""

    index: int
    reference_text: str
    hypothesis_text: str
    cer: float
    start_ms_delta: int
    end_ms_delta: int


@dataclass(frozen=True)
class ScoreCard:
    """Top-level regression score record for one sample."""

    sample_id: str
    overall_score: float
    metric_bundle: MetricBundle
    cue_diffs: list[CueDiff] = field(default_factory=list)
