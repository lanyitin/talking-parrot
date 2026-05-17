# quality-scorer Specification

## Purpose

TBD - created by archiving change 'regression-runner'. Update Purpose after archive.

## Requirements

### Requirement: QualityScorer pure-function contract

The system SHALL provide a callable `score(snapshot: ProjectSnapshot, descriptor: SampleDescriptor) -> ScoreCard` in `src/talking_parrot/regression/scorer.py`. The function MUST be pure: it MUST NOT read or write any file, MUST NOT mutate its inputs, and MUST NOT import from `talking_parrot.regression.runner`, `talking_parrot.regression.cli`, `talking_parrot.regression.baseline`, or `talking_parrot.regression.reporter`. The returned `ScoreCard` MUST be constructed using the frozen dataclass exported by `talking_parrot.shared.metrics`.

#### Scenario: Pure invocation does no I/O

- **WHEN** `score(snapshot, descriptor)` is called inside a test that monkeypatches `pathlib.Path.open` to raise
- **THEN** the call MUST succeed and return a `ScoreCard`

#### Scenario: Inputs are not mutated

- **WHEN** `score` is invoked with a snapshot whose `subtitles` list is captured before and after the call
- **THEN** the two lists MUST be equal by value and the snapshot MUST remain `frozen`


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
### Requirement: CER computation via stdlib difflib

The scorer SHALL compute Character Error Rate as `1.0 - difflib.SequenceMatcher(None, reference, hypothesis).ratio()` where `reference` is `descriptor.reference_text` and `hypothesis` is the concatenation of `snapshot.subtitles[*].text` joined without separator. The result MUST be clamped into the closed interval `[0.0, 1.0]` and stored as `MetricBundle.cer`. No third-party library MAY be used for this computation.

#### Scenario: Identical reference and hypothesis yield zero CER

- **WHEN** the descriptor reference text equals the concatenated subtitle text
- **THEN** the resulting `MetricBundle.cer` MUST equal `0.0`

#### Scenario: Empty reference text yields unscored verdict signal

- **WHEN** `descriptor.reference_text` is the empty string
- **THEN** the resulting `MetricBundle.cer` MUST equal `0.0` and the resulting `ScoreCard.overall_score` MUST equal `0.0`


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
### Requirement: Confidence and no-speech aggregates

The scorer SHALL compute `MetricBundle.confidence_mean` as the arithmetic mean of `transcription_results[*].metrics.avg_logprob` exponentiated to a probability via `math.exp`, `MetricBundle.confidence_p10` as the 10th percentile of the same probabilities, `MetricBundle.no_speech_prob_mean` as the arithmetic mean of `transcription_results[*].metrics.no_speech_prob`, and `MetricBundle.repetition_ratio_mean` as the arithmetic mean of `transcription_results[*].metrics.repetition_ratio`. When the `transcription_results` list is empty, every aggregate MUST default to `0.0`.

#### Scenario: Empty transcription results default to zero

- **WHEN** `snapshot.transcription_results` is `[]`
- **THEN** `confidence_mean`, `confidence_p10`, `no_speech_prob_mean`, and `repetition_ratio_mean` MUST each equal `0.0`

#### Scenario: Aggregates use exponentiated logprob

- **WHEN** two transcription results carry `avg_logprob = -1.0` and `avg_logprob = -0.5`
- **THEN** `confidence_mean` MUST equal `(math.exp(-1.0) + math.exp(-0.5)) / 2`


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
### Requirement: Per-cue diff emission

The scorer SHALL populate `ScoreCard.cue_diffs` with one `CueDiff` per current subtitle, where `index` is the subtitle index, `hypothesis_text` is the subtitle text, `reference_text` is the empty string when no per-cue reference is available, `cer` is the per-cue CER computed against the cue's hypothesis (clamped to `[0.0, 1.0]`), and `start_ms_delta` and `end_ms_delta` are zero when no baseline cue exists. The list MUST be ordered by ascending `index`.

#### Scenario: Cue diffs ordered by index

- **WHEN** `snapshot.subtitles` contains three cues with indices 2, 0, 1
- **THEN** `score_card.cue_diffs` MUST list indices in order `0, 1, 2`

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