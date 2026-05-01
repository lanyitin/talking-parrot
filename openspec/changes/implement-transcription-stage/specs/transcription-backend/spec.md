## ADDED Requirements

### Requirement: TranscriptionBackend interface defines the contract for all transcription backends

The system SHALL provide an abstract base class `TranscriptionBackend` declaring:
- A read-only abstract `name: str` property identifying the backend (e.g., `"faster-whisper"`, `"mlx-whisper"`).
- An abstract method `transcribe(audio_path: Path, chunk: Chunk, model: str, language: str | None) -> TranscriptionResult` that transcribes the audio window `[chunk.start_ms, chunk.end_ms]` using the named model and returns a populated `TranscriptionResult`.

`TranscriptionBackend` SHALL NOT be instantiable directly. Concrete subclasses MUST implement both members.

#### Scenario: Direct instantiation rejected

- **WHEN** code attempts to call `TranscriptionBackend()` directly
- **THEN** Python MUST raise `TypeError` because the class is abstract

#### Scenario: Concrete subclass satisfies interface

- **WHEN** a subclass implements `name` as a property and `transcribe` with the required signature
- **THEN** the subclass MUST be instantiable and `isinstance(instance, TranscriptionBackend)` MUST return `True`

### Requirement: TranscriptionResult populated by backend

A `TranscriptionBackend.transcribe()` call SHALL return a `TranscriptionResult` whose:
- `chunk_index` equals `chunk.index`.
- `start_ms` equals `chunk.start_ms` and `end_ms` equals `chunk.end_ms` (taken from the chunk window, not from internal segment timestamps).
- `text` is the joined, stripped transcription text for the window.
- `language` is the language code applied (BCP-47 or two-letter code as supplied by the underlying library).
- `model_used` equals the `model` argument passed to `transcribe()`.
- `metrics` is a populated `TranscriptionMetrics`.
- `aligned_tokens` is `None` (alignment is the responsibility of `AlignmentStage`).

#### Scenario: Result fields reflect chunk window

- **GIVEN** a chunk with `index=2`, `start_ms=10000`, `end_ms=20000`
- **WHEN** any concrete backend's `transcribe()` returns successfully
- **THEN** the returned `TranscriptionResult` MUST have `chunk_index=2`, `start_ms=10000`, `end_ms=20000`, and `aligned_tokens is None`

### Requirement: TranscriptionMetrics contract for cascade conditions

Every `TranscriptionBackend` SHALL compute the four `TranscriptionMetrics` fields with these portable rules so that cascade conditions written against one backend behave consistently on the other:
- `avg_logprob` — mean of internal segment `avg_logprob` values, weighted by each segment's duration in milliseconds.
- `compression_ratio` — mean of internal segment `compression_ratio` values, weighted by each segment's duration in milliseconds.
- `no_speech_prob` — maximum of internal segment `no_speech_prob` values across the chunk.
- `repetition_ratio` — `1.0 - (unique_token_count / total_token_count)` where tokens are produced by whitespace-splitting the joined `text`. When `total_token_count` is `0`, the value MUST be `0.0`.

#### Scenario: Empty text yields zero repetition ratio

- **GIVEN** a chunk for which the backend produces empty text
- **WHEN** `transcribe()` returns
- **THEN** `result.metrics.repetition_ratio` MUST equal `0.0`

##### Example: weighted-mean avg_logprob

- **GIVEN** internal segments `[(duration_ms=1000, avg_logprob=-0.5), (duration_ms=3000, avg_logprob=-0.1)]`
- **WHEN** the backend computes metrics
- **THEN** `metrics.avg_logprob` MUST equal `(-0.5 * 1000 + -0.1 * 3000) / 4000 = -0.2`

##### Example: max no_speech_prob

- **GIVEN** internal segments with `no_speech_prob` values `[0.05, 0.40, 0.10]`
- **WHEN** the backend computes metrics
- **THEN** `metrics.no_speech_prob` MUST equal `0.40`
