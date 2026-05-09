## ADDED Requirements

### Requirement: CLI entry point and sample discovery

The system SHALL expose a runnable module `talking_parrot.regression` such that `uv run python -m talking_parrot.regression` discovers every `test-samples/<sample>/descriptor.yml` under the configured samples directory and iterates each declared variant. The samples directory SHALL default to `test-samples/` and SHALL be overridable via the CLI flag `--samples-dir`. Each descriptor MUST yield one `SampleDescriptor` value object exposing `sample_id`, `base_file`, `reference_text`, and `variants`.

#### Scenario: Discover declared samples

- **WHEN** `RegressionRunner.discover_samples` is invoked against a directory containing one descriptor with two variants
- **THEN** the runner MUST return one `SampleDescriptor` whose `variants` list has length 2 in declared order

#### Scenario: Missing samples directory raises

- **WHEN** the CLI is invoked with `--samples-dir` pointing to a non-existent path
- **THEN** the process MUST exit with code 2 and MUST log a single error message via stdlib `logging`

### Requirement: Per-variant pipeline orchestration

`RegressionRunner` SHALL invoke the existing `talking_parrot.pipeline.orchestrator` once per variant, capture the resulting `ProjectSnapshot` (consumed from `talking_parrot.shared`), and produce a `RunResult` carrying the `ProjectSnapshot`, the `SampleDescriptor`, the variant file name, and an ISO-8601 `run_timestamp`. The runner MUST cache the orchestrator instance across variants within a single CLI invocation. The runner MUST NOT subprocess into another Python interpreter.

#### Scenario: Single orchestrator instance reused

- **WHEN** `RegressionRunner.run_all` is invoked over two variants of the same sample with a stub orchestrator that records its constructions
- **THEN** the orchestrator MUST be constructed exactly once

#### Scenario: Missing audio file produces skipped verdict

- **WHEN** a variant's audio file does not exist on disk
- **THEN** the produced `RunResult` MUST carry verdict `skipped` and the process MUST NOT exit with code 1 unless `--strict-missing` is set

### Requirement: Verdict thresholds and exit code

The CLI SHALL exit with code `0` when every sample's verdict is one of `stable`, `improved`, `bootstrapped`, `skipped`, or `unscored`; with code `1` when any sample's verdict is `regressed`; and with code `2` on configuration or I/O failure. A run is `regressed` WHEN current `MetricBundle.cer` exceeds baseline `MetricBundle.cer` by more than `cer_tolerance` (default `0.02`) OR current `MetricBundle.confidence_mean` is less than baseline `MetricBundle.confidence_mean` by more than `confidence_tolerance` (default `0.05`). Both tolerances MUST be overridable via `--cer-tolerance` and `--confidence-tolerance`.

#### Scenario: CER above tolerance triggers regression

- **WHEN** baseline CER is `0.04`, current CER is `0.10`, and `cer_tolerance` is `0.02`
- **THEN** the verdict MUST equal `regressed` and the CLI MUST exit with code `1`

#### Scenario: Confidence drop above tolerance triggers regression

- **WHEN** baseline `confidence_mean` is `0.90`, current is `0.80`, `confidence_tolerance` is `0.05`, and CER is unchanged
- **THEN** the verdict MUST equal `regressed`

#### Scenario: All samples within tolerance exits zero

- **WHEN** every sample yields verdict `stable` or `improved`
- **THEN** the CLI MUST exit with code `0`

### Requirement: Reset-baseline flag

The CLI SHALL accept `--reset-baseline`. When supplied, every current `ScoreCard` MUST overwrite the stored baseline via the configured `BaselineStore`, every verdict MUST be reported as `bootstrapped`, and the CLI MUST exit with code `0` regardless of CER or confidence deltas.

#### Scenario: Reset overwrites baselines

- **WHEN** the CLI is invoked with `--reset-baseline` against a sample whose existing baseline has CER `0.01` and the current run has CER `0.50`
- **THEN** the stored baseline MUST be replaced with the current `ScoreCard` and the CLI MUST exit with code `0`
