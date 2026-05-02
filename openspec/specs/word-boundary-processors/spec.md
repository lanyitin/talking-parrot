# word-boundary-processors Specification

## Purpose

TBD - created by archiving change 'implement-post-processing-stage'. Update Purpose after archive.

## Requirements

### Requirement: WordBoundaryMergeProcessor merges adjacent cues that satisfy all merge constraints

The system SHALL provide `WordBoundaryMergeProcessor(SubtitleProcessor)` constructed with `token_map_by_index: dict[int, list[AlignedToken]]`. Two adjacent cues `a` and `b` (in the input list) SHALL be merged into a single output cue when ALL of the following hold:

- `b.start_ms - a.end_ms <= config.merge_gap_threshold_ms`
- `b.end_ms - a.start_ms <= config.merge_max_duration_ms`
- `len(a.text) + 1 + len(b.text) <= config.max_line_length * config.max_lines_per_subtitle`

A merged cue SHALL have `start_ms = a.start_ms`, `end_ms = b.end_ms`, and `text = a.text + " " + b.text`. Merging SHALL be applied iteratively (left-to-right, single pass) so that more than two cues MAY collapse into one.

#### Scenario: Two cues within all thresholds are merged

- **GIVEN** `subs_in = [Subtitle(1, 0, 1000, "hello"), Subtitle(2, 1100, 2000, "world")]`
- **AND** `config.merge_gap_threshold_ms = 200, merge_max_duration_ms = 6000, max_line_length = 42, max_lines_per_subtitle = 2`
- **WHEN** the processor runs
- **THEN** the output MUST equal `[Subtitle(index=<any>, start_ms=0, end_ms=2000, text="hello world")]`

#### Scenario: Gap exceeding threshold prevents merge

- **GIVEN** `subs_in = [Subtitle(1, 0, 1000, "a"), Subtitle(2, 5000, 6000, "b")]` and `config.merge_gap_threshold_ms = 200`
- **WHEN** the processor runs
- **THEN** the output MUST contain 2 cues with the same texts and timings

#### Scenario: Resulting duration exceeding cap prevents merge

- **GIVEN** `subs_in = [Subtitle(1, 0, 4000, "a"), Subtitle(2, 4100, 8000, "b")]` and `config.merge_max_duration_ms = 6000`
- **WHEN** the processor runs
- **THEN** the output MUST contain 2 cues unchanged

#### Scenario: Resulting text exceeding length cap prevents merge

- **GIVEN** `subs_in = [Subtitle(1, 0, 1000, "x" * 30), Subtitle(2, 1100, 2000, "y" * 30)]`
- **AND** `config.max_line_length = 42, max_lines_per_subtitle = 1`
- **WHEN** the processor runs
- **THEN** the output MUST contain 2 cues unchanged

##### Example: cascade merge across three cues

| Input cues | Gap thresh | Max dur | Output |
| --- | --- | --- | --- |
| (0–500,"a"), (600–1100,"b"), (1200–1700,"c") | 200 | 6000 | (0–1700, "a b c") |


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
### Requirement: WordBoundarySplitProcessor splits oversized cues at token boundaries

The system SHALL provide `WordBoundarySplitProcessor(SubtitleProcessor)` constructed with `token_map_by_index: dict[int, list[AlignedToken]]`. A cue `c` whose duration `c.end_ms - c.start_ms > config.split_max_duration_ms` SHALL be split into `n = ceil(duration / config.split_max_duration_ms)` pieces. The cue's associated `aligned_tokens` (looked up by its current `index`, with merge-derived cues mapped via the closure helper from D3) SHALL be partitioned into `n` consecutive groups whose target time slice boundaries are `start_ms + k * duration / n` for `k in 1..n-1`. Each piece's `text` SHALL be the space-joined `word` field of its token group; each piece's `start_ms` / `end_ms` SHALL equal the first/last token's absolute `start_ms` / `end_ms`. If `len(tokens) < n` (cannot split), the cue SHALL pass through unchanged and a DEBUG log SHALL be emitted with the cue's `index`.

#### Scenario: Long cue with sufficient tokens is split into N pieces

- **GIVEN** a cue with duration 12000ms and 6 evenly-spaced tokens, `config.split_max_duration_ms = 6000`
- **WHEN** the processor runs
- **THEN** the output MUST contain 2 cues whose token boundaries match tokens `[0..2]` and `[3..5]`
- **AND** each output cue's text MUST be the space-joined token words

#### Scenario: Cue under the cap passes through unchanged

- **GIVEN** a cue with duration 5000ms and `config.split_max_duration_ms = 6000`
- **WHEN** the processor runs
- **THEN** the output MUST contain exactly that cue (timings and text equal)

#### Scenario: Insufficient tokens leaves cue intact and logs DEBUG

- **GIVEN** a cue with duration 12000ms but only 1 token, `config.split_max_duration_ms = 6000`
- **WHEN** the processor runs
- **THEN** the output MUST contain exactly that cue
- **AND** a DEBUG log containing the cue's `index` MUST be emitted

##### Example: 12s cue with 4 tokens splits into 2

| Input cue | Tokens (start_ms,end_ms,word) | split_max | Output cues |
| --- | --- | --- | --- |
| (0–12000) | (0,3000,"a"), (3100,6000,"b"), (6100,9000,"c"), (9100,12000,"d") | 6000 | (0–6000,"a b"), (6100–12000,"c d") |

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