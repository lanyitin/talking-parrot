## Why

`docs/TODOs.md` has a standing item to build a regression test harness so each pipeline change can be evaluated against the audio assets in `test-samples/`. The shared layer (`ProjectSnapshot`, `ScoreCard`, `MetricBundle`, `CueDiff`, `SnapshotLoader`) has just landed via `2026-05-09-shared-layer`, leaving the runner / scorer / reporter / baseline / CLI components unimplemented. Without these, transcription quality drift cannot be detected automatically and TODO item 1 of the quality-and-tooling initiative remains open.

## What Changes

- Introduce `src/talking_parrot/regression/` package with single-responsibility modules: `runner.py`, `scorer.py`, `reporter.py`, `baseline.py`, `cli.py`, plus `__init__.py` and `__main__.py` so `uv run python -m talking_parrot.regression` is the supported entry point.
- Define a CLI orchestration capability that discovers samples from `test-samples/<sample>/descriptor.yml`, runs the existing pipeline orchestrator per variant, scores the result, compares against a baseline, writes JSON + HTML reports, and exits non-zero on regression.
- Define a quality-scorer capability that converts a `ProjectSnapshot` plus reference text into a `ScoreCard` / `MetricBundle` (CER via Python stdlib `difflib`, plus confidence and no-speech aggregates) without I/O or new third-party dependencies.
- Define a regression-baseline-store capability with a `BaselineStore` protocol and `JsonBaselineStore` implementation that persists per-sample baselines under `test-samples/<sample>/baseline.json`.
- Define a regression-report capability that fixes the on-disk JSON schema (versioned) and a minimal self-contained HTML view written to `test-samples/results/latest.json` and `test-samples/results/latest.html`.
- Add unit tests under `tests/unit/regression/` per module and one integration test using a fixture `ProjectSnapshot` (no real audio dependency).
- Consume `talking_parrot.shared` types only; this change MUST NOT redefine `ProjectSnapshot`, `ScoreCard`, `MetricBundle`, `CueDiff`, or `SnapshotLoader`.

## Impact

- **Affected specs:** new capabilities `regression-runner`, `quality-scorer`, `regression-baseline-store`, `regression-report`.
- **Affected code:** new files under `src/talking_parrot/regression/`, new tests under `tests/unit/regression/` and `tests/integration/regression/`. Existing capabilities (`project-snapshot`, `quality-metrics`, `pipeline-end-to-end-wiring`) are imported only — not modified.
- **Tooling:** adds a runnable module `talking_parrot.regression`; no change to `[build-system]` and no new third-party dependency. `jiwer` is recorded as an Open Question / suggested dependency, not adopted.
- **CI / quality:** harness invocation is opt-in (operator runs it); the test suite covers orchestration logic with fixture snapshots so `uv run pytest` remains hermetic.
