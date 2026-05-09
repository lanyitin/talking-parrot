## Context

The harness is the first consumer of the just-archived shared layer (`talking_parrot.shared`). It must:

- Iterate every `test-samples/<sample>/descriptor.yml` and every variant inside it.
- Drive `talking_parrot.pipeline.orchestrator` once per variant, capture the resulting `ProjectSnapshot`, score it, compare to a baseline, and emit a report.
- Stay dependency-free — Python stdlib only — so `uv run pytest` and CI remain hermetic.
- Cleanly decompose into Single-Responsibility modules so future scorers (BLEU, WER) can be added without touching CER code.

Constraints inherited from `CLAUDE.md`: Python ≥ 3.13 via `uv`; mandatory docstrings on every public symbol; ruff format / ruff check / mypy clean; no edits to `[build-system]`; no new dependencies without approval.

## Goals / Non-Goals

**Goals**
- Deterministic, programmatic regression detection for the talking-parrot pipeline.
- Baseline-vs-current comparison with explicit thresholds; exit code reflects regression status.
- JSON report is the source of truth; HTML report is a thin renderer for humans.
- Library-callable: every module is importable and unit-testable without subprocesses.

**Non-Goals**
- No GUI, no MCP, no streaming.
- No new ASR backend; uses existing pipeline orchestrator.
- No automatic git-SHA capture (operator passes `--label` if desired).
- No modifications to shared/ types or to existing pipeline code.

## Decisions

### Decision: Module decomposition follows SRP

`runner.py` discovers samples and drives the pipeline. `scorer.py` is a pure function `(ProjectSnapshot, reference_text) -> ScoreCard`. `reporter.py` is a pure function `(report_model) -> (json_str, html_str)`. `baseline.py` owns persistence. `cli.py` wires them together and is the only module that performs argument parsing or filesystem mutation outside of `baseline.py` and `reporter.py`'s explicit write calls.

**Why:** keeps the scorer and reporter trivially unit-testable from fixture snapshots; isolates I/O so mypy / mocking remains simple.

**Alternatives considered:** single-file `regression.py` (rejected — bundles I/O with logic); class-per-step OOP design (rejected — adds ceremony for no benefit, pure functions suffice).

### Decision: CER uses stdlib `difflib`

CER is computed via `difflib.SequenceMatcher` on the concatenation of all current `ProjectSnapshot.subtitles` text vs the descriptor `text` field, normalised by reference length, lower-bounded at 0.0 and upper-bounded at 1.0.

**Why:** zero new dependencies; matches the suggestion in `docs/planning/quality-and-tooling/01-regression-harness.md`.

**Alternatives considered:** `jiwer` (rejected for now; recorded as Open Question because adding a dep needs explicit approval per CLAUDE.md).

### Decision: BaselineStore is a Protocol with a JSON implementation

A `typing.Protocol` named `BaselineStore` exposes `load(sample_id: str) -> ScoreCard | None` and `save(sample_id: str, card: ScoreCard) -> None`. The default implementation is `JsonBaselineStore(root_dir: Path)`, writing to `test-samples/<sample_id>/baseline.json`. Files are written atomically (write to `<name>.tmp` then `os.replace`).

**Why:** DIP — `RegressionRunner` depends on the protocol, never on the filesystem; tests inject an in-memory store.

**Alternatives considered:** abstract base class (rejected — Protocol is the project convention for ports).

### Decision: Regression verdict is rule-based with explicit thresholds

A run is `regressed` when current CER exceeds baseline CER by more than the absolute tolerance `cer_tolerance` (default `0.02`) OR current `confidence_mean` is below baseline `confidence_mean` by more than `confidence_tolerance` (default `0.05`). It is `improved` when CER drops by more than tolerance AND confidence does not regress. Otherwise `stable`. Thresholds are CLI-configurable via `--cer-tolerance` and `--confidence-tolerance`.

**Why:** explicit, auditable thresholds; rule shape mirrors the existing `audit: true` workflow toggle in `.spectra.yaml`.

**Alternatives considered:** weighted overall_score comparison only (rejected — opaque; harder to debug regressions).

### Decision: Implementation Contract — Baseline JSON format

```json
{
  "schema_version": 1,
  "sample_id": "sample1",
  "variant_file": "base.mp3",
  "captured_at": "2026-05-09T12:34:56Z",
  "label": "manual-2026-05-09",
  "score_card": {
    "sample_id": "sample1",
    "overall_score": 0.87,
    "metric_bundle": {
      "cer": 0.04,
      "confidence_mean": 0.82,
      "confidence_p10": 0.61,
      "repetition_ratio_mean": 0.0,
      "no_speech_prob_mean": 0.05
    },
    "cue_diffs": []
  }
}
```

`schema_version` is integer; loader rejects unknown versions with `BaselineSchemaError`. `cue_diffs` is always serialised even when empty.

### Decision: Implementation Contract — Report JSON / HTML format

JSON written to `test-samples/results/latest.json` with shape:

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-09T12:35:10Z",
  "label": "manual-2026-05-09",
  "overall_verdict": "regressed",
  "samples": [
    {
      "sample_id": "sample1",
      "variant_file": "base.mp3",
      "verdict": "regressed",
      "current": { "score_card": "..." },
      "baseline": { "score_card": "..." },
      "delta": {
        "cer": 0.03,
        "confidence_mean": -0.02,
        "confidence_p10": -0.01,
        "repetition_ratio_mean": 0.0,
        "no_speech_prob_mean": 0.0
      }
    }
  ]
}
```

HTML written to `test-samples/results/latest.html` is a single self-contained document (no external CSS / JS) containing one `<table>` of samples with verdict-coloured cells (green = improved, yellow = stable, red = regressed), and a per-sample `<details>` panel with the cue-level diff list. Reporter MUST embed all styles inline in a `<style>` tag.

### Decision: CLI surface and exit codes

`uv run python -m talking_parrot.regression [--samples-dir DIR] [--results-dir DIR] [--label STR] [--reset-baseline] [--cer-tolerance FLOAT] [--confidence-tolerance FLOAT]`. Exit code is `0` when every sample's verdict is `stable` or `improved`; `1` when any sample is `regressed`; `2` on argument or I/O failure (caught and logged via stdlib `logging`). `--reset-baseline` overwrites baselines with current scores and forces exit code `0`.

### Decision: Sample discovery and pipeline invocation

`runner.discover_samples(samples_dir)` returns a list of `SampleDescriptor` value objects parsed from each `descriptor.yml` (using stdlib `tomllib`-style parsing is wrong here — the file is YAML; loader uses `pyyaml` only if already a dependency, otherwise a hand-rolled parser is rejected and pyyaml is flagged as a required existing dep). Per variant, `RegressionRunner.run_variant` calls the existing `pipeline.orchestrator` entry point (no subprocess), captures the resulting `ProjectSnapshot`, and yields a `RunResult`. Missing audio files are reported and included in the report with verdict `skipped`; they MUST NOT cause exit code `1` unless `--strict-missing` is passed.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Pipeline run time per sample is long (model loading) | Runner caches the pipeline orchestrator instance across variants within one CLI invocation. |
| Reference text in `descriptor.yml` is incomplete | CER is advisory; report flags samples whose reference is empty with verdict `unscored`. |
| Audio files not committed to Git | Harness skips missing files with a warning, surfaces them in the report, exits `0` unless `--strict-missing`. |
| Baseline drift on model upgrade | `--reset-baseline` flag overwrites baselines, requires explicit operator invocation. |
| HTML rendering complexity creep | HTML emitter is purposely a single inline-style document; no template engine. |

## Migration Plan

This change adds new modules only. There is nothing to migrate. First operator run produces baselines (verdict `bootstrapped`, exit code `0`); subsequent runs compare against them.

## Open Questions

- Should `jiwer` (or `python-Levenshtein`) be added later for a faster / standardised CER and to enable WER? Current decision is **no — stdlib only** for this change. If approved, a follow-up change `regression-runner-wer` would introduce it.
- Should the harness publish results to a remote dashboard? Out of scope; would be a separate change.
