## ADDED Requirements

### Requirement: ChunkingStage greedy accumulation

The system SHALL provide a `ChunkingStage` class that implements `PipelineStage`. When enabled, it SHALL iterate over `ctx.vad_segments` from left to right and greedily accumulate segments into a pending chunk. A segment SHALL be added to the current pending chunk if `(segment.end_ms - pending_start_ms) / 1000 <= config.chunking.max_chunk_seconds`. When adding the next segment would exceed this limit, the pending chunk SHALL be sealed and a new pending chunk SHALL begin with that segment. The final pending chunk SHALL be sealed after all segments are processed.

#### Scenario: Segments fit within max_chunk_seconds

- **WHEN** all `vad_segments` together span fewer than `max_chunk_seconds` seconds
- **THEN** `ctx.chunks` MUST contain exactly one `Chunk` whose `source_segments` equals the full `vad_segments` list

#### Scenario: Segments exceed max_chunk_seconds and are split

- **WHEN** the cumulative span of successive segments surpasses `max_chunk_seconds`
- **THEN** `ctx.chunks` MUST contain multiple `Chunk` objects with non-overlapping `source_segments`, each chunk's span not exceeding `max_chunk_seconds * 1000 ms`

##### Example: three segments, limit 30 s

| segments (start–end ms) | max_chunk_seconds | Expected chunks |
|-------------------------|-------------------|-----------------|
| 0–10 000, 11 000–21 000, 22 000–32 000 | 30 | chunk 0: segs 0–1 (0–21 000 ms); chunk 1: seg 2 (22 000–32 000 ms) |

#### Scenario: Empty vad_segments

- **WHEN** `ctx.vad_segments` is an empty list
- **THEN** `ctx.chunks` MUST be an empty list

---

### Requirement: ChunkingStage hard-cut fallback for oversized segments

When a single `VadSegment` has duration `(end_ms - start_ms) > config.chunking.max_chunk_seconds * 1000 ms`, the system SHALL split it into consecutive sub-chunks of exactly `max_chunk_seconds * 1000 ms` each (except the final sub-chunk which may be shorter). Each sub-chunk SHALL carry the original segment as its sole entry in `source_segments`.

#### Scenario: Oversized segment is split

- **WHEN** a `VadSegment` has duration greater than `max_chunk_seconds * 1000 ms`
- **THEN** the stage MUST emit two or more `Chunk` objects covering the full segment span with no gap and no overlap

##### Example: 75 s segment, limit 30 s

- **GIVEN** one `VadSegment(start_ms=0, end_ms=75_000)` and `max_chunk_seconds=30`
- **WHEN** `ChunkingStage.process(ctx)` runs
- **THEN** three chunks are produced: `[0, 30_000)`, `[30_000, 60_000)`, `[60_000, 75_000)` — each with `source_segments=[original_segment]`

---

### Requirement: ChunkingStage silence_pad expansion

After sealing all chunks, the system SHALL expand each chunk's boundaries by `config.chunking.silence_pad_ms` milliseconds: `start_ms` SHALL be decreased by `silence_pad_ms` (clamped to `0`) and `end_ms` SHALL be increased by `silence_pad_ms` (clamped to `ctx.media_info.duration_ms`).

#### Scenario: Silence pad applied within audio bounds

- **WHEN** `silence_pad_ms=50` and a chunk has `start_ms=100, end_ms=5000`
- **THEN** the returned chunk MUST have `start_ms=50` and `end_ms=5050`

#### Scenario: Silence pad clamped at audio start

- **WHEN** `silence_pad_ms=200` and a chunk has `start_ms=100`
- **THEN** the returned chunk MUST have `start_ms=0` (not negative)

#### Scenario: Silence pad clamped at audio end

- **WHEN** `silence_pad_ms=200` and a chunk has `end_ms` within 100 ms of `ctx.media_info.duration_ms`
- **THEN** the returned chunk's `end_ms` MUST equal `ctx.media_info.duration_ms`

---

### Requirement: ChunkingStage disabled returns context unchanged

When `config.chunking` is `None` or `config.chunking.enabled` is `False`, the system SHALL return the input `ctx` unchanged with no chunks populated and no side effects.

#### Scenario: Stage disabled

- **WHEN** `config.chunking.enabled = False` and `process(ctx)` is invoked with non-empty `vad_segments`
- **THEN** the returned context MUST have `chunks == []` and MUST be the same object or structurally equal to the input

---

### Requirement: ChunkingStage produces zero-indexed contiguous chunk indices

Each `Chunk` emitted by `ChunkingStage` SHALL have an `index` field equal to its position in the output list (0, 1, 2, …).

#### Scenario: Chunk indices are contiguous

- **WHEN** `ChunkingStage` produces N chunks
- **THEN** `[c.index for c in ctx.chunks]` MUST equal `list(range(N))`
