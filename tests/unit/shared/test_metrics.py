"""Tests for ``ScoreCard``, ``MetricBundle``, and ``CueDiff``."""

from __future__ import annotations

import dataclasses
import inspect

import pytest

from talking_parrot.shared import metrics as metrics_module
from talking_parrot.shared.metrics import CueDiff, MetricBundle, ScoreCard


def _bundle() -> MetricBundle:
    return MetricBundle(
        cer=0.1,
        confidence_mean=0.9,
        confidence_p10=0.7,
        repetition_ratio_mean=0.0,
        no_speech_prob_mean=0.05,
    )


def test_metric_bundle_required_fields() -> None:
    mb = _bundle()
    assert mb.cer == 0.1
    assert mb.confidence_mean == 0.9
    assert mb.confidence_p10 == 0.7
    assert mb.repetition_ratio_mean == 0.0
    assert mb.no_speech_prob_mean == 0.05


def test_metric_bundle_frozen() -> None:
    mb = _bundle()
    with pytest.raises(dataclasses.FrozenInstanceError):
        mb.cer = 0.2  # type: ignore[misc]


def test_cue_diff_carries_reference_and_hypothesis() -> None:
    diff = CueDiff(
        index=0,
        reference_text="hello",
        hypothesis_text="hallo",
        cer=0.2,
        start_ms_delta=5,
        end_ms_delta=-3,
    )
    assert diff.reference_text == "hello"
    assert diff.hypothesis_text == "hallo"


def test_score_card_default_cue_diffs_empty() -> None:
    card = ScoreCard(sample_id="sample1", overall_score=0.0, metric_bundle=_bundle())
    assert card.cue_diffs == []


def test_score_card_frozen() -> None:
    card = ScoreCard(sample_id="sample1", overall_score=0.0, metric_bundle=_bundle())
    with pytest.raises(dataclasses.FrozenInstanceError):
        card.overall_score = 1.0  # type: ignore[misc]


def test_module_exposes_only_dataclasses() -> None:
    """No callable that computes scores SHALL be present in metrics module."""
    public_names = [n for n in dir(metrics_module) if not n.startswith("_")]
    allowed_dataclasses = {"ScoreCard", "MetricBundle", "CueDiff"}

    for name in public_names:
        obj = getattr(metrics_module, name)
        if name in allowed_dataclasses:
            assert dataclasses.is_dataclass(obj), f"{name} must be a dataclass"
            continue
        # Permit re-exports from the typing/dataclasses modules but disallow
        # functions defined in this module.
        if inspect.isfunction(obj) and obj.__module__ == metrics_module.__name__:
            raise AssertionError(
                f"metrics module must not define scoring functions; found {name}"
            )
