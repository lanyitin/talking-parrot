## MODIFIED Requirements

### Requirement: TranscriptionBackend interface defines the contract for all transcription backends

The system SHALL provide an abstract base class `TranscriptionBackend` declaring:
- A read-only abstract `name: str` property identifying the backend (e.g., `"faster-whisper"`, `"mlx-whisper"`).
- An abstract method `transcribe(audio_path: Path, chunk: Chunk, model: str, language: str | None) -> list[TranscriptionResult]` that transcribes the audio window `[chunk.start_ms, chunk.end_ms]` using the named model and returns a populated list of `TranscriptionResult`, with one element per Whisper internal segment, in temporal order.

`TranscriptionBackend` SHALL NOT be instantiable directly. Concrete subclasses MUST implement both members.

The returned list MAY be empty when the underlying model produces no segments for the chunk window; callers MUST handle the empty case.

#### Scenario: Direct instantiation rejected

- **WHEN** code attempts to call `TranscriptionBackend()` directly
- **THEN** Python MUST raise `TypeError` because the class is abstract

#### Scenario: Concrete subclass satisfies interface

- **WHEN** a subclass implements `name` as a property and `transcribe` with the required signature
- **THEN** the subclass MUST be instantiable and `isinstance(instance, TranscriptionBackend)` MUST return `True`

#### Scenario: Empty segment list permitted

- **GIVEN** a chunk whose audio yields no usable Whisper segments
- **WHEN** `transcribe()` returns
- **THEN** the returned `list[TranscriptionResult]` MAY have length 0 and the caller MUST treat that as a valid (no-op) outcome

### Requirement: TranscriptionResult populated by backend

A `TranscriptionBackend.transcribe()` call SHALL return a `list[TranscriptionResult]`. For each element of the list:

- `chunk_index` equals `chunk.index` (every result in the list shares the same `chunk_index`).
- `start_ms` equals `chunk.start_ms + int(round(segment.start_seconds * 1000))` where `segment` is the Whisper internal segment that produced this result.
- `end_ms` equals `chunk.start_ms + int(round(segment.end_seconds * 1000))` for the same segment.
- `text` is the segment's text, stripped of leading and trailing whitespace.
- `language` is the language code applied (BCP-47 or two-letter code as supplied by the underlying library).
- `model_used` equals the `model` argument passed to `transcribe()`.
- `metrics` is a populated `TranscriptionMetrics` carrying the segment's raw values (no chunk-level aggregation).
- `aligned_tokens` is `None` (alignment is the responsibility of `AlignmentStage`).

The list SHALL be ordered by ascending `start_ms`.

#### Scenario: Result fields reflect segment window

- **GIVEN** a chunk with `index=2`, `start_ms=10000`, `end_ms=20000` and Whisper internal segments `[(start=0.0, end=2.0), (start=2.5, end=5.0)]`
- **WHEN** any concrete backend's `transcribe()` returns successfully
- **THEN** the returned list MUST have length 2 with `chunk_index=2` for both, `start_ms=[10000, 12500]`, `end_ms=[12000, 15000]`, and `aligned_tokens is None` for each

### Requirement: TranscriptionMetrics contract for cascade conditions

Every `TranscriptionBackend` SHALL populate `TranscriptionMetrics` on each per-segment `TranscriptionResult` with raw Whisper-segment values, not chunk-level aggregates:

- `avg_logprob` — the segment's `avg_logprob` as reported by the underlying library.
- `compression_ratio` — the segment's `compression_ratio` as reported by the underlying library.
- `no_speech_prob` — the segment's `no_speech_prob` as reported by the underlying library.
- `repetition_ratio` — `1.0 - (unique_token_count / total_token_count)` where tokens are produced by whitespace-splitting the segment's `text`. When `total_token_count` is `0`, the value MUST be `0.0`.

Aggregation across segments for cascade decisions is the responsibility of `TranscriptionStage`, not of the backend (see `transcription-stage`).

#### Scenario: Empty text yields zero repetition ratio

- **GIVEN** a segment whose backend produces empty text
- **WHEN** `transcribe()` returns the result for that segment
- **THEN** `result.metrics.repetition_ratio` MUST equal `0.0`

#### Scenario: Per-segment values not averaged

- **GIVEN** Whisper internal segments with `avg_logprob` values `[-0.5, -0.1]` and durations `[1000 ms, 3000 ms]`
- **WHEN** the backend returns the per-segment result list
- **THEN** the two `TranscriptionResult` instances MUST carry `metrics.avg_logprob == -0.5` and `metrics.avg_logprob == -0.1` respectively (no weighted mean applied)
