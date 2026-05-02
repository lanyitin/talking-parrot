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

`TimeBasedSplitProcessor` SHALL split any cue whose `end_ms - start_ms > config.split_max_duration_ms` into `n = ceil(duration / config.split_max_duration_ms)` equal-time slices. For each slice, the text split index SHALL be `char_idx_i = round(i / n * len(text))` (proportional by `len(text)`, no token data). The concatenation of all child texts SHALL equal the original `text`, and the first child's `start_ms` and the last child's `end_ms` SHALL equal the original cue's bounds.

If `len(text) <= 1`, the cue SHALL be returned unchanged and a DEBUG log entry SHALL be emitted.

#### Scenario: A 12-second cue is split into two equal-time slices

- **GIVEN** a cue `("the quick brown fox", 0, 12000)` (19 characters) and `split_max_duration_ms=6000`
- **WHEN** `TimeBasedSplitProcessor().process([sub], cfg)` is called
- **THEN** the result has two cues whose `start_ms` / `end_ms` pairs are `(0, 6000)` and `(6000, 12000)`, whose text pieces concatenate to `"the quick brown fox"`, and whose indices are `1` and `2`

#### Scenario: A cue shorter than the split threshold is unchanged

- **GIVEN** a cue `("ok", 0, 3000)` and `split_max_duration_ms=6000`
- **WHEN** the processor runs
- **THEN** the cue is returned unchanged (only `index` re-numbered)

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