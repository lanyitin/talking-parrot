# character-boundary-processors Specification

## Purpose

TBD - created by archiving change 'implement-post-processing-stage'. Update Purpose after archive.

## Requirements

### Requirement: CharacterBoundaryMergeProcessor merges adjacent character-aligned cues

`CharacterBoundaryMergeProcessor` SHALL implement `SubtitleProcessor.process(subtitles, config)` and merge two adjacent cues `a, b` when ALL of the following hold:

- `b.start_ms - a.end_ms <= config.merge_gap_threshold_ms`
- `b.end_ms - a.start_ms <= config.merge_max_duration_ms`
- `len(a.text) + len(b.text) <= config.max_line_length * config.max_lines_per_subtitle`

When merging, the processor SHALL produce a new `Subtitle` whose `text = a.text + b.text` (empty separator, no whitespace inserted), `start_ms = a.start_ms`, `end_ms = b.end_ms`. The output list SHALL be re-numbered with 1-based indices. The processor SHALL NOT consume an `AlignedToken` map.

#### Scenario: Two short adjacent CJK cues are merged with empty separator

- **GIVEN** a list of two cues `[("こんにちは", 0, 800), ("世界", 850, 1500)]` and a config with `merge_gap_threshold_ms=200`, `merge_max_duration_ms=6000`, `max_line_length=20`, `max_lines_per_subtitle=2`
- **WHEN** `CharacterBoundaryMergeProcessor().process(subs, cfg)` is called
- **THEN** the result is a single `Subtitle` with `text="こんにちは世界"`, `start_ms=0`, `end_ms=1500`, `index=1`

#### Scenario: Cues whose gap exceeds threshold are not merged

- **GIVEN** two cues separated by 500ms and `merge_gap_threshold_ms=200`
- **WHEN** the processor runs
- **THEN** the two cues SHALL be returned unchanged (only `index` re-numbered)


<!-- @trace
source: implement-post-processing-stage
updated: 2026-05-02
code:
  - src/talking_parrot/config/models.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/cli.py
  - tests/unit/io/subtitle_export/__init__.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - tests/unit/post_processing/__init__.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/stages/post_processing_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/__init__.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/config/test_export_config.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/stages/test_post_processing_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_character_boundary.py
-->

---
### Requirement: CharacterBoundarySplitProcessor splits oversized cues by linear interpolation

`CharacterBoundarySplitProcessor` SHALL split any cue whose `end_ms - start_ms > config.split_max_duration_ms` into `n = ceil(duration / config.split_max_duration_ms)` equal-time slices. For each slice `i` (0-indexed), the candidate character split index SHALL be computed as `candidate_i = round(slice_end_ms_i / cue_duration_ms * len(text))`. The processor SHALL then call `policy.adjust(text, candidate_i, search_radius)` where `policy` is a `SplitBoundaryPolicy` injected via the constructor (default: `LinearSplitBoundaryPolicy()`) and `search_radius = config.japanese_split_search_radius`. The returned index SHALL be used as the actual split point. Slices SHALL preserve total `text` (concatenation of all child texts equals the original `text`) and total time span (first child's `start_ms` equals original, last child's `end_ms` equals original). Slice timestamps SHALL remain at the linear positions `slice_end_ms_i = start_ms + round((i + 1) * cue_duration_ms / n)`; only the text-split index is adjusted by the policy.

The constructor signature SHALL be `CharacterBoundarySplitProcessor(policy: SplitBoundaryPolicy | None = None)`. When `policy is None`, the processor SHALL substitute `LinearSplitBoundaryPolicy()` so the default (no-op) behaviour is preserved.

The processor SHALL NOT consume an `AlignedToken` map; only `Subtitle` fields, `PostProcessingConfig`, and the injected policy are read.

If `len(text) <= 1`, the processor SHALL leave the cue intact and emit a DEBUG log entry naming the cue index. The policy SHALL NOT be called in this case.

If after policy adjustment two consecutive slice indices are equal (i.e., the policy snapped both to the same boundary), the processor SHALL emit an empty-text child for the second slice (preserving the time-span invariant) and emit a DEBUG log entry naming the cue index.

#### Scenario: A 9-second cue is split into two equal-time character slices

- **GIVEN** a single cue `("あいうえおかきくけこ", 0, 9000)` (10 characters), `split_max_duration_ms=6000`, and a `LinearSplitBoundaryPolicy`
- **WHEN** `CharacterBoundarySplitProcessor(policy=LinearSplitBoundaryPolicy()).process([sub], cfg)` is called
- **THEN** the result has two cues: `("あいうえお", 0, 4500, index=1)` and `("かきくけこ", 4500, 9000, index=2)`

#### Scenario: A single-character cue cannot be split

- **GIVEN** a single cue `("。", 0, 9000)` and `split_max_duration_ms=6000`
- **WHEN** the processor runs
- **THEN** the cue SHALL be returned unchanged (only `index` re-numbered) and a DEBUG log entry SHALL be emitted
- **AND** the injected policy's `adjust` MUST NOT be called

#### Scenario: Policy adjusts the text-split index but not the time-split

- **GIVEN** a cue with `cue_duration_ms = 9000`, `len(text) = 9`, `split_max_duration_ms = 6000`, and a stub policy that returns `candidate_index + 1` for any input
- **WHEN** the processor runs
- **THEN** the boundary timestamps MUST be at `0`, `4500`, `9000` (unchanged from the linear policy)
- **AND** the first child's text length MUST equal `round(4500 / 9000 * 9) + 1 = 6`, not `5`

#### Scenario: Default constructor uses the linear policy

- **GIVEN** `CharacterBoundarySplitProcessor()` (no policy argument)
- **WHEN** the processor runs against any cue
- **THEN** the resulting splits MUST be identical to those produced when `LinearSplitBoundaryPolicy()` is explicitly passed

<!-- @trace
source: japanese-aware-cue-split
updated: 2026-05-08
code:
  - CLAUDE.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/japanese.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/post_processing/dedup.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/stages/transcription_stage.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/logging_config.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
tests:
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/config/test_loader.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_dedup.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/post_processing/test_split_policy.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/post_processing/test_japanese.py
-->