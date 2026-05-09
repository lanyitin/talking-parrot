"""Unit tests for ``talking_parrot.regression.reporter``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from talking_parrot.shared import MetricBundle, ScoreCard

from talking_parrot.regression import (
    RegressionReport,
    SampleReportEntry,
    render_report,
    write_report,
)


def _bundle(cer: float = 0.04, confidence_mean: float = 0.82) -> MetricBundle:
    return MetricBundle(
        cer=cer,
        confidence_mean=confidence_mean,
        confidence_p10=0.61,
        repetition_ratio_mean=0.0,
        no_speech_prob_mean=0.05,
    )


def _card(sample_id: str = "sample1") -> ScoreCard:
    return ScoreCard(sample_id=sample_id, overall_score=0.87, metric_bundle=_bundle())


def _report_with(verdicts: list[str]) -> RegressionReport:
    entries: list[SampleReportEntry] = []
    for i, v in enumerate(verdicts):
        entries.append(
            SampleReportEntry(
                sample_id=f"sample{i}",
                variant_file="base.mp3",
                verdict=v,
                current=_card(f"sample{i}"),
                baseline=None if v == "bootstrapped" else _card(f"sample{i}"),
                delta=None
                if v == "bootstrapped"
                else {
                    "cer": 0.0,
                    "confidence_mean": 0.0,
                    "confidence_p10": 0.0,
                    "repetition_ratio_mean": 0.0,
                    "no_speech_prob_mean": 0.0,
                },
            )
        )
    return RegressionReport(
        schema_version=1,
        generated_at="2026-05-09T12:35:10+00:00",
        label="manual",
        samples=tuple(entries),
    )


def test_render_is_pure_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """``render_report`` does not touch the filesystem."""

    def boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("render_report must not open files")

    monkeypatch.setattr(Path, "open", boom)
    report = _report_with(["stable"])
    json_text, html_text = render_report(report)
    assert isinstance(json_text, str)
    assert isinstance(html_text, str)


def test_write_report_uses_atomic_replace(tmp_path: Path) -> None:
    """``write_report`` produces ``latest.json`` and ``latest.html``."""
    report = _report_with(["stable"])
    write_report(report, tmp_path)
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "latest.html").exists()
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_json_schema_v1_shape() -> None:
    """JSON report contains the documented top-level keys."""
    report = _report_with(["stable", "improved", "regressed"])
    json_text, _ = render_report(report)
    payload = json.loads(json_text)
    assert payload["schema_version"] == 1
    for key in ("generated_at", "label", "overall_verdict", "samples"):
        assert key in payload
    # Worst per-sample verdict propagates as overall_verdict.
    assert payload["overall_verdict"] == "regressed"


def test_bootstrap_baseline_is_null() -> None:
    """Bootstrap entries serialise ``baseline`` and ``delta`` as ``null``."""
    report = _report_with(["bootstrapped"])
    json_text, _ = render_report(report)
    payload = json.loads(json_text)
    entry = payload["samples"][0]
    assert entry["baseline"] is None
    assert entry["delta"] is None
    assert entry["verdict"] == "bootstrapped"


def test_html_self_contained() -> None:
    """HTML has no external CSS or JS references."""
    _, html_text = render_report(_report_with(["stable"]))
    assert '<link rel="stylesheet"' not in html_text
    assert "<script src=" not in html_text
    assert "<style>" in html_text


def test_verdict_class_in_style() -> None:
    """Verdict CSS classes exist inside the inline ``<style>`` block."""
    _, html_text = render_report(_report_with(["regressed"]))
    style_start = html_text.index("<style>")
    style_end = html_text.index("</style>")
    style_block = html_text[style_start:style_end]
    for cls in (
        ".verdict-regressed",
        ".verdict-improved",
        ".verdict-stable",
        ".verdict-bootstrapped",
    ):
        assert cls in style_block, f"missing {cls} in <style> block"
    assert "verdict-regressed" in html_text
