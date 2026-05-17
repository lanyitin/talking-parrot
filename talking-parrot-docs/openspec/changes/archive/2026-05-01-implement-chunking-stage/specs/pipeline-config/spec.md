## ADDED Requirements

### Requirement: ChunkingConfig has silence_pad_ms field

The system SHALL add a `silence_pad_ms: int` field to `ChunkingConfig` with a default value of `50`. The field MUST be accepted by the YAML loader and MUST be validated to reject negative values.

#### Scenario: Default value

- **WHEN** `ChunkingConfig` is instantiated without specifying `silence_pad_ms`
- **THEN** `config.chunking.silence_pad_ms` MUST equal `50`

#### Scenario: Explicit value from YAML

- **WHEN** the config YAML contains `chunking: { silence_pad_ms: 100 }`
- **THEN** `config.chunking.silence_pad_ms` MUST equal `100`
