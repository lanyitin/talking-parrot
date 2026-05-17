## MODIFIED Requirements

### Requirement: TimeBasedSplitProcessor splits oversized cues proportionally by text length

`TimeBasedSplitProcessor` SHALL split any cue whose `end_ms - start_ms > config.split_max_duration_ms` into `n = ceil(duration / config.split_max_duration_ms)` equal-time slices. For each slice `i` (1-indexed in `[1, n]`), the candidate text split index SHALL be `candidate_i = round(i / n * len(text))`. The processor SHALL then call `policy.adjust(text, candidate_i, search_radius)` where `policy` is a `SplitBoundaryPolicy` injected via the constructor (default: `LinearSplitBoundaryPolicy()`) and `search_radius = config.japanese_split_search_radius`. The returned index SHALL be used as the actual split point. The concatenation of all child texts SHALL equal the original `text`, and the first child's `start_ms` and the last child's `end_ms` SHALL equal the original cue's bounds. Time-split positions are unchanged by the policy; only the text-split positions are adjusted.

The constructor signature SHALL be `TimeBasedSplitProcessor(policy: SplitBoundaryPolicy | None = None)`. When `policy is None`, the processor SHALL substitute `LinearSplitBoundaryPolicy()`.

If `len(text) <= 1`, the cue SHALL be returned unchanged and a DEBUG log entry SHALL be emitted. The policy SHALL NOT be called in this case.

If after policy adjustment two consecutive slice text-indices are equal, the processor SHALL emit an empty-text child for the later slice (preserving the time-span invariant) and emit a DEBUG log entry naming the cue index.

#### Scenario: A 12-second cue is split into two equal-time slices

- **GIVEN** a cue `("the quick brown fox", 0, 12000)` (19 characters), `split_max_duration_ms=6000`, and a `LinearSplitBoundaryPolicy`
- **WHEN** `TimeBasedSplitProcessor(policy=LinearSplitBoundaryPolicy()).process([sub], cfg)` is called
- **THEN** the result has two cues whose `start_ms` / `end_ms` pairs are `(0, 6000)` and `(6000, 12000)`, whose text pieces concatenate to `"the quick brown fox"`, and whose indices are `1` and `2`

#### Scenario: A cue shorter than the split threshold is unchanged

- **GIVEN** a cue `("ok", 0, 3000)` and `split_max_duration_ms=6000`
- **WHEN** the processor runs
- **THEN** the cue is returned unchanged (only `index` re-numbered)
- **AND** the injected policy's `adjust` MUST NOT be called

#### Scenario: Default constructor uses the linear policy

- **GIVEN** `TimeBasedSplitProcessor()` (no policy argument)
- **WHEN** the processor runs against any cue
- **THEN** the resulting splits MUST be identical to those produced when `LinearSplitBoundaryPolicy()` is explicitly passed

