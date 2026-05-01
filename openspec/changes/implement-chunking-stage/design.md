## Context

The pipeline currently runs VAD to produce `VadSegment` objects, but has no stage that converts those segments into `Chunk` objects. `ChunkingStage` fills this gap: it is the second stage in the pipeline (after VAD) and populates `ctx.chunks` so that the transcription stage can iterate over well-scoped audio windows.

Existing foundation:
- `PipelineStage` abstract base in `src/talking_parrot/stages/base.py`
- `VadSegment(start_ms, end_ms, ...)` frozen dataclass in `src/talking_parrot/models/vad.py`
- `Chunk(index, start_ms, end_ms, source_segments)` frozen dataclass in `src/talking_parrot/models/chunk.py`
- `ChunkingConfig(enabled, max_chunk_seconds, overlap_ms)` pydantic model in `src/talking_parrot/config/models.py`
- `PipelineContext` frozen dataclass provides `ctx.vad_segments` and `ctx.chunks`

## Goals / Non-Goals

**Goals:**
- Implement `ChunkingStage` that is enabled/disabled via `config.chunking.enabled`
- Greedy accumulation: add `VadSegment` to an open chunk until the next segment would push it past `max_chunk_seconds * 1000 ms`; then seal the chunk and open a new one
- Apply `silence_pad_ms` to expand each chunk's `start_ms` and `end_ms` by `silence_pad_ms` (clamped to `[0, media_info.duration_ms]`)
- Hard-cut fallback for single segments longer than `max_chunk_seconds * 1000 ms`: split into sub-chunks of `max_chunk_seconds * 1000 ms` each, all carrying the original segment as `source_segments=[segment]`
- Produce zero-indexed `Chunk` objects assigned contiguous indices
- Add `silence_pad_ms: int = 50` to `ChunkingConfig`

**Non-Goals:**
- Re-transcription or retrying logic
- Cross-chunk context passing (overlap_ms behaviour is deferred; the field exists in config but is not used by this stage)
- Merging speech segments that VAD separated by more than the greedy limit
- Any audio I/O (chunks hold only timestamps, no bytes)

## Decisions

### Greedy accumulation strategy

Segments are accumulated left to right. A pending chunk is represented by `(start_ms, end_ms, segments[])`. For each new segment:
- If `pending` is empty, start a new pending chunk with the segment.
- Otherwise, compute `candidate_end = segment.end_ms`. If `(candidate_end - pending.start_ms) / 1000 > max_chunk_seconds`, seal the pending chunk and start a new one with the current segment.
- Otherwise, extend pending: `pending.end_ms = segment.end_ms`, append segment.

Alternative considered — dynamic-programming optimal split: minimises maximum chunk duration across all splits. Rejected because it requires a full pass before emitting any chunk, which complicates streaming integration later, and the greedy approach is sufficient for Whisper which handles variably-sized input.

### silence_pad_ms application

After sealing all chunks, a second pass expands each chunk:
```
chunk.start_ms = max(0, chunk.start_ms - silence_pad_ms)
chunk.end_ms   = min(media_info.duration_ms, chunk.end_ms + silence_pad_ms)
```
`media_info.duration_ms` is read from `ctx.media_info`. This avoids any chunk extending beyond the audio file length.

Alternative considered — applying pad during accumulation: would change the threshold comparison logic (pending.end_ms already includes pad), causing cascading threshold inaccuracies. Rejected.

### Hard-cut fallback for oversized segments

If a single `VadSegment` has duration `(end_ms - start_ms) > max_chunk_seconds * 1000`:
- Compute `step = max_chunk_seconds * 1000`
- Emit sub-chunks: `[seg.start_ms + i*step, min(seg.start_ms + (i+1)*step, seg.end_ms)]` for `i = 0, 1, ...`
- Each sub-chunk carries `source_segments=[original_segment]`

Alternative considered — skipping oversized segments: unacceptable data loss. Rejected.

### ChunkingConfig extension

Add `silence_pad_ms: int = 50` to `ChunkingConfig` in `src/talking_parrot/config/models.py`. The default 50 ms is conservative enough to avoid merging distinct speech regions but wide enough to prevent Whisper from seeing hard cuts at phoneme boundaries.

### Disabled-stage behaviour

When `config.chunking` is `None` or `config.chunking.enabled` is `False`, return `ctx` unchanged (no chunks populated). Downstream stages must handle `ctx.chunks == []`.

## Risks / Trade-offs

[Risk: Silence-pad expansion causes chunk overlap] → Mitigation: padding is small (default 50 ms) and applied independently per chunk after sealing; overlapping boundaries are intentional and acceptable for Whisper.

[Risk: Hard-cut produces a sub-chunk that is still too long] → Mitigation: the split step equals exactly `max_chunk_seconds * 1000 ms`, so no sub-chunk can exceed the limit; only the last sub-chunk may be shorter.

[Risk: `ctx.media_info.duration_ms` is zero or uninitialised] → Mitigation: `min(duration_ms, ...)` clamp degrades gracefully to zero—a pathological input that will be caught by upstream validation before chunking runs.
