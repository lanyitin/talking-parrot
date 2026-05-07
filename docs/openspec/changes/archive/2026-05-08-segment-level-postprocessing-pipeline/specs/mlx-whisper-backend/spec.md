## MODIFIED Requirements

### Requirement: MLXWhisperBackend assembles TranscriptionResult per the backend contract

`MLXWhisperBackend.transcribe()` SHALL iterate the `segments` field of the value returned by `mlx_whisper.transcribe` and emit one `TranscriptionResult` per element, in iteration order, satisfying the segment-level rules declared in `transcription-backend`.

For each segment dict:

- The result's `text` SHALL equal the segment's `text` after `str.strip()` (no cross-segment joining).
- The result's `metrics` SHALL be populated with the segment's raw `avg_logprob`, `compression_ratio`, `no_speech_prob`, plus a locally-computed `repetition_ratio` derived from the segment's stripped text.
- The result's `start_ms` and `end_ms` SHALL be `chunk.start_ms + int(round(segment["start"] * 1000))` and `chunk.start_ms + int(round(segment["end"] * 1000))` respectively.

The backend SHALL set every result's `language` to the `language` field of the returned dict when present, otherwise to the supplied `language` argument.

#### Scenario: Library-provided language surfaced on each result

- **GIVEN** `mlx_whisper.transcribe(...)` returns a dict with `language="en"` and three segments
- **WHEN** `transcribe()` is called with `language=None`
- **THEN** every element of the returned list MUST have `language == "en"`

#### Scenario: One result per segment dict

- **GIVEN** the returned dict contains two segments with texts `" hello"`, `" world "`
- **WHEN** `MLXWhisperBackend.transcribe()` runs
- **THEN** the returned list MUST have length 2 with `result[0].text == "hello"` and `result[1].text == "world"`
