"""Unit tests for ``talking_parrot.regression.cli``."""

from __future__ import annotations

from pathlib import Path

import pytest

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.shared import MetricBundle, ProjectSnapshot, ScoreCard

from talking_parrot.regression import cli as cli_module
from talking_parrot.regression.cli import main, parse_args

from tests.unit.regression._fixtures import make_snapshot


def _write_descriptor(
    samples_dir: Path,
    sample_id: str,
    *,
    text: str,
    create_audio: bool = True,
) -> None:
    sample_dir = samples_dir / sample_id
    sample_dir.mkdir(parents=True)
    (sample_dir / "descriptor.yml").write_text(
        f"file: base.mp3\ntext: {text}\nvariants: []\n", encoding="utf-8"
    )
    if create_audio:
        (sample_dir / "base.mp3").write_bytes(b"")


def test_flags_parsed() -> None:
    """All documented CLI flags are parsed."""
    config = parse_args(
        [
            "--samples-dir",
            "/tmp/s",
            "--results-dir",
            "/tmp/r",
            "--label",
            "L",
            "--reset-baseline",
            "--cer-tolerance",
            "0.10",
            "--confidence-tolerance",
            "0.20",
            "--strict-missing",
        ]
    )
    assert config.samples_dir == Path("/tmp/s")
    assert config.results_dir == Path("/tmp/r")
    assert config.label == "L"
    assert config.reset_baseline is True
    assert config.cer_tolerance == 0.10
    assert config.confidence_tolerance == 0.20
    assert config.strict_missing is True


def test_exit_two_on_missing_samples_dir(tmp_path: Path) -> None:
    """A non-existent ``--samples-dir`` exits 2."""
    code = main(
        [
            "--samples-dir",
            str(tmp_path / "does-not-exist"),
            "--results-dir",
            str(tmp_path / "out"),
        ]
    )
    assert code == 2


class _StubStore:
    """Configurable in-memory :class:`BaselineStore`."""

    def __init__(self, baseline_card: ScoreCard | None = None) -> None:
        self._baseline_card = baseline_card
        self.saved: dict[str, ScoreCard] = {}

    def load(self, sample_id: str) -> ScoreCard | None:
        return self._baseline_card

    def save(self, sample_id: str, card: ScoreCard) -> None:
        self.saved[sample_id] = card


def _runner_factory_returning(snapshot: ProjectSnapshot):
    def _factory():
        def _runner(_dir: Path, _variant: str) -> ProjectSnapshot:
            return snapshot

        return _runner

    return _factory


def test_exit_zero_when_stable(tmp_path: Path) -> None:
    """All samples stable → exit 0."""
    _write_descriptor(tmp_path, "sample1", text="hello")
    snapshot = make_snapshot(subtitles=[Subtitle(0, 0, 1000, "hello")])
    # No transcription_results in the snapshot ⇒ confidence_mean = 0.0
    # so a baseline confidence_mean = 0.0 yields a "stable" verdict.
    baseline = ScoreCard(
        sample_id="sample1",
        overall_score=0.0,
        metric_bundle=MetricBundle(
            cer=0.0,
            confidence_mean=0.0,
            confidence_p10=0.0,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.0,
        ),
    )
    code = main(
        [
            "--samples-dir",
            str(tmp_path),
            "--results-dir",
            str(tmp_path / "out"),
        ],
        pipeline_runner_factory=_runner_factory_returning(snapshot),
        baseline_store=_StubStore(baseline_card=baseline),
    )
    assert code == 0


def test_exit_one_when_regressed(tmp_path: Path) -> None:
    """A regressed sample drives exit 1."""
    _write_descriptor(tmp_path, "sample1", text="reference text")
    snapshot = make_snapshot(
        subtitles=[Subtitle(0, 0, 1000, "completely different output")]
    )
    baseline = ScoreCard(
        sample_id="sample1",
        overall_score=0.0,
        metric_bundle=MetricBundle(
            cer=0.0,
            confidence_mean=0.9,
            confidence_p10=0.0,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.0,
        ),
    )
    code = main(
        [
            "--samples-dir",
            str(tmp_path),
            "--results-dir",
            str(tmp_path / "out"),
        ],
        pipeline_runner_factory=_runner_factory_returning(snapshot),
        baseline_store=_StubStore(baseline_card=baseline),
    )
    assert code == 1


def test_reset_baseline_overrides_verdicts(tmp_path: Path) -> None:
    """``--reset-baseline`` forces every verdict to bootstrapped and exit 0."""
    _write_descriptor(tmp_path, "sample1", text="reference")
    snapshot = make_snapshot(
        subtitles=[Subtitle(0, 0, 1000, "very different output text")]
    )
    # Existing baseline with CER 0.01 — current is much worse.
    baseline = ScoreCard(
        sample_id="sample1",
        overall_score=0.0,
        metric_bundle=MetricBundle(
            cer=0.01,
            confidence_mean=0.9,
            confidence_p10=0.0,
            repetition_ratio_mean=0.0,
            no_speech_prob_mean=0.0,
        ),
    )
    store = _StubStore(baseline_card=baseline)
    code = main(
        [
            "--samples-dir",
            str(tmp_path),
            "--results-dir",
            str(tmp_path / "out"),
            "--reset-baseline",
        ],
        pipeline_runner_factory=_runner_factory_returning(snapshot),
        baseline_store=store,
    )
    assert code == 0
    # Stored baseline was overwritten.
    assert "sample1" in store.saved


def test_module_attribute_main_exists() -> None:
    """Defensive: ``main`` is importable from ``cli``."""
    assert callable(cli_module.main)


def test_internal_exit_code_helper_signals_regressed() -> None:
    """The verdict→exit-code helper returns 1 for any regressed verdict."""
    assert (
        cli_module._exit_code_for_verdicts(
            ["stable", "regressed"], strict_missing=False
        )
        == 1
    )


@pytest.fixture(autouse=True)
def _reset_logging_handlers() -> None:
    """Tests should not leak logging handlers."""
    yield
    logger = cli_module._logger
    for h in list(logger.handlers):
        logger.removeHandler(h)
