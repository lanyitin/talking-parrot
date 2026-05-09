---
title: "01 — Regression Harness"
tags:
  - quality
  - regression
  - testing
aliases:
  - regression-harness
---

# 01 — Regression Harness

[[README|Back to overview]] | Related: [[shared-architecture]]

---

## Goal

Provide an automated harness that runs the full talking-parrot pipeline against every audio file in `test-samples/`, collects structured quality metrics (subtitle text, confidence, timing), persists the results, and reports whether quality improved or regressed relative to a stored baseline.

---

## Scope

- Discover and iterate over all samples described by `descriptor.yml` files under `test-samples/`
- Run the full pipeline (`pipeline/orchestrator.py`) programmatically for each sample variant
- Collect `ScoreCard` per run: subtitle count, character error rate (CER) vs reference text, avg confidence, coverage rate, timing drift
- Persist results as JSON baselines under `test-samples/<sample>/baseline.json`
- Produce a human-readable HTML summary report
- Expose a `uv run python -m talking_parrot.regression` CLI entry point

---

## Non-Goals

- Does not replace the unit/integration test suite (`tests/`)
- Does not stream audio or render video — read-only file processing
- Does not implement its own ASR model; uses the existing pipeline
- Does not track Git SHAs automatically (callers must tag runs if desired)

---

## Dependencies

| Dependency | Direction | Notes |
|---|---|---|
| `shared/project_snapshot.py` | upstream | `ProjectSnapshot` value object |
| `shared/metrics.py` | upstream | `ScoreCard`, `CueDiff` |
| `pipeline/orchestrator.py` | upstream | existing — called as a library, not subprocess |
| `test-samples/*/descriptor.yml` | data | existing — defines sample + reference text |

---

## Data Model

```mermaid
classDiagram
    class SampleDescriptor {
        +sample_id: str
        +base_file: str
        +reference_text: str
        +variants: list[SampleVariant]
        +from_yml(path: str)$ SampleDescriptor
    }

    class SampleVariant {
        +file: str
        +description: str
    }

    class RunResult {
        +sample_id: str
        +variant_file: str
        +run_timestamp: str
        +git_sha: str | None
        +score_card: ScoreCard
        +subtitles: list[SubtitleRecord]
    }

    class ScoreCard {
        +subtitle_count: int
        +cer: float
        +avg_logprob: float
        +avg_no_speech_prob: float
        +coverage_rate: float
        +avg_timing_drift_ms: float
        +overall_score: float
    }

    class SubtitleRecord {
        +index: int
        +start_ms: int
        +end_ms: int
        +text: str
        +avg_logprob: float
        +no_speech_prob: float
    }

    class BaselineStore {
        <<interface>>
        +load(sample_id: str) RunResult | None
        +save(result: RunResult) void
    }

    class JsonBaselineStore {
        +root_dir: str
        +load(sample_id: str) RunResult | None
        +save(result: RunResult) void
    }

    class RegressionReport {
        +run_results: list[RunResult]
        +comparisons: list[RunComparison]
        +overall_verdict: str
    }

    class RunComparison {
        +sample_id: str
        +variant_file: str
        +baseline: ScoreCard | None
        +current: ScoreCard
        +delta: ScoreCard
        +verdict: str
    }

    SampleDescriptor "1" *-- "0..*" SampleVariant
    RunResult "1" *-- "1" ScoreCard
    RunResult "1" *-- "0..*" SubtitleRecord
    BaselineStore <|.. JsonBaselineStore
    RegressionReport "1" *-- "0..*" RunResult
    RegressionReport "1" *-- "0..*" RunComparison
    RunComparison "1" *-- "2" ScoreCard
```

---

## Process Flow

```mermaid
flowchart TD
    A([CLI: uv run python -m talking_parrot.regression]) --> B[Discover SampleDescriptors\nfrom test-samples/**/descriptor.yml]
    B --> C{For each sample\n+ variant}
    C --> D[Load audio file\nvia AudioDecoder]
    D --> E[Run pipeline\nOrchestrator.run]
    E --> F[Collect ProjectSnapshot\nvad_segments + subtitles + metrics]
    F --> G[QualityScorer.score\nreturns ScoreCard]
    G --> H{Baseline exists?}
    H -->|yes| I[Load JsonBaselineStore\nCompute RunComparison delta]
    H -->|no| J[First run — save as new baseline]
    I --> K[Determine verdict\nregressed / improved / stable]
    J --> K
    K --> L[Accumulate into\nRegressionReport]
    L --> C
    C --> M{All samples done}
    M --> N[ReportWriter.write_json\ntest-samples/results/latest.json]
    N --> O[ReportWriter.write_html\ntest-samples/results/latest.html]
    O --> P{Any regressions?}
    P -->|yes| Q([Exit code 1\nprint summary to stdout])
    P -->|no| R([Exit code 0\nprint summary to stdout])
```

---

## Module Breakdown

| Module | Responsibility (SRP) |
|---|---|
| `regression/runner.py` | Discovers samples, invokes pipeline, collects `ProjectSnapshot` per run |
| `regression/scorer.py` | Pure function: `ProjectSnapshot + SampleDescriptor → ScoreCard`; no I/O |
| `regression/reporter.py` | Pure function: `RegressionReport → JSON str + HTML str`; no I/O |
| `regression/baseline.py` | `BaselineStore` interface + `JsonBaselineStore` implementation |
| `regression/cli.py` | Argument parsing, env-var injection, wires runner → scorer → reporter → baseline |

> [!tip] OCP in practice
> New scoring dimensions (BLEU, word error rate) are added by implementing a new class satisfying `QualityScorerPort`, then registering it in `cli.py`. No existing scorer is modified.

---

## CER Calculation Note

Character Error Rate (CER) = edit distance between concatenated output text and `descriptor.yml` `text` field, normalised by reference length. This requires no new dependency — Python stdlib `difflib.SequenceMatcher` is sufficient.

> [!note] Suggested new dependency
> If WER (word error rate) is later required, `jiwer` is the standard choice. Not needed for the initial milestone.

---

## Implementation Milestones

1. **M1 — Shared layer** `shared/project_snapshot.py` + `shared/metrics.py`: define frozen dataclasses, no logic.
2. **M2 — Sample discovery** `regression/runner.py`: `SampleDescriptor.from_yml`, file glob, variant iteration.
3. **M3 — Scorer** `regression/scorer.py`: implement CER, confidence aggregation, coverage rate — fully unit-testable without audio files.
4. **M4 — Baseline store** `regression/baseline.py`: `JsonBaselineStore` — reads/writes `baseline.json`.
5. **M5 — Reporter** `regression/reporter.py`: JSON + minimal HTML output.
6. **M6 — CLI + integration** wire everything; add `[project.scripts]` entry in `pyproject.toml`.

---

## Risks & Trade-offs

| Risk | Mitigation |
|---|---|
| Pipeline run time per sample is long (model loading) | Cache model instance across samples within one CLI invocation |
| Reference text in `descriptor.yml` may be incomplete | CER is advisory; human review is still required for semantic quality |
| `test-samples/` audio files not committed to Git (size) | Harness skips missing files with a warning and reports them in the HTML output |
| Baseline drift on model upgrade | Provide `--reset-baseline` flag to overwrite; require explicit operator decision |

---

## Spectra Proposal Suggestion

Split into two changes:
1. `/spectra-propose` **shared-layer** — `ProjectSnapshot`, `ScoreCard`, `BaselineStore` (no pipeline changes)
2. `/spectra-propose` **regression-runner** — runner, scorer, reporter, CLI (depends on shared-layer change)
