"""End-to-end integration test for the regression runner.

Realises the **Decision: Module decomposition follows SRP** wiring
end-to-end via a stub orchestrator and a fixture
:class:`BaselineStore`. No real audio is touched.
"""

from __future__ import annotations

import json
from pathlib import Path

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.shared import (
    AudioInfo,
    MetricBundle,
    ProjectSnapshot,
    ScoreCard,
)

from talking_parrot.regression.cli import main


def _make_snapshot(text: str) -> ProjectSnapshot:
    return ProjectSnapshot(
        version="1",
        created_at="2026-05-09T00:00:00Z",
        source_path="",
        config_snapshot={},
        audio_info=AudioInfo(
            sample_rate=16000, duration_ms=0, rms_mean=0.0, rms_peak=0.0
        ),
        vad_frames=[],
        vad_segments=[],
        chunks=[],
        transcription_results=[
            TranscriptionResult(
                chunk_index=0,
                start_ms=0,
                end_ms=1000,
                text=text,
                language="ja",
                model_used="test",
                metrics=TranscriptionMetrics(
                    avg_logprob=-0.1,
                    compression_ratio=1.0,
                    no_speech_prob=0.05,
                    repetition_ratio=0.0,
                ),
            )
        ],
        pre_postprocess_subtitles=[],
        subtitles=[Subtitle(0, 0, 1000, text)],
    )


class _InMemoryBaselineStore:
    def __init__(self) -> None:
        self.cards: dict[str, ScoreCard] = {}

    def load(self, sample_id: str) -> ScoreCard | None:
        return self.cards.get(sample_id)

    def save(self, sample_id: str, card: ScoreCard) -> None:
        self.cards[sample_id] = card


def test_runner_with_fixture_snapshot(tmp_path: Path) -> None:
    """End-to-end happy path produces JSON + HTML and exit code 0."""
    samples_dir = tmp_path / "samples"
    sample_dir = samples_dir / "sample1"
    sample_dir.mkdir(parents=True)
    (sample_dir / "descriptor.yml").write_text(
        "file: base.mp3\ntext: hello\nvariants: []\n", encoding="utf-8"
    )
    (sample_dir / "base.mp3").write_bytes(b"")

    snapshot = _make_snapshot("hello")

    def _factory():
        def _runner(_dir: Path, _variant: str) -> ProjectSnapshot:
            return snapshot

        return _runner

    # Pre-seed a matching baseline so the verdict is "stable".
    seed_card = ScoreCard(
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
    store = _InMemoryBaselineStore()
    store.cards["sample1"] = seed_card

    results_dir = tmp_path / "results"
    code = main(
        [
            "--samples-dir",
            str(samples_dir),
            "--results-dir",
            str(results_dir),
        ],
        pipeline_runner_factory=_factory,
        baseline_store=store,
    )
    assert code == 0
    json_path = results_dir / "latest.json"
    html_path = results_dir / "latest.html"
    assert json_path.exists()
    assert html_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["samples"][0]["sample_id"] == "sample1"
