## ADDED Requirements

### Requirement: SileroVADBackend wraps silero_vad and returns per-frame probabilities

The system SHALL provide `SileroVADBackend` implementing `VADBackend` with:
- `name` property returning `"silero_vad"`
- Constructor accepting `chunk_size: int = 512`
- `analyze()` splitting audio into chunks of `chunk_size` samples, calling the Silero model on each chunk, and returning one `RawVadFrame` per chunk

The Silero model SHALL be lazy-loaded via `silero_vad.load_silero_vad()` on the first `analyze()` call and cached for subsequent calls.

#### Scenario: analyze returns one frame per chunk

- **WHEN** `analyze()` is called with audio of N samples
- **THEN** it returns `floor(N / chunk_size)` frames

##### Example: frame count for common audio lengths

| audio samples | chunk_size | expected frame count |
|---------------|------------|----------------------|
| 512           | 512        | 1                    |
| 1024          | 512        | 2                    |
| 1500          | 512        | 2                    |
| 16000         | 512        | 31                   |

#### Scenario: frame time_ms matches chunk position

- **WHEN** `analyze()` is called with `chunk_size=512` and `sample_rate=16000`
- **THEN** the frame at index `i` has `time_ms = i * 512 / 16000 * 1000 = i * 32`

##### Example: time_ms for first four frames

| frame index | chunk_size | sample_rate | expected time_ms |
|-------------|------------|-------------|-----------------|
| 0           | 512        | 16000       | 0               |
| 1           | 512        | 16000       | 32              |
| 2           | 512        | 16000       | 64              |
| 3           | 512        | 16000       | 96              |

#### Scenario: prob reflects Silero model output

- **WHEN** the Silero model returns probability `0.72` for a chunk
- **THEN** the corresponding `RawVadFrame.prob` equals `0.72`
