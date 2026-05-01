## Why

The pipeline's VAD stage produces a list of `VadSegment` objects but nothing yet converts them into transcription-ready `Chunk` objects. Without `ChunkingStage`, the transcription stage has no input and the pipeline cannot run end-to-end.

## What Changes

- A new `ChunkingStage` class is added under `src/talking_parrot/stages/` that implements `PipelineStage` and converts `ctx.vad_segments` into `ctx.chunks`.
- The stage uses a greedy accumulation algorithm: segments are appended to the current chunk until the next segment would cause the chunk to exceed `max_chunk_seconds`. When that threshold is reached, the current chunk is finalised and a new one begins.
- Each segment boundary receives a configurable `silence_pad_ms` of extra time, expanding `Chunk.start_ms` and `Chunk.end_ms` slightly beyond the raw segment span to avoid clipping audio at boundaries.
- A hard-cut fallback handles any single `VadSegment` whose duration exceeds `max_chunk_seconds` by splitting it into consecutive fixed-length sub-chunks of `max_chunk_seconds * 1000 ms` (each carrying the original segment as its sole `source_segment`).
- `ChunkingConfig` gains a new field `silence_pad_ms: int = 50` to support the boundary-padding behaviour.

## Capabilities

### New Capabilities

- `chunking-stage`: Greedy-merge `VadSegment` list into `Chunk` list, with silence padding and hard-cut fallback for oversized segments.

### Modified Capabilities

- `pipeline-config`: Add `silence_pad_ms: int` field to `ChunkingConfig`.

## Impact

- Affected specs: `chunking-stage` (new), `pipeline-config` (modified — new field)
- Affected code:
  - New: `src/talking_parrot/stages/chunking_stage.py`, `tests/unit/stages/test_chunking_stage.py`
  - Modified: `src/talking_parrot/config/models.py`, `src/talking_parrot/stages/__init__.py`
  - Removed: (none)
