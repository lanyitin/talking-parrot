"""Report rendering and writing.

Realises **Decision: ReportWriter is a pure renderer plus thin write
step** and **Decision: Implementation Contract — Report JSON / HTML
format** from the ``regression-runner`` change's ``design.md``.

``render_report`` is pure — no I/O. ``write_report`` is the only
function in this module that touches the filesystem.
"""

from __future__ import annotations

import html
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from talking_parrot.shared import ScoreCard

_REPORT_SCHEMA_VERSION = 1
_logger = logging.getLogger("talking_parrot.regression.reporter")

_VALID_VERDICTS = {
    "regressed",
    "improved",
    "stable",
    "bootstrapped",
    "skipped",
    "unscored",
}

# Verdict ordering: highest index = "worst" verdict.
_VERDICT_RANK = {
    "improved": 0,
    "stable": 1,
    "skipped": 2,
    "unscored": 3,
    "bootstrapped": 4,
    "regressed": 5,
}


@dataclass(frozen=True, slots=True)
class SampleReportEntry:
    """One row in a regression report."""

    sample_id: str
    variant_file: str
    verdict: str
    current: ScoreCard
    baseline: ScoreCard | None
    delta: dict[str, float] | None
    stage_timings: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegressionReport:
    """Top-level regression report aggregate."""

    schema_version: int
    generated_at: str
    label: str | None
    samples: tuple[SampleReportEntry, ...]

    @property
    def overall_verdict(self) -> str:
        """Return the worst per-sample verdict.

        Bootstrapped runs report ``bootstrapped`` overall when no
        ``regressed`` sample is present.
        """
        if not self.samples:
            return "stable"
        worst = max(
            self.samples,
            key=lambda e: _VERDICT_RANK.get(e.verdict, -1),
        )
        return worst.verdict


def _score_card_to_json(card: ScoreCard) -> dict:
    """Serialise a :class:`ScoreCard` to a JSON-safe dict."""
    mb = card.metric_bundle
    return {
        "sample_id": card.sample_id,
        "overall_score": card.overall_score,
        "metric_bundle": {
            "cer": mb.cer,
            "confidence_mean": mb.confidence_mean,
            "confidence_p10": mb.confidence_p10,
            "repetition_ratio_mean": mb.repetition_ratio_mean,
            "no_speech_prob_mean": mb.no_speech_prob_mean,
        },
        "cue_diffs": [
            {
                "index": d.index,
                "reference_text": d.reference_text,
                "hypothesis_text": d.hypothesis_text,
                "cer": d.cer,
                "start_ms_delta": d.start_ms_delta,
                "end_ms_delta": d.end_ms_delta,
            }
            for d in card.cue_diffs
        ],
    }


def _report_to_json_dict(report: RegressionReport) -> dict:
    """Render ``report`` to the schema-v1 JSON dict shape."""
    samples_json: list[dict] = []
    for entry in report.samples:
        if entry.baseline is None:
            baseline_obj: dict | None = None
            delta_obj: dict | None = None
        else:
            baseline_obj = {"score_card": _score_card_to_json(entry.baseline)}
            delta_obj = dict(entry.delta) if entry.delta is not None else None
        samples_json.append(
            {
                "sample_id": entry.sample_id,
                "variant_file": entry.variant_file,
                "verdict": entry.verdict,
                "current": {"score_card": _score_card_to_json(entry.current)},
                "baseline": baseline_obj,
                "delta": delta_obj,
                "stage_timings": dict(entry.stage_timings),
            }
        )
    return {
        "schema_version": _REPORT_SCHEMA_VERSION,
        "generated_at": report.generated_at,
        "label": report.label,
        "overall_verdict": report.overall_verdict,
        "samples": samples_json,
    }


_HTML_STYLE = """
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2em; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.8em; text-align: left; }
th { background: #f4f4f4; }
.verdict-regressed { background: #fdd; color: #900; font-weight: bold; }
.verdict-improved { background: #dfd; color: #060; font-weight: bold; }
.verdict-stable { background: #ffd; color: #660; }
.verdict-bootstrapped { background: #ddf; color: #006; }
.verdict-skipped { background: #eee; color: #555; }
.verdict-unscored { background: #eee; color: #555; }
details { margin: 0.5em 0; }
""".strip()


def _render_html(report: RegressionReport) -> str:
    """Render ``report`` to a single self-contained HTML document."""
    rows: list[str] = []
    for entry in report.samples:
        verdict_class = f"verdict-{entry.verdict}"
        cer = entry.current.metric_bundle.cer
        conf = entry.current.metric_bundle.confidence_mean
        cue_rows = "\n".join(
            f"<li>#{html.escape(str(d.index))} cer={d.cer:.4f} "
            f"hyp={html.escape(d.hypothesis_text)}</li>"
            for d in entry.current.cue_diffs
        )
        timing_rows = "\n".join(
            f"<li>{html.escape(stage)}: {secs:.2f}s</li>"
            for stage, secs in entry.stage_timings.items()
        )
        timing_total = sum(entry.stage_timings.values())
        timing_cell = (
            f"<details><summary>{timing_total:.1f}s total</summary>"
            f"<ul>{timing_rows}</ul></details>"
            if entry.stage_timings
            else "—"
        )
        rows.append(
            f"<tr>"
            f"<td>{html.escape(entry.sample_id)}</td>"
            f"<td>{html.escape(entry.variant_file)}</td>"
            f'<td class="{html.escape(verdict_class)}">'
            f"{html.escape(entry.verdict)}</td>"
            f"<td>{cer:.4f}</td>"
            f"<td>{conf:.4f}</td>"
            f"<td>{timing_cell}</td>"
            f"<td><details><summary>cue diffs ({len(entry.current.cue_diffs)})"
            f"</summary><ul>{cue_rows}</ul></details></td>"
            f"</tr>"
        )

    table_body = "\n".join(rows) if rows else "<tr><td colspan='6'>No samples</td></tr>"
    label_text = html.escape(report.label) if report.label else "(none)"
    overall = html.escape(report.overall_verdict)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head>\n'
        '<meta charset="utf-8">\n'
        "<title>Talking Parrot Regression Report</title>\n"
        f"<style>{_HTML_STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        "<h1>Talking Parrot Regression Report</h1>\n"
        f"<p>Generated at {html.escape(report.generated_at)} — "
        f"label: {label_text} — "
        f'overall verdict: <span class="verdict-{overall}">{overall}</span></p>\n'
        "<table>\n"
        "<thead><tr>"
        "<th>sample_id</th><th>variant_file</th><th>verdict</th>"
        "<th>cer</th><th>confidence_mean</th><th>stage_timings</th><th>cue_diffs</th>"
        "</tr></thead>\n"
        f"<tbody>\n{table_body}\n</tbody>\n"
        "</table>\n"
        "</body></html>\n"
    )


def render_report(report: RegressionReport) -> tuple[str, str]:
    """Render ``report`` to ``(json_text, html_text)``.

    Pure: no I/O. The JSON text follows the schema-v1 shape; the HTML is
    a single self-contained document with one ``<style>`` block.
    """
    _logger.debug(
        "render_report samples=%d label=%r", len(report.samples), report.label
    )
    json_text = json.dumps(
        _report_to_json_dict(report), ensure_ascii=False, indent=2, sort_keys=True
    )
    html_text = _render_html(report)
    return json_text, html_text


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically via tempfile + ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def write_report(report: RegressionReport, results_dir: Path) -> None:
    """Write the rendered report to ``results_dir/latest.{json,html}``."""
    json_text, html_text = render_report(report)
    json_path = Path(results_dir) / "latest.json"
    html_path = Path(results_dir) / "latest.html"
    _logger.debug("write_report json=%s html=%s", json_path, html_path)
    _atomic_write(json_path, json_text)
    _atomic_write(html_path, html_text)


__all__ = [
    "RegressionReport",
    "SampleReportEntry",
    "render_report",
    "write_report",
]
