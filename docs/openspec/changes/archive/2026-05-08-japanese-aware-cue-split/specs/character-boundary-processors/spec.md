## MODIFIED Requirements

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

