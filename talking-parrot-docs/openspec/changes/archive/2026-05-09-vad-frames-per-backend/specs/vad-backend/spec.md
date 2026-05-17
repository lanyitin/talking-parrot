## MODIFIED Requirements

### Requirement: RawVadFrame is an immutable value object

The system SHALL provide a `RawVadFrame` frozen dataclass with:
- `time_ms: int` — start time of the frame in milliseconds
- `prob: float` — speech probability in range `[0.0, 1.0]`
- `backend: str` — identifier of the producing backend; for real backends this MUST equal the backend's `name` attribute (e.g., `"silero_vad"`, `"ten_vad"`); the literal string `"composite"` is reserved for the unified composite timeline emitted by `VADStage`; the literal string `"unknown"` is reserved for frames loaded from legacy `.tp` files that predate this field.

All three fields are required at construction. `backend` MUST be a non-empty string.

#### Scenario: RawVadFrame cannot be mutated after construction

- **WHEN** a `RawVadFrame` is constructed with `time_ms=0, prob=0.5, backend="silero_vad"`
- **THEN** attempting to assign to any field raises `FrozenInstanceError`

#### Scenario: RawVadFrame requires a backend tag at construction

- **WHEN** code constructs `RawVadFrame(time_ms=0, prob=0.5)` without supplying `backend`
- **THEN** the call raises `TypeError`

##### Example: valid frame construction

| time_ms | prob | backend       | Valid? |
|---------|------|---------------|--------|
| 0       | 0.0  | "silero_vad"  | Yes    |
| 160     | 0.95 | "ten_vad"     | Yes    |
| 320     | 1.0  | "composite"   | Yes    |
| 480     | 0.5  | "unknown"     | Yes    |
| 0       | 0.5  | ""            | No (empty backend) |
