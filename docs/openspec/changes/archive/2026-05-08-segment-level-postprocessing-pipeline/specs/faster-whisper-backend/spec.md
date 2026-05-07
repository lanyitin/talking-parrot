## MODIFIED Requirements

### Requirement: FasterWhisperBackend assembles TranscriptionResult per the backend contract

`FasterWhisperBackend.transcribe()` SHALL consume the segment iterator returned by `WhisperModel.transcribe` and emit one `TranscriptionResult` per yielded segment, in iteration order, satisfying the segment-level rules declared in `transcription-backend`.

For each yielded segment:

- The result's `text` SHALL equal the segment's `text` after `str.strip()` (no cross-segment joining).
- The result's `metrics` SHALL be populated with the segment's raw `avg_logprob`, `compression_ratio`, `no_speech_prob`, plus a locally-computed `repetition_ratio` derived from the segment's stripped text.
- The result's `start_ms` and `end_ms` SHALL be `chunk.start_ms + int(round(segment.start * 1000))` and `chunk.start_ms + int(round(segment.end * 1000))` respectively.

The backend SHALL set every result's `language` to the value from the `info` object returned by `WhisperModel.transcribe` (the second return value), preferring it over the supplied `language` argument so that auto-detection is preserved when `language=None`.

#### Scenario: Auto-detected language surfaced on each result

- **GIVEN** `model.transcribe(...)` returns `(segments, info)` where `info.language == "ja"` and the iterator yields three segments
- **WHEN** `transcribe()` is called with `language=None`
- **THEN** every element of the returned list MUST have `language == "ja"`

#### Scenario: One result per yielded segment

- **GIVEN** the iterator yields two segments with texts `" hello"`, `" world "`
- **WHEN** `FasterWhisperBackend.transcribe()` runs
- **THEN** the returned list MUST have length 2 with `result[0].text == "hello"` and `result[1].text == "world"`

##### Example: empty-iterator return

- **GIVEN** `WhisperModel.transcribe` yields zero segments for the chunk
- **WHEN** `transcribe()` returns
- **THEN** the returned list MUST equal `[]`
