## 1. Package scaffolding

- [x] 1.1 Create `src/talking_parrot/regression/__init__.py` exposing the public API (`RegressionRunner`, `score`, `BaselineStore`, `JsonBaselineStore`, `render_report`, `write_report`) so the import surface aligns with the **Decision: Module decomposition follows SRP** module split, verified by `tests/unit/regression/test_public_api.py::test_public_symbols_exported`.
- [x] 1.2 [P] Create `src/talking_parrot/regression/__main__.py` delegating to `cli.main()` so `uv run python -m talking_parrot.regression --help` prints the documented flag list, verified by `tests/unit/regression/test_cli_entry.py::test_module_dunder_main_help_succeeds`.

## 2. Quality scorer (pure)

- [x] 2.1 Implement the **QualityScorer pure-function contract** by coding `score(snapshot, descriptor) -> ScoreCard` in `src/talking_parrot/regression/scorer.py` so it performs no I/O and does not import from runner/cli/baseline/reporter, exercising the **Decision: Module decomposition follows SRP** boundary, verified by `tests/unit/regression/test_scorer.py::test_pure_no_io` and `::test_inputs_not_mutated`.
- [x] 2.2 Implement **CER computation via stdlib difflib** using `difflib.SequenceMatcher` per the **Decision: CER uses stdlib `difflib`** clamp-to-`[0,1]` rule, verified by `tests/unit/regression/test_scorer.py::test_cer_identical_zero` and `::test_cer_clamped`.
- [x] 2.3 Implement **Confidence and no-speech aggregates** with `math.exp` over `avg_logprob` plus 10th-percentile / mean helpers and zero defaults on empty results, verified by `tests/unit/regression/test_scorer.py::test_aggregates_use_exp_logprob` and `::test_empty_results_default_zero`.
- [x] 2.4 [P] Implement **Per-cue diff emission** producing one ordered `CueDiff` per current subtitle in ascending `index`, verified by `tests/unit/regression/test_scorer.py::test_cue_diffs_sorted_by_index`.
- [x] 2.5 [P] Add docstrings to every public symbol of `scorer.py` and confirm `uv run mypy src/talking_parrot/regression/scorer.py` exits zero.

## 3. Baseline store

- [x] 3.1 Define the **BaselineStore protocol** as `@runtime_checkable` in `src/talking_parrot/regression/baseline.py` together with the `BaselineSchemaError` exception per the **Decision: BaselineStore is a Protocol with a JSON implementation**, verified by `tests/unit/regression/test_baseline.py::test_protocol_runtime_checkable`.
- [x] 3.2 Implement the **JsonBaselineStore filesystem layout**: `JsonBaselineStore.save` writes to `<root>/<sample_id>/baseline.json` atomically via tempfile + `os.replace`, verified by `tests/unit/regression/test_baseline.py::test_save_atomic_replace`.
- [x] 3.3 Implement the **Baseline JSON schema v1** serialisation matching the **Decision: Implementation Contract — Baseline JSON format** (top-level keys, always-present `cue_diffs`), verified by `tests/unit/regression/test_baseline.py::test_round_trip_preserves_cue_diffs` and `::test_empty_cue_diffs_present`.
- [x] 3.4 [P] Implement `JsonBaselineStore.load` returning `None` on missing file and raising `BaselineSchemaError` on unknown `schema_version`, verified by `tests/unit/regression/test_baseline.py::test_load_missing_returns_none` and `::test_load_unknown_schema_raises`.

## 4. Report writer

- [x] 4.1 Implement **ReportWriter is a pure renderer plus thin write step** by coding pure `render_report(report) -> tuple[str, str]` and a separate `write_report(report, results_dir)` that does the only I/O, verified by `tests/unit/regression/test_reporter.py::test_render_is_pure_no_io` and `::test_write_report_uses_atomic_replace`.
- [x] 4.2 Implement the **Report JSON schema v1** payload per the **Decision: Implementation Contract — Report JSON / HTML format** (top-level keys, `null` baseline/delta on bootstrap, worst per-sample verdict as `overall_verdict`), verified by `tests/unit/regression/test_reporter.py::test_json_schema_v1_shape` and `::test_bootstrap_baseline_is_null`.
- [x] 4.3 [P] Ensure the **HTML report self-contained** output has zero external `<link>`/`<script src>` references and embeds verdict CSS classes (`.verdict-regressed`, `.verdict-improved`, `.verdict-stable`, `.verdict-bootstrapped`) inside one inline `<style>` block, verified by `tests/unit/regression/test_reporter.py::test_html_self_contained` and `::test_verdict_class_in_style`.

## 5. Runner orchestration

- [x] 5.1 Implement the **CLI entry point and sample discovery** capability: `discover_samples(samples_dir) -> list[SampleDescriptor]` parsing each `descriptor.yml` per the **Decision: Sample discovery and pipeline invocation**, verified by `tests/unit/regression/test_runner.py::test_discover_samples_orders_variants` and `tests/unit/regression/test_cli.py::test_exit_two_on_missing_samples_dir`.
- [x] 5.2 Implement **Per-variant pipeline orchestration** by driving `talking_parrot.pipeline.orchestrator` once per variant and reusing one orchestrator instance across variants, verified by `tests/unit/regression/test_runner.py::test_orchestrator_constructed_once`.
- [x] 5.3 [P] Implement missing-audio handling that emits `verdict="skipped"` and only triggers exit code 1 with `--strict-missing`, verified by `tests/unit/regression/test_runner.py::test_missing_audio_skipped_default` and `::test_missing_audio_strict_exits_one`.
- [x] 5.4 Implement **Verdict thresholds and exit code** per the **Decision: Regression verdict is rule-based with explicit thresholds** with configurable `cer_tolerance` and `confidence_tolerance`, verified by `tests/unit/regression/test_runner.py::test_cer_above_tolerance_regressed` and `::test_confidence_drop_above_tolerance_regressed`.

## 6. CLI wiring

- [x] 6.1 Implement argument parsing of `--samples-dir`, `--results-dir`, `--label`, `--reset-baseline`, `--cer-tolerance`, `--confidence-tolerance`, `--strict-missing` per the **Decision: CLI surface and exit codes**, verified by `tests/unit/regression/test_cli.py::test_flags_parsed`.
- [x] 6.2 Wire exit-code rules (`0` clean, `1` regressed, `2` config/I-O failure) per the **Decision: CLI surface and exit codes**, verified by `tests/unit/regression/test_cli.py::test_exit_zero_when_stable` and `::test_exit_one_when_regressed`.
- [x] 6.3 [P] Implement the **Reset-baseline flag** so `--reset-baseline` overrides every verdict to `bootstrapped` and forces exit code `0`, verified by `tests/unit/regression/test_cli.py::test_reset_baseline_overrides_verdicts`.

## 7. Integration test

- [x] 7.1 Add `tests/integration/regression/test_end_to_end.py::test_runner_with_fixture_snapshot` injecting a stub orchestrator that returns a fixture `ProjectSnapshot` plus a fixture `BaselineStore`, asserting the runner produces a JSON + HTML report and the documented exit code, exercising the **Decision: Module decomposition follows SRP** wiring end-to-end without real audio.

## 8. Quality gates

- [x] 8.1 [P] Run `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src`, and `uv run pytest`; all four MUST exit zero before this change is considered complete.
- [x] 8.2 [P] Confirm no third-party dependency is introduced (no edits to `pyproject.toml` `[project.dependencies]`); record any future suggestion under design `## Open Questions`.
