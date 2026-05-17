## MODIFIED Requirements

### Requirement: AlignmentStage aligns each chunk and shifts timestamps to absolute

For each `result` in `ctx.transcription_results`, the stage SHALL:
1. Read audio bytes via `audio_bytes = audio_reader.read(result.start_ms, result.end_ms)` (the segment's absolute time bounds, NOT the parent chunk's bounds).
2. Call `tokens = backend.align(audio_bytes, audio_reader.sample_rate, result.text)`.
3. Shift each returned token's `start_ms` and `end_ms` by adding `result.start_ms` (the backend returns audio-window-relative timestamps; the stage produces absolute timestamps).

The stage SHALL build the output list in the same order as `ctx.transcription_results`. `result.chunk_index` MAY still be used for diagnostic logging but MUST NOT be used to derive the audio range to read.

#### Scenario: Timestamps shifted by result start, not chunk start

- **GIVEN** a `TranscriptionResult` with `start_ms = 12_500`, `end_ms = 14_000` (its parent chunk has `start_ms=10_000, end_ms=20_000`) and a backend returning a single token with `start_ms=100, end_ms=500`
- **WHEN** the stage processes that result
- **THEN** the absolute token MUST have `start_ms = 12_600` and `end_ms = 13_000`
- **AND** the audio reader MUST have been called with `(12_500, 14_000)` (not `(10_000, 20_000)`)

#### Scenario: Multiple segments from one chunk aligned independently

- **GIVEN** two `TranscriptionResult` instances with the same `chunk_index` but `start_ms`/`end_ms` `(12_000, 13_000)` and `(13_500, 14_500)`
- **WHEN** the stage processes both
- **THEN** the audio reader MUST have been called twice with each segment's bounds, and each result's aligned tokens MUST be shifted by that result's `start_ms`
