## MODIFIED Requirements

### Requirement: TranscriptionResult exposes metrics for condition evaluation

The `TranscriptionResult` dataclass SHALL expose a `metrics: TranscriptionMetrics` field. `TranscriptionMetrics` SHALL contain at minimum `avg_logprob: float`, `compression_ratio: float`, `no_speech_prob: float`, `repetition_ratio: float`. `TranscriptionResult` SHALL also expose `chunk_index`, `start_ms`, `end_ms`, `text`, `language`, `model_used`, and `aligned_tokens: list[AlignedToken] | None`.

`start_ms` and `end_ms` SHALL represent the absolute time bounds of the Whisper internal segment that produced this result, NOT the bounds of the parent `Chunk`. Multiple `TranscriptionResult` instances MAY share the same `chunk_index`; their `start_ms`/`end_ms` ranges SHALL be non-overlapping and ordered ascending within a single chunk. `metrics` SHALL carry the segment's raw values, not chunk-level aggregates.

#### Scenario: Metrics are accessible by attribute name

- **WHEN** `result.metrics.avg_logprob` is read
- **THEN** the value MUST be a float (not a dict lookup)

#### Scenario: Segment bounds within parent chunk

- **GIVEN** a chunk with `start_ms=10000, end_ms=20000` and three `TranscriptionResult` instances sharing this `chunk_index`
- **WHEN** their `start_ms`/`end_ms` are inspected
- **THEN** each MUST satisfy `chunk.start_ms <= result.start_ms < result.end_ms <= chunk.end_ms`
- **AND** the three results MUST be sorted ascending by `start_ms` and have non-overlapping ranges
