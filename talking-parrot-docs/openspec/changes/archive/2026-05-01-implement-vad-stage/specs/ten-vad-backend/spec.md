## ADDED Requirements

### Requirement: TenVADBackend wraps ten_vad.TenVad and returns per-frame probabilities

The system SHALL provide `TenVADBackend` implementing `VADBackend` with:
- `name` property returning `"ten_vad"`
- Constructor accepting `hop_size: int = 256` and `threshold: float = 0.5`
- `analyze()` splitting audio into chunks of `hop_size` samples, calling `TenVad.process()` on each chunk, and returning one `RawVadFrame` per chunk

The `TenVad` instance SHALL be lazy-initialised on the first `analyze()` call and cached for subsequent calls.

#### Scenario: analyze returns one frame per hop

- **WHEN** `analyze()` is called with audio of N samples at 16000 Hz
- **THEN** it returns `floor(N / hop_size)` frames

##### Example: frame count for common audio lengths

| audio samples | hop_size | expected frame count |
|---------------|----------|----------------------|
| 256           | 256      | 1                    |
| 512           | 256      | 2                    |
| 1000          | 256      | 3                    |
| 8000          | 256      | 31                   |

#### Scenario: frame time_ms matches chunk position

- **WHEN** `analyze()` is called with `hop_size=256` and `sample_rate=16000`
- **THEN** the frame at index `i` has `time_ms = i * 256 / 16000 * 1000 = i * 16`

##### Example: time_ms for first four frames

| frame index | hop_size | sample_rate | expected time_ms |
|-------------|----------|-------------|-----------------|
| 0           | 256      | 16000       | 0               |
| 1           | 256      | 16000       | 16              |
| 2           | 256      | 16000       | 32              |
| 3           | 256      | 16000       | 48              |

#### Scenario: prob reflects TenVad result.probability

- **WHEN** `TenVad.process()` returns `result.probability = 0.87` for a chunk
- **THEN** the corresponding `RawVadFrame.prob` equals `0.87`
