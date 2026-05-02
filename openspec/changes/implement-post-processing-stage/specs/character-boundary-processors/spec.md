## ADDED Requirements

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

### Requirement: CharacterBoundarySplitProcessor splits oversized cues by linear interpolation

`CharacterBoundarySplitProcessor` SHALL split any cue whose `end_ms - start_ms > config.split_max_duration_ms` into `n = ceil(duration / config.split_max_duration_ms)` equal-time slices. For each slice `i` (0-indexed), the character split index SHALL be computed as `char_idx_i = round(slice_end_ms_i / cue_duration_ms * len(text))`. Slices SHALL preserve total `text` (concatenation of all child texts equals the original `text`) and total time span (first child's `start_ms` equals original, last child's `end_ms` equals original).

The processor SHALL NOT consume an `AlignedToken` map; only `Subtitle` fields and `PostProcessingConfig` are read.

If `len(text) <= 1`, the processor SHALL leave the cue intact and emit a DEBUG log entry naming the cue index.

#### Scenario: A 9-second cue is split into two equal-time character slices

- **GIVEN** a single cue `("あいうえおかきくけこ", 0, 9000)` (10 characters) and `split_max_duration_ms=6000`
- **WHEN** `CharacterBoundarySplitProcessor().process([sub], cfg)` is called
- **THEN** the result has two cues: `("あいうえお", 0, 4500, index=1)` and `("かきくけこ", 4500, 9000, index=2)`

#### Scenario: A single-character cue cannot be split

- **GIVEN** a single cue `("。", 0, 9000)` and `split_max_duration_ms=6000`
- **WHEN** the processor runs
- **THEN** the cue SHALL be returned unchanged (only `index` re-numbered) and a DEBUG log entry SHALL be emitted
