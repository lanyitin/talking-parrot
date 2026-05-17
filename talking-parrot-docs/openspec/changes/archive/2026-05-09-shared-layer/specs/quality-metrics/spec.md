## ADDED Requirements

### Requirement: ScoreCard value object

The system SHALL provide a frozen dataclass `ScoreCard` in `src/talking_parrot/shared/metrics.py` with fields `sample_id: str`, `overall_score: float`, `metric_bundle: MetricBundle`, and `cue_diffs: list[CueDiff]`. `cue_diffs` MUST default to an empty list. The dataclass MUST be declared with `frozen=True`.

#### Scenario: Construction with defaults

- **WHEN** `ScoreCard(sample_id="sample1", overall_score=0.0, metric_bundle=mb)` is constructed
- **THEN** `cue_diffs` MUST equal `[]`

#### Scenario: Mutation rejected

- **WHEN** code attempts `card.overall_score = 1.0` after construction
- **THEN** the system MUST raise `dataclasses.FrozenInstanceError`

### Requirement: MetricBundle value object

The system SHALL provide a frozen dataclass `MetricBundle` in `src/talking_parrot/shared/metrics.py` with fields `cer: float`, `confidence_mean: float`, `confidence_p10: float`, `repetition_ratio_mean: float`, `no_speech_prob_mean: float`. All fields MUST be required (no defaults).

#### Scenario: All fields required

- **WHEN** code constructs `MetricBundle(cer=0.1, confidence_mean=0.9, confidence_p10=0.7, repetition_ratio_mean=0.0, no_speech_prob_mean=0.05)`
- **THEN** the construction MUST succeed and every field MUST be readable on the instance

### Requirement: CueDiff value object

The system SHALL provide a frozen dataclass `CueDiff` in `src/talking_parrot/shared/metrics.py` with fields `index: int`, `reference_text: str`, `hypothesis_text: str`, `cer: float`, `start_ms_delta: int`, `end_ms_delta: int`. The dataclass MUST be declared with `frozen=True`.

#### Scenario: CueDiff carries reference and hypothesis

- **WHEN** `CueDiff(index=0, reference_text="hello", hypothesis_text="hallo", cer=0.2, start_ms_delta=5, end_ms_delta=-3)` is constructed
- **THEN** `diff.reference_text` MUST equal `"hello"` and `diff.hypothesis_text` MUST equal `"hallo"`

### Requirement: No scoring logic in this capability

The metrics module SHALL contain only value-object definitions in this change. No function, method, or classmethod that computes a score, CER, or any aggregate from input data SHALL be added to `src/talking_parrot/shared/metrics.py` as part of this change. Scoring logic belongs to a future regression-runner change.

#### Scenario: Module exposes only dataclasses and re-exports

- **WHEN** the public symbols of `talking_parrot.shared.metrics` are enumerated
- **THEN** every public symbol MUST be either a dataclass type (`ScoreCard`, `MetricBundle`, `CueDiff`) or a typing import; no callable producing scores MUST be present
