## ADDED Requirements

### Requirement: AlignmentBackend interface declares language, granularity, and align

The system SHALL provide an abstract base class `AlignmentBackend` declaring:
- A read-only abstract `language: str` property identifying the language code the backend serves (e.g., `"en"`, `"ja"`).
- A read-only abstract `granularity: AlignmentGranularity` property declaring whether the backend produces word-level or character-level tokens.
- An abstract method `align(audio_data: bytes, sample_rate: int, transcript: str) -> list[AlignedToken]` that returns chunk-relative `AlignedToken` instances (start_ms / end_ms measured from the start of the supplied audio).

`AlignmentBackend` SHALL NOT be instantiable directly. Concrete subclasses MUST implement all three members.

#### Scenario: Direct instantiation rejected

- **WHEN** code attempts to call `AlignmentBackend()` directly
- **THEN** Python MUST raise `TypeError` because the class is abstract

#### Scenario: Concrete subclass satisfies interface

- **WHEN** a subclass implements `language`, `granularity`, and `align` with the required signatures
- **THEN** the subclass MUST be instantiable and `isinstance(instance, AlignmentBackend)` MUST return `True`

### Requirement: AlignmentBackend.align returns chunk-relative timestamps

The list returned by `align(audio_data, sample_rate, transcript)` SHALL contain `AlignedToken` instances whose `start_ms` and `end_ms` are measured from the first sample of `audio_data` (i.e., chunk-relative, not absolute). The caller (`AlignmentStage`) is responsible for shifting timestamps to absolute time by adding the chunk's `start_ms`.

Token order MUST match the natural reading order of `transcript`: left-to-right for English (after lowercasing and splitting on whitespace) and codepoint order for Japanese (after stripping ASCII whitespace).

#### Scenario: Returned timestamps are within audio window

- **GIVEN** `audio_data` representing a 5000 ms (`5_000`) audio window at `sample_rate=16000`
- **WHEN** `align()` returns successfully
- **THEN** every returned `AlignedToken.start_ms` MUST satisfy `0 <= start_ms <= end_ms <= 5_000`

### Requirement: Shared CTC kernel performs forced alignment

The system SHALL provide an internal `ctc_align(emissions, dictionary, transcript_tokens, blank_id, frame_rate_hz, *, segment_offset_ms) -> list[AlignedToken]` helper used by all `AlignmentBackend` implementations. The kernel SHALL:

1. Map each `transcript_tokens[i]` to its dictionary index when present; tokens absent from the dictionary MUST be assigned a wildcard column equal to `max(emissions[t, j!=blank_id])` per frame.
2. Compute a trellis `T[t, j]` via the standard CTC dynamic-programming recurrence, with `T[0, 0] = 0` and `T[0, j>0] = -inf`.
3. Backtrack the optimal path to produce `(token_index, time_index, score)` triples in chronological order.
4. Collapse runs of identical `token_index` into segments and convert each segment to an `AlignedToken` with `start_ms = segment_offset_ms + start_frame * 1000 / frame_rate_hz` and `end_ms = segment_offset_ms + end_frame * 1000 / frame_rate_hz`, using the mean per-frame score as `score`.

Tokens that fail dictionary lookup AND whose wildcard score is below `-inf` (i.e., no usable column) MUST be returned with `start_ms = NaN`, `end_ms = NaN`, `score = 0.0`. After all token segments are produced, the kernel SHALL run a nearest-neighbour `interpolate_nans` pass that fills NaN start_ms / end_ms values from the closest non-NaN neighbours. If every token is NaN, the kernel SHALL set `start_ms = segment_offset_ms`, `end_ms = segment_offset_ms` for every token and `score = 0.0`.

#### Scenario: Empty transcript yields empty token list

- **WHEN** `ctc_align` is called with `transcript_tokens=[]`
- **THEN** the function MUST return `[]` without computing any trellis

#### Scenario: NaN interpolation fills missing timestamps

- **GIVEN** three tokens where token 1 has NaN start/end and tokens 0 and 2 have concrete start/end values `(start_ms=100, end_ms=200)` and `(start_ms=400, end_ms=500)`
- **WHEN** `interpolate_nans` runs
- **THEN** token 1's `start_ms` and `end_ms` MUST be filled with values from the nearest non-NaN neighbour (specifically: `start_ms` becomes `200` and `end_ms` becomes `400`, the nearest preceding `end_ms` and nearest following `start_ms` respectively)
