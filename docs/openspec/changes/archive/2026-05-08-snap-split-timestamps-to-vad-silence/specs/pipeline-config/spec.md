## ADDED Requirements

### Requirement: PostProcessingConfig split-time snap radius field

`PostProcessingConfig` SHALL expose an additional integer field `split_time_snap_radius_ms` with default value `250` that controls the search radius used by `VadAlignedSplitTimePolicy` when adjusting split-cue timestamps to nearby VAD silences. The value MUST be in the closed interval `[0, 2000]`. The bound SHALL be enforced via a pydantic field validator; out-of-range values MUST raise `pydantic.ValidationError`.

A value of `0` SHALL be interpreted by the `DefaultGranularityAwareProcessorFactory` as a request to disable VAD-aligned snapping and substitute `LinearSplitTimePolicy()`.

#### Scenario: Default value is 250

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `PostProcessingConfig` MUST have `split_time_snap_radius_ms == 250`

#### Scenario: Negative value rejected

- **GIVEN** YAML with `post_processing.split_time_snap_radius_ms: -1`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

#### Scenario: Out-of-range value rejected

- **GIVEN** YAML with `post_processing.split_time_snap_radius_ms: 2500`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

#### Scenario: Boundary values accepted

- **GIVEN** YAML with `post_processing.split_time_snap_radius_ms: 0` and a separate config with `post_processing.split_time_snap_radius_ms: 2000`
- **WHEN** `ConfigLoader.load()` parses each
- **THEN** both MUST succeed without raising

##### Example: Valid range table

| YAML value | outcome             |
| ---------- | ------------------- |
| `0`        | accepted (disables) |
| `250`      | accepted (default)  |
| `2000`     | accepted (max)      |
| `-1`       | rejected            |
| `2001`     | rejected            |

<!-- @trace
source: snap-split-timestamps-to-vad-silence
-->
