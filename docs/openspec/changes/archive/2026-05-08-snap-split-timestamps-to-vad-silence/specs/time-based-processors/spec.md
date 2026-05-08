## MODIFIED Requirements

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
