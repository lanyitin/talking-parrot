## Why

Subtitle timing in the current pipeline is degraded by two related problems. First, each `Chunk` aggregates multiple VAD segments into a single Whisper call, and the backend collapses Whisper's per-segment metrics (`avg_logprob`, `no_speech_prob`, `compression_ratio`, `repetition_ratio`) into one chunk-level value via weighted-mean / max. A single hallucinated VAD segment is therefore diluted by neighbouring healthy ones and cannot be filtered. Second, no post-processing exists for known Whisper failure modes — hallucinated bracketed text (`[音楽]`), repeated phrase spillover across overlapping chunks, or Japanese filler/repetition noise — so cue boundaries are routinely too long or duplicated.

A reference implementation in another local project (`audio2subtitle`) addresses both problems. This change ports its filtering logic and refactors the transcription contract so the filters can operate at the granularity Whisper actually produces (per Whisper segment), not at the coarser chunk granularity.

## What Changes

- **BREAKING**: `TranscriptionBackend.transcribe(...)` returns `list[TranscriptionResult]` instead of a single `TranscriptionResult`. One result is emitted per Whisper internal segment.
- **BREAKING**: `TranscriptionResult.start_ms` and `end_ms` change semantics from "chunk window bounds" to "absolute time bounds of the Whisper segment that produced this result". `chunk_index` is retained for traceback.
- **BREAKING**: `TranscriptionMetrics` fields are no longer aggregated; each result carries the raw Whisper-segment metrics.
- `TranscriptionStage` extends per-chunk results into `transcription_results` rather than appending one result per chunk.
- New `HallucinationFilterStage` runs between transcription and alignment and removes per-segment results that match known hallucination patterns (exact phrase list, bracketed text, ≥5-character repeats) or exceed configured `avg_logprob` / `no_speech_prob` / `compression_ratio` / `repetition_ratio` thresholds.
- `AlignmentStage` reads audio for `[result.start_ms, result.end_ms)` (not the whole chunk) and shifts aligned tokens by `result.start_ms`.
- New `DedupSubtitleProcessor` collapses runs of consecutive cues with text similarity ≥ threshold and inter-cue gap ≤ threshold; the merged cue keeps the first cue's text and extends `end_ms` to the last cue's `end_ms`.
- New `JapaneseFillerProcessor` and `JapaneseRepetitionProcessor` apply when `expected_language == "ja"`: filler removal and capped character repetition (with onomatopoeia whitelist).
- `DefaultGranularityAwareProcessorFactory` prepends dedup and (conditionally) appends the Japanese processors around the existing `[Merge, Split]` pair, for all three granularity paths.
- `PostProcessingConfig` gains dedup and Japanese-cleanup toggles/thresholds. New `HallucinationFilterConfig` (under the top-level pipeline config) carries the filter toggles and four numeric thresholds.

## Non-Goals

- Reworking VAD chunking strategy. Chunking remains greedy multi-segment accumulation.
- Per-segment alignment retries or re-chunking after filtering. Filtered segments are simply dropped.
- Porting `audio2subtitle`'s CPS filter. Existing duration caps in `[Merge, Split]` cover the main timing failure mode and per-segment filtering reduces high-CPS hallucinations indirectly.
- Multi-language post-processing. Only Japanese cleanup is in scope; English passes through dedup + merge/split unchanged.

## Capabilities

### New Capabilities

- `hallucination-filter-stage`: New pipeline stage that filters out per-segment `TranscriptionResult` entries identified as hallucinations.
- `dedup-subtitle-processor`: New `SubtitleProcessor` that merges consecutive near-duplicate cues, extending end timestamps.
- `japanese-postprocessors`: New language-conditional `SubtitleProcessor` pair (filler removal + repetition collapsing).

### Modified Capabilities

- `transcription-backend`: `transcribe(...)` return type changes to `list[TranscriptionResult]`; per-result metrics carry Whisper-segment raw values rather than chunk-level aggregates.
- `faster-whisper-backend`: Concrete implementation of the new list-returning contract; one `TranscriptionResult` per Whisper segment.
- `mlx-whisper-backend`: Same contract change as faster-whisper backend.
- `transcription-stage`: Extends backend results into `transcription_results` (was append).
- `pipeline-data-models`: `TranscriptionResult.start_ms`/`end_ms` semantics change; `PipelineContext` gains no new fields (filter result reflected only as a shorter `transcription_results` list).
- `alignment-stage`: Reads audio using `result.start_ms`/`end_ms` and shifts tokens by `result.start_ms`.
- `granularity-aware-processor-factory`: Prepends dedup and conditionally appends Japanese processors in all three granularity paths.
- `pipeline-config`: Adds `HallucinationFilterConfig` and extends `PostProcessingConfig` with dedup/Japanese fields.
- `pipeline-end-to-end-wiring`: Inserts `HallucinationFilterStage` between transcription and alignment.

## Impact

- Affected specs: see Capabilities above.
- Affected code:
  - New:
    - src/talking_parrot/stages/hallucination_filter_stage.py
    - src/talking_parrot/post_processing/dedup.py
    - src/talking_parrot/post_processing/japanese.py
    - tests/stages/test_hallucination_filter_stage.py
    - tests/post_processing/test_dedup.py
    - tests/post_processing/test_japanese.py
  - Modified:
    - src/talking_parrot/transcription/backend.py
    - src/talking_parrot/transcription/faster_whisper_backend.py
    - src/talking_parrot/transcription/mlx_whisper_backend.py
    - src/talking_parrot/stages/transcription_stage.py
    - src/talking_parrot/stages/alignment_stage.py
    - src/talking_parrot/post_processing/factory.py
    - src/talking_parrot/config/models.py
    - src/talking_parrot/cli.py
    - tests/transcription/test_faster_whisper_backend.py
    - tests/transcription/test_mlx_whisper_backend.py
    - tests/stages/test_transcription_stage.py
    - tests/stages/test_alignment_stage.py
    - tests/post_processing/test_factory.py
  - Removed: (none)
- Dependencies: no new third-party dependencies. Uses standard-library `difflib` for similarity scoring.
