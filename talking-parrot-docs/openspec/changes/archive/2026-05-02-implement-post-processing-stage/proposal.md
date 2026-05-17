## Why

Stage 5 of the pipeline (`PostProcessingStage`) is the final transformation between `TranscriptionResult` and the user-facing `Subtitle` sequence. Without it the orchestrator has no way to merge over-short cues, split over-long cues, or honor `AlignmentGranularity` boundaries — so the output of Stage 4 cannot become subtitles, and Stage 6 (export) has nothing to write. ADR-0003 already pinned the strategy (granularity-aware processor factory with WORD / CHARACTER / fallback groups); this change implements it.

## What Changes

- Add a new `post_processing` subsystem under `src/talking_parrot/post_processing/` containing the `SubtitleProcessor` ABC, six concrete processors, and the `GranularityAwareProcessorFactory`.
- Add `PostProcessingStage` under `src/talking_parrot/stages/` that reads `ctx.alignment_granularity`, invokes the factory, converts `TranscriptionResult` to an initial `Subtitle` sequence, runs the processor pipeline, and writes the final `subtitles` list onto the returned `PipelineContext`.
- Extend `PostProcessingConfig` (in `src/talking_parrot/config/models.py`) with three numeric thresholds the processors require: `merge_gap_threshold_ms`, `merge_max_duration_ms`, `split_max_duration_ms` (with defaults that preserve current YAML files). The existing `enabled`, `max_line_length`, `max_lines_per_subtitle` fields are kept as-is; this is additive, not breaking.
- The disabled path (`ctx.config.post_processing is None` or `enabled is False`) MUST short-circuit: emit a one-cue-per-`TranscriptionResult` baseline `subtitles` list (so downstream export still runs) without consulting the factory.
- The `FAILED` alignment path (`ctx.alignment_status == FAILED`) MUST fall back to the time-based processor group AND emit a WARNING log, per ADR-0003.

## Non-Goals

- This change does NOT implement subtitle export — `SRTExporter` / `WebVTTExporter` are tracked under `implement-subtitle-export`.
- This change does NOT introduce new alignment granularities (e.g. `SYLLABLE`); the enum remains `{WORD, CHARACTER}`.
- This change does NOT modify `AlignmentBackend` or any upstream Stage; the granularity contract is read-only here.
- This change does NOT wire `PostProcessingStage` into `cli.py` end-to-end runs; orchestrator integration is covered when all stages exist (validated in `implement-subtitle-export`).
- Linguistically aware splitting (e.g. Japanese punctuation rules, MeCab word segmentation) is deferred. Character-boundary processors split on the configured time threshold but at character boundaries — language heuristics are future work.

## Capabilities

### New Capabilities

- `post-processing-stage`: The Stage 5 orchestration class — `name`, constructor injection, disabled / FAILED-alignment short-circuit paths, ordering of factory invocation, baseline `Subtitle` construction from `TranscriptionResult`, and `dataclasses.replace` immutability contract.
- `subtitle-processor`: The `SubtitleProcessor` ABC contract that all six processors implement — single `process(subtitles, config) -> list[Subtitle]` method, immutability of input, ordering preservation, monotonic timestamp invariants on output.
- `granularity-aware-processor-factory`: The factory that maps `AlignmentGranularity | None` to an ordered list of `SubtitleProcessor` instances, including the `None` → time-based fallback rule.
- `word-boundary-processors`: `WordBoundaryMergeProcessor` and `WordBoundarySplitProcessor` — operate on `Subtitle` cues whose source `TranscriptionResult.aligned_tokens` is word-level; merge / split decisions MUST land on token boundaries.
- `character-boundary-processors`: `CharacterBoundaryMergeProcessor` and `CharacterBoundarySplitProcessor` — operate on character-level aligned tokens (e.g. Japanese); MUST split between characters, never inside a multi-byte sequence.
- `time-based-processors`: `TimeBasedMergeProcessor` and `TimeBasedSplitProcessor` — fallback group when alignment is disabled or failed; decisions are based purely on `start_ms` / `end_ms` and configured thresholds, with no token introspection.

### Modified Capabilities

(none — the existing alignment / transcription specs are referenced read-only)

## Impact

- Affected specs: six new capability specs listed above.
- Affected code:
  - New:
    - src/talking_parrot/post_processing/__init__.py
    - src/talking_parrot/post_processing/base.py
    - src/talking_parrot/post_processing/factory.py
    - src/talking_parrot/post_processing/word_boundary.py
    - src/talking_parrot/post_processing/character_boundary.py
    - src/talking_parrot/post_processing/time_based.py
    - src/talking_parrot/stages/post_processing_stage.py
    - tests/unit/post_processing/__init__.py
    - tests/unit/post_processing/test_base.py
    - tests/unit/post_processing/test_factory.py
    - tests/unit/post_processing/test_word_boundary.py
    - tests/unit/post_processing/test_character_boundary.py
    - tests/unit/post_processing/test_time_based.py
    - tests/unit/stages/test_post_processing_stage.py
  - Modified:
    - src/talking_parrot/config/models.py (additive fields on `PostProcessingConfig`)
    - src/talking_parrot/stages/__init__.py (export `PostProcessingStage`)
  - Removed: (none)
- Dependencies: no new third-party dependencies. Pure-Python stage that consumes existing data models (`Subtitle`, `TranscriptionResult`, `AlignedToken`, `AlignmentStatus`, `AlignmentGranularity`).
