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

`CharacterBoundarySplitProcessor` SHALL split any cue whose `end_ms - start_ms > config.split_max_duration_ms` into `n = ceil(duration / config.split_max_duration_ms)` slices.

**Constructor signature:**

```
CharacterBoundarySplitProcessor(
    policy: SplitBoundaryPolicy | None = None,
    time_policy: SplitTimePolicy | None = None,
    token_map_by_index: dict[int, list[AlignedToken]] | None = None,
)
```

When `policy is None`, the processor SHALL substitute `LinearSplitBoundaryPolicy()`. When `time_policy is None`, the processor SHALL substitute `LinearSplitTimePolicy()`. When `token_map_by_index is None`, the processor SHALL treat it as an empty dict (no tokens available for any cue).

**Primary path (VAD-driven, time → text, with grammar sanity gate):** For each inner boundary `i` in `[1, n-1]`, the processor SHALL:

1. Call `silence_midpoint = time_policy.pick(sub.start_ms, sub.end_ms)`.
2. Look up `tokens = token_map_by_index.get(sub.index, [])`.
3. If `silence_midpoint is not None` AND `tokens` is non-empty: binary-search `tokens` by `AlignedToken.end_ms` to find the first token whose `end_ms >= silence_midpoint`. Let `found_idx` be that token's position; when no such token exists, `found_idx = len(tokens)`. Compute `char_idx_vad = len("".join(t.word for t in tokens[:found_idx]))`, clamped to `[1, len(text) - 1]`. The time boundary SHALL be `silence_midpoint`.
4. **Sanity-gate sub-step (sub-path 3a — VAD valid):** If `policy.is_valid(text, char_idx_vad)` is `True`, the text cut index SHALL be `char_idx_vad`. No log entry SHALL be emitted for this sub-path.
5. **Sanity-gate sub-step (sub-path 3b — grammar snap):** Otherwise, compute `snapped_idx = policy.adjust(text, char_idx_vad, config.vad_grammar_search_radius)`. If `policy.is_valid(text, snapped_idx)` is `True`, the text cut index SHALL be `snapped_idx`. The processor SHALL emit one INFO log entry with structured fields `cue_id` (= `sub.index`), `char_idx_vad`, `char_idx_final` (= `snapped_idx`), `fallback_reason="grammar_snap"`.
6. **Sanity-gate sub-step (sub-path 3c — grammar fallback):** Otherwise, compute `linear_candidate = round((linear_slice_end_ms_i - sub.start_ms) / duration * len(text))` where `linear_slice_end_ms_i = sub.start_ms + (i * duration) // n`, clamped to `[1, len(text) - 1]`. The text cut index SHALL be `policy.adjust(text, linear_candidate, search_radius)` using the existing legacy fallback `search_radius` (the same value used by the original fallback path). The time boundary SHALL remain `silence_midpoint` (VAD time signal is preserved even when text falls back). The processor SHALL emit one INFO log entry with structured fields `cue_id` (= `sub.index`), `char_idx_vad`, `char_idx_final`, `fallback_reason="grammar_fallback"`.

For each boundary, exactly one of sub-paths 3a, 3b, 3c SHALL execute. INFO log entries SHALL NOT be emitted on sub-path 3a.

**Fallback path (grammar-based, text → time, when VAD signal is unavailable):** If `silence_midpoint is None` OR `tokens` is empty, the processor SHALL fall back to the previous algorithm for that boundary:

- Text index: `policy.adjust(text, candidate_text_idx_i, search_radius)` where `candidate_text_idx_i = round((linear_slice_end_ms_i - sub.start_ms) / duration * len(text))` and `linear_slice_end_ms_i = sub.start_ms + (i * duration) // n`.
- Time boundary: `time_policy.adjust(linear_slice_end_ms_i, sub.start_ms, sub.end_ms)`.

The processor SHALL emit a DEBUG log entry when this fallback path activates, naming the cue index and the reason (`"no_silence"` or `"empty_token_map"`). The DEBUG log on the legacy fallback path is unchanged from the prior specification and is distinct from the INFO logs emitted by sub-paths 3b and 3c.

**Invariants (unchanged from prior specification):**

- `boundaries[0] = sub.start_ms`, `boundaries[n] = sub.end_ms`.
- If two consecutive `boundaries[i]` and `boundaries[i+1]` collide such that `boundaries[i] >= boundaries[i+1]`, the processor SHALL set `boundaries[i+1] = boundaries[i] + 1` and emit a DEBUG log entry.
- If `len(text) <= 1`, the processor SHALL leave the cue intact and emit a DEBUG log entry; neither policy SHALL be called.
- If two consecutive text-split indices are equal, the processor SHALL emit an empty-text child for the second slice and emit a DEBUG log entry.
- Slices SHALL preserve total time span (first child `start_ms` equals original, last child `end_ms` equals original) and total text (concatenation of all child texts equals the original text).

The processor SHALL NOT call `time_policy.pick` when `len(text) <= 1`.

#### Scenario: VAD-driven path 3a uses char_idx_vad when grammar permits

- **GIVEN** a cue `("あいうえおかきくけこ", 0, 9000)`, `split_max_duration_ms=6000`, tokens `[AlignedToken("あいうえお", 0, 4000, 1.0), AlignedToken("かきくけこ", 4000, 9000, 1.0)]`, `time_policy.pick` returning `4200`, and a `policy` whose `is_valid(text, 5)` returns `True`
- **WHEN** the processor runs
- **THEN** the result has two cues with first text `"あいうえお"` and time boundaries `(0, 4200)` / `(4200, 9000)`
- **AND** no INFO log entry with `fallback_reason="grammar_snap"` or `"grammar_fallback"` SHALL be emitted

#### Scenario: VAD-driven path 3b snaps to nearby valid boundary and logs grammar_snap

- **GIVEN** a cue with text `"専攻しておりました"` (length 9, `sub.index=1`), tokens whose cumulative character counts produce `char_idx_vad = 8` (a leading-final boundary), `time_policy.pick` returning a non-None midpoint, `config.vad_grammar_search_radius = 2`, and a `JapaneseSplitBoundaryPolicy` whose default rules mark `8` as INVALID and yield a valid snap target at `6`
- **WHEN** the processor runs and reaches sub-path 3b for this boundary
- **THEN** the text cut index for that boundary MUST equal `6`
- **AND** exactly one INFO log entry MUST be emitted with `cue_id=1`, `char_idx_vad=8`, `char_idx_final=6`, `fallback_reason="grammar_snap"`

#### Scenario: VAD-driven path 3c falls back to linear candidate and logs grammar_fallback

- **GIVEN** a cue with text `"カタカナテストです"` (length 9, `sub.index=1`), tokens whose cumulative character counts produce `char_idx_vad = 4` (mid-katakana, INVALID), `time_policy.pick` returning a non-None midpoint, `config.vad_grammar_search_radius = 2` (no valid index in `[2, 6]`), and a `JapaneseSplitBoundaryPolicy` whose default rules find a valid index at `7` when given the linear candidate plus the legacy fallback `search_radius`
- **WHEN** the processor runs and reaches sub-path 3c for this boundary
- **THEN** the text cut index for that boundary MUST equal `7`
- **AND** the time boundary for that slice MUST equal the silence midpoint returned by `time_policy.pick`
- **AND** exactly one INFO log entry MUST be emitted with `cue_id=1`, `char_idx_vad=4`, `char_idx_final=7`, `fallback_reason="grammar_fallback"`

#### Scenario: Legacy fallback activates when pick returns None

- **GIVEN** a cue `("あいうえおかきくけこ", 0, 9000)`, `split_max_duration_ms=6000`, tokens available, and `time_policy.pick` returning `None`
- **WHEN** the processor runs
- **THEN** the result is identical to what `LinearSplitBoundaryPolicy` + `LinearSplitTimePolicy` would produce
- **AND** a DEBUG log entry MUST be emitted with reason `"no_silence"`
- **AND** no INFO log entry with `fallback_reason="grammar_snap"` or `"grammar_fallback"` SHALL be emitted

#### Scenario: Legacy fallback activates when token map is empty for the cue

- **GIVEN** a cue `("あいうえおかきくけこ", 0, 9000)`, `split_max_duration_ms=6000`, `token_map_by_index={}`, and `time_policy.pick` returning a non-None midpoint
- **WHEN** the processor runs
- **THEN** the grammar-based legacy fallback path is used
- **AND** a DEBUG log entry MUST be emitted with reason `"empty_token_map"`
- **AND** no INFO log entry with `fallback_reason="grammar_snap"` or `"grammar_fallback"` SHALL be emitted

#### Scenario: None token_map_by_index treated as empty dict

- **GIVEN** `CharacterBoundarySplitProcessor()` constructed with no `token_map_by_index` argument
- **WHEN** the processor runs against any oversized cue
- **THEN** the processor MUST behave as if `token_map_by_index={}` were passed (legacy fallback path for all cues)

##### Example: three-path decision table for one inner boundary

| `is_valid(char_idx_vad)` | `is_valid(snapped_idx)` after small-radius snap | Sub-path | Final text index | INFO log `fallback_reason` |
| ------------------------ | ------------------------------------------------ | -------- | ---------------- | -------------------------- |
| `True`                   | n/a                                              | 3a       | `char_idx_vad`   | (none)                     |
| `False`                  | `True`                                           | 3b       | `snapped_idx`    | `grammar_snap`             |
| `False`                  | `False`                                          | 3c       | `policy.adjust(text, linear_candidate, legacy_radius)` | `grammar_fallback`         |

<!-- @trace
source: vad-grammar-sanity-gate
updated: 2026-05-09
code:
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/config/models.py
  - docs/architecture/index.md
  - src/talking_parrot/post_processing/split_policy.py
  - src/talking_parrot/post_processing/japanese.py
  - docs/architecture/ADR-0004-VAD-driven切分文法sanity-check整合.md
tests:
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/config/test_loader.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/post_processing/test_split_policy.py
-->