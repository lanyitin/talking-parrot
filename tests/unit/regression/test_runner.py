"""Unit tests for ``talking_parrot.regression.runner``."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.shared import MetricBundle, ProjectSnapshot, ScoreCard

from talking_parrot.regression import (
    RegressionRunner,
    SampleVariant,
    compute_verdict,
    discover_samples,
)

from tests.unit.regression._fixtures import make_snapshot


def _write_descriptor(
    samples_dir: Path,
    sample_id: str,
    *,
    base_file: str,
    text: str,
    variants: list[SampleVariant],
    create_audio_for: list[str] | None = None,
) -> None:
    sample_dir = samples_dir / sample_id
    sample_dir.mkdir(parents=True)
    yml_lines = [
        f"file: {base_file}",
        f"text: {text}",
        "variants:",
    ]
    for v in variants:
        yml_lines.append(f"  - file: {v.file}")
        yml_lines.append(f"    description: {v.description}")
    (sample_dir / "descriptor.yml").write_text(
        "\n".join(yml_lines) + "\n", encoding="utf-8"
    )
    for af in create_audio_for or []:
        (sample_dir / af).write_bytes(b"")


def test_discover_samples_orders_variants(tmp_path: Path) -> None:
    """``discover_samples`` preserves declared variant order, length 2."""
    _write_descriptor(
        tmp_path,
        "sample1",
        base_file="base.mp3",
        text="hello",
        variants=[
            SampleVariant(file="quiet.mp3", description="quiet"),
            SampleVariant(file="loud.mp3", description="loud"),
        ],
    )
    descriptors = discover_samples(tmp_path)
    assert len(descriptors) == 1
    desc = descriptors[0]
    assert desc.sample_id == "sample1"
    assert desc.base_file == "base.mp3"
    assert desc.reference_text == "hello"
    assert len(desc.variants) == 2
    assert [v.file for v in desc.variants] == ["quiet.mp3", "loud.mp3"]


class _StubBaselineStore:
    """In-memory :class:`BaselineStore` for tests."""

    def __init__(self) -> None:
        self.cards: dict[str, ScoreCard] = {}

    def load(self, sample_id: str) -> ScoreCard | None:
        return self.cards.get(sample_id)

    def save(self, sample_id: str, card: ScoreCard) -> None:
        self.cards[sample_id] = card


class _ConstructionCountingFactory:
    """Pipeline runner factory that records its construction count."""

    def __init__(self, snapshot: ProjectSnapshot) -> None:
        self.snapshot = snapshot
        self.constructions = 0

    def __call__(self):
        self.constructions += 1

        def _runner(sample_dir: Path, variant_file: str) -> ProjectSnapshot:
            return self.snapshot

        return _runner


def _fixed_clock() -> _dt.datetime:
    return _dt.datetime(2026, 5, 9, 12, 0, 0, tzinfo=_dt.UTC)


def test_orchestrator_constructed_once(tmp_path: Path) -> None:
    """The pipeline runner factory is invoked exactly once across variants."""
    _write_descriptor(
        tmp_path,
        "sample1",
        base_file="base.mp3",
        text="hello",
        variants=[
            SampleVariant(file="quiet.mp3"),
            SampleVariant(file="loud.mp3"),
        ],
        create_audio_for=["base.mp3", "quiet.mp3", "loud.mp3"],
    )
    snapshot = make_snapshot(subtitles=[Subtitle(0, 0, 1000, "hello")])
    factory = _ConstructionCountingFactory(snapshot)
    runner = RegressionRunner(
        samples_dir=tmp_path,
        baseline_store=_StubBaselineStore(),
        pipeline_runner_factory=factory,
        clock=_fixed_clock,
    )
    runner.run_all()
    assert factory.constructions == 1


def test_missing_audio_skipped_default(tmp_path: Path) -> None:
    """Missing audio yields verdict ``skipped`` and never errors out."""
    _write_descriptor(
        tmp_path,
        "sample1",
        base_file="base.mp3",
        text="hello",
        variants=[],  # no audio file written
    )
    snapshot = make_snapshot(subtitles=[Subtitle(0, 0, 1000, "hello")])
    factory = _ConstructionCountingFactory(snapshot)
    runner = RegressionRunner(
        samples_dir=tmp_path,
        baseline_store=_StubBaselineStore(),
        pipeline_runner_factory=factory,
        clock=_fixed_clock,
    )
    _, results = runner.run_all()
    assert all(r.verdict == "skipped" for r in results)


def test_missing_audio_strict_exits_one(tmp_path: Path) -> None:
    """When ``--strict-missing`` is set, missing audio drives exit code 1."""
    from talking_parrot.regression.cli import _exit_code_for_verdicts

    code = _exit_code_for_verdicts(["skipped"], strict_missing=True)
    assert code == 1
    code = _exit_code_for_verdicts(["skipped"], strict_missing=False)
    assert code == 0


def test_cer_above_tolerance_regressed() -> None:
    """Baseline CER 0.04, current 0.10, tolerance 0.02 → regressed."""
    baseline = ScoreCard(
        sample_id="s",
        overall_score=0.0,
        metric_bundle=MetricBundle(
            cer=0.04,
            confidence_mean=0.9,
            confidence_p10=0.0,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.0,
        ),
    )
    current = ScoreCard(
        sample_id="s",
        overall_score=0.0,
        metric_bundle=MetricBundle(
            cer=0.10,
            confidence_mean=0.9,
            confidence_p10=0.0,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.0,
        ),
    )
    assert (
        compute_verdict(
            current=current,
            baseline=baseline,
            cer_tolerance=0.02,
            confidence_tolerance=0.05,
        )
        == "regressed"
    )


def test_confidence_drop_above_tolerance_regressed() -> None:
    """Confidence drop 0.10 > tolerance 0.05 → regressed."""
    baseline = ScoreCard(
        sample_id="s",
        overall_score=0.0,
        metric_bundle=MetricBundle(
            cer=0.04,
            confidence_mean=0.90,
            confidence_p10=0.0,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.0,
        ),
    )
    current = ScoreCard(
        sample_id="s",
        overall_score=0.0,
        metric_bundle=MetricBundle(
            cer=0.04,
            confidence_mean=0.80,
            confidence_p10=0.0,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.0,
        ),
    )
    assert (
        compute_verdict(
            current=current,
            baseline=baseline,
            cer_tolerance=0.02,
            confidence_tolerance=0.05,
        )
        == "regressed"
    )
