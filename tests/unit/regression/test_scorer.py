"""Unit tests for ``talking_parrot.regression.scorer``."""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path

import pytest

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.regression import score
from talking_parrot.regression import scorer as scorer_module

from tests.unit.regression._fixtures import (
    make_descriptor,
    make_result,
    make_snapshot,
)


def test_pure_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """``score`` performs no filesystem I/O."""

    def boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("score must not open files")

    monkeypatch.setattr(Path, "open", boom)
    snapshot = make_snapshot(subtitles=[Subtitle(0, 0, 1000, "hello")])
    descriptor = make_descriptor(reference_text="hello")
    card = score(snapshot, descriptor)
    assert card.sample_id == "sample1"


def test_inputs_not_mutated() -> None:
    """``score`` does not mutate snapshot or descriptor."""
    snapshot = make_snapshot(subtitles=[Subtitle(0, 0, 1000, "hello")])
    descriptor = make_descriptor(reference_text="hello")
    before_subs = list(snapshot.subtitles)
    score(snapshot, descriptor)
    assert list(snapshot.subtitles) == before_subs


def test_scorer_does_not_import_runner_cli_baseline_reporter() -> None:
    """``scorer.py`` MUST NOT import from the I/O modules."""
    src = inspect.getsource(scorer_module)
    tree = ast.parse(src)
    forbidden_modules = {
        "talking_parrot.regression.runner",
        "talking_parrot.regression.cli",
        "talking_parrot.regression.baseline",
        "talking_parrot.regression.reporter",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module not in forbidden_modules, (
                f"scorer.py imported forbidden module {node.module}"
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_modules, (
                    f"scorer.py imported forbidden module {alias.name}"
                )


def test_cer_identical_zero() -> None:
    """Identical reference and hypothesis yield CER 0.0."""
    snapshot = make_snapshot(subtitles=[Subtitle(0, 0, 1000, "hello")])
    descriptor = make_descriptor(reference_text="hello")
    card = score(snapshot, descriptor)
    assert card.metric_bundle.cer == 0.0


def test_cer_clamped() -> None:
    """CER is clamped to ``[0, 1]``."""
    snapshot = make_snapshot(
        subtitles=[Subtitle(0, 0, 1000, "completely different output")]
    )
    descriptor = make_descriptor(reference_text="x")
    card = score(snapshot, descriptor)
    assert 0.0 <= card.metric_bundle.cer <= 1.0


def test_aggregates_use_exp_logprob() -> None:
    """confidence_mean uses ``math.exp`` over avg_logprob."""
    snapshot = make_snapshot(
        subtitles=[Subtitle(0, 0, 1000, "hello")],
        transcription_results=[
            make_result(avg_logprob=-1.0),
            make_result(avg_logprob=-0.5),
        ],
    )
    descriptor = make_descriptor(reference_text="hello")
    card = score(snapshot, descriptor)
    expected = (math.exp(-1.0) + math.exp(-0.5)) / 2
    assert card.metric_bundle.confidence_mean == pytest.approx(expected)


def test_empty_results_default_zero() -> None:
    """All aggregates default to 0.0 for empty results."""
    snapshot = make_snapshot(subtitles=[], transcription_results=[])
    descriptor = make_descriptor(reference_text="x")
    card = score(snapshot, descriptor)
    assert card.metric_bundle.confidence_mean == 0.0
    assert card.metric_bundle.confidence_p10 == 0.0
    assert card.metric_bundle.no_speech_prob_mean == 0.0
    assert card.metric_bundle.repetition_ratio_mean == 0.0


def test_cue_diffs_sorted_by_index() -> None:
    """``cue_diffs`` is ordered by ascending ``index``."""
    snapshot = make_snapshot(
        subtitles=[
            Subtitle(2, 0, 100, "c"),
            Subtitle(0, 0, 100, "a"),
            Subtitle(1, 0, 100, "b"),
        ]
    )
    descriptor = make_descriptor(reference_text="abc")
    card = score(snapshot, descriptor)
    indices = [d.index for d in card.cue_diffs]
    assert indices == [0, 1, 2]
