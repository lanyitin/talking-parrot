## ADDED Requirements

### Requirement: VADBackend interface defines the contract for all VAD backends

The system SHALL define a `VADBackend` abstract base class with two abstract members:
- `name: str` (read-only property) — unique identifier for the backend, used as the formula variable prefix
- `analyze(audio_data: bytes, sample_rate: int) -> List[RawVadFrame]` — analyses the full audio and returns per-frame speech probabilities

All concrete VAD backends SHALL inherit from `VADBackend` and implement both members.

#### Scenario: Backend returns per-frame probabilities for non-silent audio

- **WHEN** `analyze()` is called with PCM audio containing speech
- **THEN** it returns a non-empty `List[RawVadFrame]` where each frame has `time_ms >= 0` and `prob` in `[0.0, 1.0]`

#### Scenario: Backend returns frames in chronological order

- **WHEN** `analyze()` is called with any audio
- **THEN** the returned frames are sorted by ascending `time_ms`

### Requirement: RawVadFrame is an immutable value object

The system SHALL provide a `RawVadFrame` frozen dataclass with:
- `time_ms: int` — start time of the frame in milliseconds
- `prob: float` — speech probability in range `[0.0, 1.0]`

#### Scenario: RawVadFrame cannot be mutated after construction

- **WHEN** a `RawVadFrame` is constructed
- **THEN** attempting to assign to any field raises `FrozenInstanceError`

##### Example: valid frame construction

| time_ms | prob | Valid? |
|---------|------|--------|
| 0       | 0.0  | Yes    |
| 160     | 0.95 | Yes    |
| 320     | 1.0  | Yes    |
