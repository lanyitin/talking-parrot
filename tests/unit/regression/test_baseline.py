"""Unit tests for ``talking_parrot.regression.baseline``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from talking_parrot.shared import CueDiff, MetricBundle, ScoreCard

from talking_parrot.regression import (
    BaselineSchemaError,
    BaselineStore,
    JsonBaselineStore,
)


def _card(*, with_diffs: bool = False) -> ScoreCard:
    diffs: list[CueDiff] = []
    if with_diffs:
        diffs = [
            CueDiff(
                index=0,
                reference_text="ref-a",
                hypothesis_text="hyp-a",
                cer=0.1,
                start_ms_delta=10,
                end_ms_delta=20,
            ),
            CueDiff(
                index=1,
                reference_text="ref-b",
                hypothesis_text="hyp-b",
                cer=0.2,
                start_ms_delta=-5,
                end_ms_delta=15,
            ),
        ]
    return ScoreCard(
        sample_id="sample1",
        overall_score=0.87,
        metric_bundle=MetricBundle(
            cer=0.04,
            confidence_mean=0.82,
            confidence_p10=0.61,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.05,
        ),
        cue_diffs=diffs,
    )


def test_protocol_runtime_checkable() -> None:
    """A duck-typed double satisfies :class:`BaselineStore`."""

    class Double:
        def load(self, sample_id: str) -> ScoreCard | None:
            return None

        def save(self, sample_id: str, card: ScoreCard) -> None:
            return None

    assert isinstance(Double(), BaselineStore)


def test_save_atomic_replace(tmp_path: Path) -> None:
    """``save`` writes the final file and leaves no ``.tmp`` behind."""
    store = JsonBaselineStore(tmp_path)
    store.save("sample1", _card())
    final_path = tmp_path / "sample1" / "baseline.json"
    assert final_path.exists()
    leftovers = list((tmp_path / "sample1").glob("*.tmp"))
    assert leftovers == []


def test_round_trip_preserves_cue_diffs(tmp_path: Path) -> None:
    """A saved card with two cue diffs round-trips identically."""
    store = JsonBaselineStore(tmp_path)
    original = _card(with_diffs=True)
    store.save("sample1", original)
    loaded = store.load("sample1")
    assert loaded == original


def test_empty_cue_diffs_present(tmp_path: Path) -> None:
    """An empty ``cue_diffs`` is serialised as ``[]`` (not omitted)."""
    store = JsonBaselineStore(tmp_path)
    store.save("sample1", _card(with_diffs=False))
    final_path = tmp_path / "sample1" / "baseline.json"
    payload = json.loads(final_path.read_text(encoding="utf-8"))
    assert payload["score_card"]["cue_diffs"] == []


def test_load_missing_returns_none(tmp_path: Path) -> None:
    """``load`` returns ``None`` for an unknown sample."""
    store = JsonBaselineStore(tmp_path)
    assert store.load("never-saved") is None


def test_load_unknown_schema_raises(tmp_path: Path) -> None:
    """``load`` raises :class:`BaselineSchemaError` for unknown schema."""
    sample_dir = tmp_path / "sample1"
    sample_dir.mkdir(parents=True)
    (sample_dir / "baseline.json").write_text(
        json.dumps({"schema_version": 999, "score_card": {}}),
        encoding="utf-8",
    )
    store = JsonBaselineStore(tmp_path)
    with pytest.raises(BaselineSchemaError):
        store.load("sample1")
