## ADDED Requirements

### Requirement: BaselineStore protocol

The system SHALL define a `typing.Protocol` named `BaselineStore` in `src/talking_parrot/regression/baseline.py` exposing two methods: `load(sample_id: str) -> ScoreCard | None` and `save(sample_id: str, card: ScoreCard) -> None`. The protocol MUST be runtime-checkable via `@runtime_checkable`. `RegressionRunner` MUST depend on this protocol rather than on any concrete class.

#### Scenario: Protocol is runtime-checkable

- **WHEN** an in-memory test double exposes `load` and `save` methods with the declared signatures
- **THEN** `isinstance(double, BaselineStore)` MUST return `True`

### Requirement: JsonBaselineStore filesystem layout

The system SHALL provide a concrete `JsonBaselineStore(root_dir: Path)` in the same module. `save(sample_id, card)` MUST write JSON to `<root_dir>/<sample_id>/baseline.json` and MUST be atomic: the implementation MUST write to a sibling temporary path then call `os.replace`. `load(sample_id)` MUST return `None` when the file does not exist, and MUST raise `BaselineSchemaError` when the file's `schema_version` field is not `1`.

#### Scenario: Save is atomic

- **WHEN** `save` is invoked and the underlying write to the temporary file completes successfully
- **THEN** the final file at `<root_dir>/<sample_id>/baseline.json` MUST exist and the temporary path MUST NOT remain on disk

#### Scenario: Missing baseline returns None

- **WHEN** `load("never-saved")` is invoked against an empty `root_dir`
- **THEN** the call MUST return `None` and MUST NOT raise

#### Scenario: Unknown schema_version raises

- **WHEN** the on-disk baseline file declares `"schema_version": 999`
- **THEN** `load` MUST raise `BaselineSchemaError`

### Requirement: Baseline JSON schema v1

The on-disk baseline document SHALL conform to schema version `1` and SHALL contain exactly these top-level keys: `schema_version` (integer equal to `1`), `sample_id` (string), `variant_file` (string), `captured_at` (ISO-8601 string), `label` (string or `null`), and `score_card` (object). The `score_card` object MUST serialise every field of `ScoreCard` and `MetricBundle` defined in the `quality-metrics` capability, and `cue_diffs` MUST always be present (empty list when no diffs).

#### Scenario: Round-trip preserves all fields

- **WHEN** a `ScoreCard` with two `CueDiff` entries is saved and then loaded via `JsonBaselineStore`
- **THEN** the returned `ScoreCard` MUST equal the original by value, including the two `CueDiff` entries in the same order

#### Scenario: Empty cue_diffs serialised explicitly

- **WHEN** a `ScoreCard` with `cue_diffs == []` is saved
- **THEN** the resulting JSON file MUST contain the key `cue_diffs` with the value `[]`
