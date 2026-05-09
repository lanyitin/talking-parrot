# regression-report Specification

## Purpose

TBD - created by archiving change 'regression-runner'. Update Purpose after archive.

## Requirements

### Requirement: Report JSON schema v1

The system SHALL emit a JSON report to `<results_dir>/latest.json` (default `test-samples/results/latest.json`) conforming to schema version `1` with top-level keys: `schema_version` (integer equal to `1`), `generated_at` (ISO-8601 string), `label` (string or `null`), `overall_verdict` (one of `regressed`, `improved`, `stable`, `bootstrapped`), and `samples` (list). Each `samples` entry MUST contain `sample_id`, `variant_file`, `verdict`, `current` (object containing `score_card`), `baseline` (object containing `score_card`, or `null` when bootstrapping), and `delta` (object whose keys are the `MetricBundle` field names with float values, or `null` when there is no baseline).

#### Scenario: Bootstrap run carries null baseline

- **WHEN** the report is emitted for a sample with no prior baseline
- **THEN** the corresponding entry's `baseline` field MUST equal `null`, its `delta` field MUST equal `null`, and its `verdict` field MUST equal `bootstrapped`

#### Scenario: Overall verdict is worst per-sample verdict

- **WHEN** three samples are reported with verdicts `stable`, `improved`, `regressed`
- **THEN** `overall_verdict` MUST equal `regressed`


<!-- @trace
source: regression-runner
updated: 2026-05-09
code:
  - src/talking_parrot/mcp/cli.py
  - src/talking_parrot/regression/reporter.py
  - src/talking_parrot/regression/__init__.py
  - uv.lock
  - tests/unit/regression/_fixtures.py
  - src/talking_parrot/regression/cli.py
  - src/talking_parrot/regression/scorer.py
  - src/talking_parrot/mcp/__init__.py
  - src/talking_parrot/regression/__main__.py
  - src/talking_parrot/mcp/server.py
  - pyproject.toml
  - src/talking_parrot/regression/runner.py
  - tests/integration/regression/__init__.py
  - tests/unit/regression/__init__.py
  - tests/unit/mcp/conftest.py
  - src/talking_parrot/mcp/__main__.py
  - tests/unit/mcp/__init__.py
  - src/talking_parrot/regression/baseline.py
tests:
  - tests/unit/regression/test_cli_entry.py
  - tests/unit/mcp/test_stdio_dispatch.py
  - tests/unit/regression/test_reporter.py
  - tests/unit/mcp/test_http_dispatch.py
  - tests/unit/mcp/test_range_helpers.py
  - tests/unit/mcp/test_cli_transport_selection.py
  - tests/unit/mcp/test_shutdown.py
  - tests/unit/regression/test_cli.py
  - tests/integration/regression/test_end_to_end.py
  - tests/unit/mcp/test_summary.py
  - tests/unit/mcp/test_cli_dispatch.py
  - tests/unit/mcp/test_snapshot_binding.py
  - tests/unit/mcp/test_cli_env.py
  - tests/unit/regression/test_runner.py
  - tests/unit/regression/test_scorer.py
  - tests/unit/mcp/test_cli_args.py
  - tests/unit/mcp/test_port_collision.py
  - tests/unit/mcp/test_transcription_results.py
  - tests/unit/mcp/test_diagnostics.py
  - tests/unit/regression/test_public_api.py
  - tests/unit/mcp/test_tool_registration.py
  - tests/unit/regression/test_baseline.py
-->

---
### Requirement: HTML report self-contained

The system SHALL emit an HTML report to `<results_dir>/latest.html` that is a single self-contained document with no external CSS or JavaScript references. All styling MUST appear inside one `<style>` element inside the document `<head>`. The HTML MUST contain one `<table>` listing each sample with columns `sample_id`, `variant_file`, `verdict`, `cer`, `confidence_mean`, and a per-sample `<details>` element listing each `CueDiff`.

#### Scenario: No external resources referenced

- **WHEN** the emitted HTML is parsed
- **THEN** it MUST contain zero `<link rel="stylesheet">` elements and zero `<script src="...">` elements

#### Scenario: Verdict cell carries class for colour

- **WHEN** a sample's verdict is `regressed`
- **THEN** its verdict cell MUST carry the CSS class `verdict-regressed` and the inline `<style>` block MUST define a rule for `.verdict-regressed`


<!-- @trace
source: regression-runner
updated: 2026-05-09
code:
  - src/talking_parrot/mcp/cli.py
  - src/talking_parrot/regression/reporter.py
  - src/talking_parrot/regression/__init__.py
  - uv.lock
  - tests/unit/regression/_fixtures.py
  - src/talking_parrot/regression/cli.py
  - src/talking_parrot/regression/scorer.py
  - src/talking_parrot/mcp/__init__.py
  - src/talking_parrot/regression/__main__.py
  - src/talking_parrot/mcp/server.py
  - pyproject.toml
  - src/talking_parrot/regression/runner.py
  - tests/integration/regression/__init__.py
  - tests/unit/regression/__init__.py
  - tests/unit/mcp/conftest.py
  - src/talking_parrot/mcp/__main__.py
  - tests/unit/mcp/__init__.py
  - src/talking_parrot/regression/baseline.py
tests:
  - tests/unit/regression/test_cli_entry.py
  - tests/unit/mcp/test_stdio_dispatch.py
  - tests/unit/regression/test_reporter.py
  - tests/unit/mcp/test_http_dispatch.py
  - tests/unit/mcp/test_range_helpers.py
  - tests/unit/mcp/test_cli_transport_selection.py
  - tests/unit/mcp/test_shutdown.py
  - tests/unit/regression/test_cli.py
  - tests/integration/regression/test_end_to_end.py
  - tests/unit/mcp/test_summary.py
  - tests/unit/mcp/test_cli_dispatch.py
  - tests/unit/mcp/test_snapshot_binding.py
  - tests/unit/mcp/test_cli_env.py
  - tests/unit/regression/test_runner.py
  - tests/unit/regression/test_scorer.py
  - tests/unit/mcp/test_cli_args.py
  - tests/unit/mcp/test_port_collision.py
  - tests/unit/mcp/test_transcription_results.py
  - tests/unit/mcp/test_diagnostics.py
  - tests/unit/regression/test_public_api.py
  - tests/unit/mcp/test_tool_registration.py
  - tests/unit/regression/test_baseline.py
-->

---
### Requirement: ReportWriter is a pure renderer plus thin write step

The system SHALL provide `render_report(report) -> tuple[str, str]` returning `(json_text, html_text)` as a pure function (no I/O), and a separate `write_report(report, results_dir: Path) -> None` that performs the two file writes via atomic `os.replace`. The renderer MUST NOT depend on `runner.py`, `baseline.py`, or `cli.py`.

#### Scenario: Pure rendering performs no I/O

- **WHEN** `render_report(report)` is called inside a test that monkeypatches `pathlib.Path.open` to raise
- **THEN** the call MUST return a `(json_text, html_text)` tuple of strings

<!-- @trace
source: regression-runner
updated: 2026-05-09
code:
  - src/talking_parrot/mcp/cli.py
  - src/talking_parrot/regression/reporter.py
  - src/talking_parrot/regression/__init__.py
  - uv.lock
  - tests/unit/regression/_fixtures.py
  - src/talking_parrot/regression/cli.py
  - src/talking_parrot/regression/scorer.py
  - src/talking_parrot/mcp/__init__.py
  - src/talking_parrot/regression/__main__.py
  - src/talking_parrot/mcp/server.py
  - pyproject.toml
  - src/talking_parrot/regression/runner.py
  - tests/integration/regression/__init__.py
  - tests/unit/regression/__init__.py
  - tests/unit/mcp/conftest.py
  - src/talking_parrot/mcp/__main__.py
  - tests/unit/mcp/__init__.py
  - src/talking_parrot/regression/baseline.py
tests:
  - tests/unit/regression/test_cli_entry.py
  - tests/unit/mcp/test_stdio_dispatch.py
  - tests/unit/regression/test_reporter.py
  - tests/unit/mcp/test_http_dispatch.py
  - tests/unit/mcp/test_range_helpers.py
  - tests/unit/mcp/test_cli_transport_selection.py
  - tests/unit/mcp/test_shutdown.py
  - tests/unit/regression/test_cli.py
  - tests/integration/regression/test_end_to_end.py
  - tests/unit/mcp/test_summary.py
  - tests/unit/mcp/test_cli_dispatch.py
  - tests/unit/mcp/test_snapshot_binding.py
  - tests/unit/mcp/test_cli_env.py
  - tests/unit/regression/test_runner.py
  - tests/unit/regression/test_scorer.py
  - tests/unit/mcp/test_cli_args.py
  - tests/unit/mcp/test_port_collision.py
  - tests/unit/mcp/test_transcription_results.py
  - tests/unit/mcp/test_diagnostics.py
  - tests/unit/regression/test_public_api.py
  - tests/unit/mcp/test_tool_registration.py
  - tests/unit/regression/test_baseline.py
-->