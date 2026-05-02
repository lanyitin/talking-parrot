## 1. Config & Foundations

- [x] 1.1 Extend `PostProcessingConfig` with `merge_gap_threshold_ms`, `merge_max_duration_ms`, `split_max_duration_ms` per **D8. `PostProcessingConfig` field defaults** (defaults 200/6000/6000) and add a validator enforcing `merge_max_duration_ms <= split_max_duration_ms`
- [x] 1.2 Add unit tests for `PostProcessingConfig` defaults, validator failure, and YAML-load backwards compatibility
- [x] 1.3 Create `src/talking_parrot/post_processing/__init__.py` package skeleton and re-export the public surface (ABC, factory, six processors)

## 2. SubtitleProcessor ABC (TDD)

- [x] 2.1 Write failing tests in `tests/unit/post_processing/test_base.py` covering **SubtitleProcessor abstract base class** instantiation and `process` signature
- [x] 2.2 Write failing tests for **SubtitleProcessor input immutability** (input list and `Subtitle` instances unchanged after `process`)
- [x] 2.3 Write failing tests for **SubtitleProcessor output ordering and timestamp invariants** (monotonic `start_ms`, `end_ms >= start_ms`, ascending `index`)
- [x] 2.4 Write failing tests for **SubtitleProcessor handles empty input** (empty list returns empty list, no factory or config access errors)
- [x] 2.5 Implement `SubtitleProcessor` ABC in `post_processing/base.py` with the single `process(subtitles, config) -> list[Subtitle]` method per **D2. `SubtitleProcessor.process` is pure and side-effect-free**
- [x] 2.6 Add a shared `_renumber(subs)` helper plus the `_with_token_map` aggregation helper described in **D3. Word-boundary processors consume `TranscriptionResult.aligned_tokens` *out-of-band***

## 3. Time-Based Processors (TDD, fallback group)

- [x] 3.1 Write failing tests in `tests/unit/post_processing/test_time_based.py` for **TimeBasedMergeProcessor merges adjacent cues using only time and length** covering the three-way merge predicate from **D5. Merge rule (all groups)** with `" "` separator
- [x] 3.2 Write failing tests for **TimeBasedSplitProcessor splits oversized cues proportionally by text length** covering equal-time slicing and proportional `len(text)` text split per **D6. Split rule (all groups)** time-based fallback branch
- [x] 3.3 Write failing test asserting `TimeBasedSplitProcessor` leaves `len(text) <= 1` cues intact and emits a DEBUG log per **D6**
- [x] 3.4 Implement `TimeBasedMergeProcessor` and `TimeBasedSplitProcessor` in `post_processing/time_based.py` (no token introspection)

## 4. Character-Boundary Processors (TDD)

- [x] 4.1 Write failing tests in `tests/unit/post_processing/test_character_boundary.py` for **CharacterBoundaryMergeProcessor merges adjacent character-aligned cues** (CJK fixtures, `""` separator)
- [x] 4.2 Write failing tests for **CharacterBoundarySplitProcessor splits oversized cues by linear interpolation** using the `char_idx = round(slice_ms / cue_duration_ms * len(text))` rule per **D4. Character-boundary processors do not need a token map** and **D6**
- [x] 4.3 Write failing test confirming character-boundary processors never consume an `AlignedToken` map (constructor takes only config) per **D4**
- [x] 4.4 Implement `CharacterBoundaryMergeProcessor` and `CharacterBoundarySplitProcessor` in `post_processing/character_boundary.py`

## 5. Word-Boundary Processors (TDD)

- [x] 5.1 Write failing tests in `tests/unit/post_processing/test_word_boundary.py` for **WordBoundaryMergeProcessor merges adjacent cues that satisfy all merge constraints** using a baked-in token map closure
- [x] 5.2 Write failing tests for **WordBoundarySplitProcessor splits oversized cues at token boundaries**, snapping slice times to nearest `AlignedToken.start_ms`
- [x] 5.3 Write failing test confirming **WORD-group processors receive token map from factory** and that `_with_token_map` produces a fresh aggregated map after merge/split
- [x] 5.4 Implement `WordBoundaryMergeProcessor` and `WordBoundarySplitProcessor` in `post_processing/word_boundary.py`, closing over the token map per **D3**

## 6. GranularityAwareProcessorFactory (TDD)

- [x] 6.1 Write failing tests in `tests/unit/post_processing/test_factory.py` for **GranularityAwareProcessorFactory interface and concrete implementation** (factory ABC + concrete class)
- [x] 6.2 Write failing tests for **Factory returns word-boundary group for WORD granularity** in `[Merge, Split]` order per **D7. Processor ordering within a group is `[Merge, Split]`**
- [x] 6.3 Write failing tests for **Factory returns character-boundary group for CHARACTER granularity** in `[Merge, Split]` order per **D7**
- [x] 6.4 Write failing tests for **Factory returns time-based group for None** in `[Merge, Split]` order per **D7**
- [x] 6.5 Write failing test for **Factory raises on unknown granularity** (e.g. a synthetic enum value) raising `ValueError`
- [x] 6.6 Implement `GranularityAwareProcessorFactory.create(granularity, transcription_results)` in `post_processing/factory.py`, building the per-cue token map for the WORD path per **D3**

## 7. PostProcessingStage (TDD)

- [x] 7.1 Write failing tests in `tests/unit/stages/test_post_processing_stage.py` for **PostProcessingStage exposes name and constructor injection** (`name == "post_processing"`, factory injected)
- [x] 7.2 Write failing tests for **PostProcessingStage builds seed subtitles from transcription results** per **D1. Seed `Subtitle` construction is one cue per `TranscriptionResult`** (1-based indices, `start_ms`/`end_ms`/`text` copied)
- [x] 7.3 Write failing tests for **PostProcessingStage disabled-path** (`config.post_processing is None` and `enabled is False`) returning seed subtitles without consulting factory per **D9. Disabled-path semantics**
- [x] 7.4 Write failing tests for **PostProcessingStage selects factory group by alignment status**: `DISABLED` silent fallback to `None`, `FAILED` logs WARNING and forces `granularity=None` per **D10. FAILED-alignment semantics**, `SUCCESS` honors `ctx.alignment_granularity`
- [x] 7.5 Write failing tests for **PostProcessingStage runs processors in factory-returned order**, re-numbering indices to `1..len(subs)` between processors
- [x] 7.6 Write failing tests for **PostProcessingStage handles empty transcription results** (returns empty `subtitles`, no factory access, no warning)
- [x] 7.7 Implement `PostProcessingStage` in `src/talking_parrot/stages/post_processing_stage.py`, returning a new context via `dataclasses.replace(ctx, subtitles=...)`
- [x] 7.8 Export `PostProcessingStage` from `src/talking_parrot/stages/__init__.py`

## 8. Verification

- [x] 8.1 Run `uv run pytest tests/unit/post_processing tests/unit/stages/test_post_processing_stage.py` and ensure 100% pass
- [x] 8.2 Run `uv run ruff check .` and `uv run ruff format --check .` with zero errors
- [x] 8.3 Run full `uv run pytest` to confirm no regressions in upstream stages
