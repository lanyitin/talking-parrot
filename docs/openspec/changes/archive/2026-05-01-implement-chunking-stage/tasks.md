## 1. Config Extension (ChunkingConfig has silence_pad_ms field)

- [x] [P] 1.1 Add `silence_pad_ms: int = 50` to `ChunkingConfig` in `src/talking_parrot/config/models.py`; add a `@field_validator("silence_pad_ms")` that raises `ValueError` for negative values (ChunkingConfig has silence_pad_ms field; ChunkingConfig extension)
- [x] [P] 1.2 Add tests in `tests/unit/config/test_models.py` for the new field: verify default is `50`, explicit value is accepted, and a negative value raises `ValidationError`

## 2. ChunkingStage Skeleton and Disabled Behaviour (ChunkingStage disabled returns context unchanged)

- [x] 2.1 Create `src/talking_parrot/stages/chunking_stage.py` with `ChunkingStage(PipelineStage)`: `name` property returns `"chunking"`; `process()` returns `ctx` unchanged when `config.chunking is None` or `config.chunking.enabled is False`, emitting one DEBUG log line (ChunkingStage disabled returns context unchanged; Disabled-stage behaviour)
- [x] 2.2 Create `tests/unit/stages/test_chunking_stage.py` with shared fixtures and tests verifying the disabled path returns the same context object

## 3. Greedy Accumulation (ChunkingStage greedy accumulation)

- [x] 3.1 Write failing tests in `tests/unit/stages/test_chunking_stage.py` covering: all segments fit in one chunk; segments split across two chunks at the `max_chunk_seconds` boundary; empty `vad_segments` yields empty `chunks`
- [x] 3.2 Implement ChunkingStage greedy accumulation loop in `ChunkingStage.process()` in `src/talking_parrot/stages/chunking_stage.py`: iterate `ctx.vad_segments` left-to-right; seal pending chunk when `(segment.end_ms - pending_start_ms) / 1000 > max_chunk_seconds` (Greedy accumulation strategy); assign zero-based contiguous `index` values (ChunkingStage produces zero-indexed contiguous chunk indices); return new context via `dataclasses.replace`

## 4. Hard-Cut Fallback (ChunkingStage hard-cut fallback for oversized segments)

- [x] 4.1 Write failing tests in `tests/unit/stages/test_chunking_stage.py` for: a 75 000 ms segment with `max_chunk_seconds=30` must produce exactly 3 chunks spanning `[0, 30 000)`, `[30 000, 60 000)`, `[60 000, 75 000)`; each sub-chunk carries the original segment in `source_segments`
- [x] 4.2 Implement ChunkingStage hard-cut fallback for oversized segments: add private `_expand_oversized(segment, max_ms)` helper in `src/talking_parrot/stages/chunking_stage.py`; call it before greedy accumulation for any segment where `(end_ms - start_ms) > max_chunk_seconds * 1000`; flatten sub-chunk spans back into the segment feed

## 5. Silence Pad Expansion (ChunkingStage silence_pad expansion)

- [x] 5.1 Write failing tests in `tests/unit/stages/test_chunking_stage.py` for: pad applied within bounds moves start back and end forward by exactly `silence_pad_ms`; start clamped to `0`; end clamped to `ctx.media_info.duration_ms`
- [x] 5.2 Implement ChunkingStage silence_pad expansion post-pass (silence_pad_ms application) in `src/talking_parrot/stages/chunking_stage.py`: after sealing all chunks rebuild each via `dataclasses.replace(chunk, start_ms=max(0, chunk.start_ms - silence_pad_ms), end_ms=min(ctx.media_info.duration_ms, chunk.end_ms + silence_pad_ms))`

## 6. Registration and Final Verification

- [x] 6.1 Export `ChunkingStage` from `src/talking_parrot/stages/__init__.py`
- [x] 6.2 Run `uv run pytest --tb=short` and `uv run ruff check .` to confirm zero failures and zero lint errors
