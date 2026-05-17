## ADDED Requirements

### Requirement: ConfigLoader parses YAML into PipelineConfig

The system SHALL provide a `ConfigLoader.load(path: str) -> PipelineConfig` method that reads a YAML file from disk and returns a strongly-typed `PipelineConfig` (pydantic model). YAML keys MUST map to the `PipelineConfig` schema declared in `pipeline-data-models`.

#### Scenario: Valid YAML loads successfully

- **WHEN** `ConfigLoader.load("config.yaml")` is called with a YAML file containing valid `expected_language`, `vad`, `chunking`, `transcribing`, `align`, and `post_processing` sections
- **THEN** the method MUST return a `PipelineConfig` instance with all sub-configs populated as their respective typed objects

### Requirement: ConfigLoader rejects unknown fields

The `ConfigLoader` SHALL reject unknown top-level or nested fields by raising `pydantic.ValidationError`. This prevents silent typos in YAML keys from being ignored.

#### Scenario: Unknown field rejected

- **WHEN** the YAML contains an unknown field (e.g., `vad.activty_threshold` instead of `activity_threshold`)
- **THEN** `ConfigLoader.load()` MUST raise `pydantic.ValidationError` identifying the offending field path

### Requirement: ConfigLoader warns on inconsistent VAD/chunking durations

When `vad.enabled` is true, `chunking.enabled` is true, and `vad.max_speech_duration_ms > chunking.max_chunk_seconds * 1000`, `ConfigLoader.load()` SHALL emit a WARNING log identifying both values and explaining that the chunker may have to perform a hard cut mid-word. The loader MUST NOT raise an error in this case.

#### Scenario: Inconsistent durations log warning

- **WHEN** `vad.max_speech_duration_ms = 60000` and `chunking.max_chunk_seconds = 30`
- **THEN** `ConfigLoader.load()` MUST emit a WARNING log mentioning both values and MUST still return a valid `PipelineConfig`

### Requirement: PipelineConfig sub-section optionality

`PipelineConfig.vad`, `PipelineConfig.chunking`, `PipelineConfig.align`, and `PipelineConfig.post_processing` SHALL be `Optional` (allow `None`). When a sub-section is `None`, the corresponding stage MUST behave as if `enabled = False`. `PipelineConfig.transcribing` SHALL be a non-empty list (validated by pydantic).

#### Scenario: Empty transcribing list rejected

- **WHEN** YAML defines `transcribing: []`
- **THEN** `ConfigLoader.load()` MUST raise `pydantic.ValidationError`

#### Scenario: Missing optional section treated as disabled

- **WHEN** YAML omits the `vad` section entirely
- **THEN** `PipelineConfig.vad` MUST be `None` and `VADStage.process()` MUST return its input context unchanged

### Requirement: First transcribing step condition must be "true"

`ConfigLoader` SHALL validate that `transcribing[0].condition` equals the literal string `"true"` (case-sensitive). Initial transcription metrics are empty, so any other expression would reference undefined fields.

#### Scenario: Non-true initial condition rejected

- **WHEN** YAML defines `transcribing[0].condition: "avg_logprob < -1.0"`
- **THEN** `ConfigLoader.load()` MUST raise `pydantic.ValidationError` identifying the first transcribing step
