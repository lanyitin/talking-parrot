# time-based-processors Specification

## Purpose

TBD - created by archiving change 'implement-post-processing-stage'. Update Purpose after archive.

## Requirements

### Requirement: TimeBasedMergeProcessor merges adjacent cues using only time and length

`TimeBasedMergeProcessor` SHALL implement `SubtitleProcessor.process(subtitles, config)` and merge two adjacent cues `a, b` when ALL of the following hold:

- `b.start_ms - a.end_ms <= config.merge_gap_threshold_ms`
- `b.end_ms - a.start_ms <= config.merge_max_duration_ms`
- `len(a.text) + 1 + len(b.text) <= config.max_line_length * config.max_lines_per_subtitle`

When merging, the processor SHALL produce a new `Subtitle` whose `text = a.text + " " + b.text` (single space separator), `start_ms = a.start_ms`, `end_ms = b.end_ms`. Output indices SHALL be 1-based contiguous. The processor SHALL NOT consume an `AlignedToken` map and SHALL NOT inspect token data.

#### Scenario: Two adjacent fallback cues are merged with single space

- **GIVEN** cues `[("hello", 0, 500), ("world", 600, 1200)]` and config `merge_gap_threshold_ms=200, merge_max_duration_ms=6000, max_line_length=40, max_lines_per_subtitle=2`
- **WHEN** `TimeBasedMergeProcessor().process(subs, cfg)` is called
- **THEN** the result is a single cue `("hello world", 0, 1200, index=1)`


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
### Requirement: TimeBasedSplitProcessor splits oversized cues proportionally by text length

`TimeBasedSplitProcessor` SHALL split any cue whose `end_ms - start_ms > config.split_max_duration_ms` into `n = ceil(duration / config.split_max_duration_ms)` slices. For each inner boundary `i` in `[1, n - 1]`, the processor SHALL compute:

- `candidate_text_idx_i = round(i / n * len(text))`
- `candidate_time_ms_i = sub.start_ms + (i * cue_duration_ms) // n`

The processor SHALL then:

- Call `text_idx_i = boundary_policy.adjust(text, candidate_text_idx_i, search_radius)` where `boundary_policy` is a `SplitBoundaryPolicy` injected via the constructor (default: `LinearSplitBoundaryPolicy()`) and `search_radius = config.japanese_split_search_radius`.
- Call `time_ms_i = time_policy.adjust(candidate_time_ms_i, sub.start_ms, sub.end_ms)` where `time_policy` is a `SplitTimePolicy` injected via the constructor (default: `LinearSplitTimePolicy()`).

The processor SHALL define `boundaries[0] = sub.start_ms`, `boundaries[n] = sub.end_ms`, and `boundaries[i] = time_ms_i` for `i` in `[1, n - 1]`. Slice `i` (0-indexed) SHALL have `start_ms = boundaries[i]` and `end_ms = boundaries[i + 1]`. The text-split indices SHALL be applied to derive each slice's text. The concatenation of all child texts SHALL equal the original `text`, and the first child's `start_ms` and the last child's `end_ms` SHALL equal the original cue's bounds.

The constructor signature SHALL be `TimeBasedSplitProcessor(policy: SplitBoundaryPolicy | None = None, time_policy: SplitTimePolicy | None = None)`. When `policy is None`, the processor SHALL substitute `LinearSplitBoundaryPolicy()`. When `time_policy is None`, the processor SHALL substitute `LinearSplitTimePolicy()`.

If `len(text) <= 1`, the cue SHALL be returned unchanged and a DEBUG log entry SHALL be emitted. Neither policy SHALL be called in this case.

If after policy adjustment two consecutive text-split indices are equal, the processor SHALL emit an empty-text child for the later slice (preserving the time-span invariant) and emit a DEBUG log entry naming the cue index.

If after time-policy adjustment two consecutive `boundaries[i]` and `boundaries[i + 1]` collide such that `boundaries[i] >= boundaries[i + 1]`, the processor SHALL set `boundaries[i + 1] = boundaries[i] + 1` (1 ms minimum slice length), preserve the `Subtitle` invariant `start_ms < end_ms`, and emit a DEBUG log entry naming the cue index.

#### Scenario: A 12-second cue is split into two equal-time slices

- **GIVEN** a cue `("the quick brown fox", 0, 12000)` (19 characters), `split_max_duration_ms=6000`, a `LinearSplitBoundaryPolicy`, and a `LinearSplitTimePolicy`
- **WHEN** `TimeBasedSplitProcessor(policy=LinearSplitBoundaryPolicy(), time_policy=LinearSplitTimePolicy()).process([sub], cfg)` is called
- **THEN** the result has two cues whose `(start_ms, end_ms)` pairs are `(0, 6000)` and `(6000, 12000)`, whose text pieces concatenate to `"the quick brown fox"`, and whose indices are `1` and `2`

#### Scenario: A cue shorter than the split threshold is unchanged

- **GIVEN** a cue `("ok", 0, 3000)` and `split_max_duration_ms=6000`
- **WHEN** the processor runs
- **THEN** the cue is returned unchanged (only `index` re-numbered)
- **AND** the injected boundary policy's `adjust` MUST NOT be called
- **AND** the injected time policy's `adjust` MUST NOT be called

#### Scenario: Default constructor uses both linear policies

- **GIVEN** `TimeBasedSplitProcessor()` (no policy arguments)
- **WHEN** the processor runs against any cue
- **THEN** the resulting splits MUST be identical to those produced when `LinearSplitBoundaryPolicy()` and `LinearSplitTimePolicy()` are explicitly passed

#### Scenario: Time policy snaps slice boundary to silence midpoint

- **GIVEN** a cue `("the quick brown fox", 0, 12000)`, `split_max_duration_ms=6000`, a `LinearSplitBoundaryPolicy`, and a stub `SplitTimePolicy` that returns `6300` for any candidate
- **WHEN** the processor runs
- **THEN** the result has two cues whose `(start_ms, end_ms)` pairs are `(0, 6300)` and `(6300, 12000)`
- **AND** the concatenation of their text MUST equal `"the quick brown fox"`

#### Scenario: Time-boundary collision emits 1ms-minimum slice

- **GIVEN** a cue `("a b c d e f g h i j k l", 0, 12000)`, `split_max_duration_ms=4000`, a `LinearSplitBoundaryPolicy`, and a stub `SplitTimePolicy` that returns `8000` for both inner-boundary candidates (collision)
- **WHEN** the processor runs
- **THEN** the result has three cues whose `(start_ms, end_ms)` pairs are `(0, 8000)`, `(8000, 8001)`, `(8001, 12000)`
- **AND** a DEBUG log entry MUST be emitted naming the cue index

<!-- @trace
source: snap-split-timestamps-to-vad-silence
-->

<!-- @trace
source: snap-split-timestamps-to-vad-silence
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/config/test_models.py
-->