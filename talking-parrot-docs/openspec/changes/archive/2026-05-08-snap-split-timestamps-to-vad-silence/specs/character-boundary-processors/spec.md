## MODIFIED Requirements

### Requirement: CharacterBoundarySplitProcessor splits oversized cues by linear interpolation

`CharacterBoundarySplitProcessor` SHALL split any cue whose `end_ms - start_ms > config.split_max_duration_ms` into `n = ceil(duration / config.split_max_duration_ms)` slices. For each inner boundary `i` in `[1, n - 1]` the processor SHALL compute:

- `candidate_text_idx_i = round((linear_slice_end_ms_i - sub.start_ms) / cue_duration_ms * len(text))` where `linear_slice_end_ms_i = sub.start_ms + (i * cue_duration_ms) // n`
- `candidate_time_ms_i = linear_slice_end_ms_i`

The processor SHALL then:

- Call `text_idx_i = boundary_policy.adjust(text, candidate_text_idx_i, search_radius)` where `boundary_policy` is a `SplitBoundaryPolicy` injected via the constructor (default: `LinearSplitBoundaryPolicy()`) and `search_radius = config.japanese_split_search_radius`.
- Call `time_ms_i = time_policy.adjust(candidate_time_ms_i, sub.start_ms, sub.end_ms)` where `time_policy` is a `SplitTimePolicy` injected via the constructor (default: `LinearSplitTimePolicy()`).

The processor SHALL define `boundaries[0] = sub.start_ms`, `boundaries[n] = sub.end_ms`, and `boundaries[i] = time_ms_i` for `i` in `[1, n - 1]`. Slice `i` (0-indexed) SHALL have `start_ms = boundaries[i]` and `end_ms = boundaries[i + 1]`. The text-split indices SHALL be applied as before to derive each slice's text. Slices SHALL preserve total `text` (concatenation of all child texts equals the original `text`) and total time span (first child's `start_ms` equals original, last child's `end_ms` equals original).

The constructor signature SHALL be `CharacterBoundarySplitProcessor(policy: SplitBoundaryPolicy | None = None, time_policy: SplitTimePolicy | None = None)`. When `policy is None`, the processor SHALL substitute `LinearSplitBoundaryPolicy()`. When `time_policy is None`, the processor SHALL substitute `LinearSplitTimePolicy()`.

The processor SHALL NOT consume an `AlignedToken` map; only `Subtitle` fields, `PostProcessingConfig`, and the two injected policies are read.

If `len(text) <= 1`, the processor SHALL leave the cue intact and emit a DEBUG log entry naming the cue index. Neither policy SHALL be called in this case.

If after policy adjustment two consecutive text-split indices are equal, the processor SHALL emit an empty-text child for the second slice (preserving the time-span invariant) and emit a DEBUG log entry naming the cue index.

If after time-policy adjustment two consecutive `boundaries[i]` and `boundaries[i + 1]` collide such that `boundaries[i] >= boundaries[i + 1]`, the processor SHALL set `boundaries[i + 1] = boundaries[i] + 1` (1 ms minimum slice length), preserve the `Subtitle` invariant `start_ms < end_ms`, and emit a DEBUG log entry naming the cue index.

#### Scenario: A 9-second cue is split into two equal-time character slices

- **GIVEN** a single cue `("あいうえおかきくけこ", 0, 9000)` (10 characters), `split_max_duration_ms=6000`, a `LinearSplitBoundaryPolicy`, and a `LinearSplitTimePolicy`
- **WHEN** `CharacterBoundarySplitProcessor(policy=LinearSplitBoundaryPolicy(), time_policy=LinearSplitTimePolicy()).process([sub], cfg)` is called
- **THEN** the result has two cues: `("あいうえお", 0, 4500, index=1)` and `("かきくけこ", 4500, 9000, index=2)`

#### Scenario: A single-character cue cannot be split

- **GIVEN** a single cue `("。", 0, 9000)` and `split_max_duration_ms=6000`
- **WHEN** the processor runs
- **THEN** the cue SHALL be returned unchanged (only `index` re-numbered) and a DEBUG log entry SHALL be emitted
- **AND** the injected boundary policy's `adjust` MUST NOT be called
- **AND** the injected time policy's `adjust` MUST NOT be called

#### Scenario: Time policy snaps slice boundary to silence midpoint

- **GIVEN** a single cue `("あいうえおかきくけこ", 0, 9000)`, `split_max_duration_ms=6000`, a `LinearSplitBoundaryPolicy`, and a stub `SplitTimePolicy` that returns `4700` for any candidate
- **WHEN** `CharacterBoundarySplitProcessor(policy=LinearSplitBoundaryPolicy(), time_policy=stub).process([sub], cfg)` is called
- **THEN** the result has two cues whose `(start_ms, end_ms)` pairs are `(0, 4700)` and `(4700, 9000)`
- **AND** the concatenation of their text MUST equal `"あいうえおかきくけこ"`

#### Scenario: Default constructor uses both linear policies

- **GIVEN** `CharacterBoundarySplitProcessor()` (no policy arguments)
- **WHEN** the processor runs against any cue
- **THEN** the resulting splits MUST be identical to those produced when `LinearSplitBoundaryPolicy()` and `LinearSplitTimePolicy()` are explicitly passed

#### Scenario: Time-boundary collision emits 1ms-minimum slice

- **GIVEN** a single cue `("あいうえおかきくけこさし", 0, 12000)` (12 characters), `split_max_duration_ms=4000`, a `LinearSplitBoundaryPolicy`, and a stub `SplitTimePolicy` that returns `8000` for both inner-boundary candidates (collision)
- **WHEN** the processor runs
- **THEN** the result has three cues whose `(start_ms, end_ms)` pairs are `(0, 8000)`, `(8000, 8001)`, `(8001, 12000)`
- **AND** a DEBUG log entry MUST be emitted naming the cue index

##### Example: Boundary order without collision

- **GIVEN** a 4-slice cue with linear candidates at `(3000, 6000, 9000)` and a time policy returning `(2900, 6100, 8900)`
- **WHEN** the processor builds `boundaries`
- **THEN** `boundaries` MUST equal `[0, 2900, 6100, 8900, 12000]` and produce slices `(0, 2900)`, `(2900, 6100)`, `(6100, 8900)`, `(8900, 12000)`

<!-- @trace
source: snap-split-timestamps-to-vad-silence
-->
