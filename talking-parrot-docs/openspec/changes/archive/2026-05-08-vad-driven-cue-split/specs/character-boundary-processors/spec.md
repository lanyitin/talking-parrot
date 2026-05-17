## MODIFIED Requirements

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

**Primary path (VAD-driven, time → text):** For each inner boundary `i` in `[1, n-1]`, the processor SHALL:

1. Call `silence_midpoint = time_policy.pick(sub.start_ms, sub.end_ms)`.
2. Look up `tokens = token_map_by_index.get(sub.index, [])`.
3. If `silence_midpoint is not None` AND `tokens` is non-empty: binary-search `tokens` by `AlignedToken.end_ms` to find the first token whose `end_ms >= silence_midpoint` (equivalently, the token whose acoustic interval contains the silence, or the first token that follows it). Let `found_idx` be that token's position in `tokens`. When no such token exists, `found_idx = len(tokens)`. The text cut index SHALL be the cumulative character count `len("".join(t.word for t in tokens[:found_idx]))`, clamped to `[1, len(text) - 1]` to ensure non-empty slices. The time boundary SHALL be `silence_midpoint`.

**Fallback path (grammar-based, text → time):** If `silence_midpoint is None` OR `tokens` is empty, the processor SHALL fall back to the previous algorithm for that boundary:

- Text index: `boundary_policy.adjust(text, candidate_text_idx_i, search_radius)` where `candidate_text_idx_i = round((linear_slice_end_ms_i - sub.start_ms) / duration * len(text))` and `linear_slice_end_ms_i = sub.start_ms + (i * duration) // n`.
- Time boundary: `time_policy.adjust(linear_slice_end_ms_i, sub.start_ms, sub.end_ms)`.

The processor SHALL emit a DEBUG log entry when the fallback activates, naming the cue index and the reason (`"no_silence"` or `"empty_token_map"`).

**Invariants (unchanged from prior specification):**

- `boundaries[0] = sub.start_ms`, `boundaries[n] = sub.end_ms`.
- If two consecutive `boundaries[i]` and `boundaries[i+1]` collide such that `boundaries[i] >= boundaries[i+1]`, the processor SHALL set `boundaries[i+1] = boundaries[i] + 1` and emit a DEBUG log entry.
- If `len(text) <= 1`, the processor SHALL leave the cue intact and emit a DEBUG log entry; neither policy SHALL be called.
- If two consecutive text-split indices are equal, the processor SHALL emit an empty-text child for the second slice and emit a DEBUG log entry.
- Slices SHALL preserve total time span (first child `start_ms` equals original, last child `end_ms` equals original) and total text (concatenation of all child texts equals the original text).

The processor SHALL NOT call `time_policy.pick` when `len(text) <= 1`.

#### Scenario: VAD-driven path selects silence midpoint and derives char index from tokens

- **GIVEN** a cue `("あいうえおかきくけこ", 0, 9000)`, `split_max_duration_ms=6000`, tokens `[AlignedToken("あいうえお", 0, 4000, 1.0), AlignedToken("かきくけこ", 4000, 9000, 1.0)]`, and `time_policy.pick` returning `4200`
- **WHEN** `CharacterBoundarySplitProcessor(token_map_by_index={1: tokens}, time_policy=stub_policy).process([sub], cfg)` is called
- **THEN** the result has two cues
- **AND** the first cue text MUST equal `"あいうえお"` (the token at or after ms 4200 is the second token, so cut before it)
- **AND** the time boundaries MUST be `(0, 4200)` and `(4200, 9000)`

#### Scenario: Fallback activates when pick returns None

- **GIVEN** a cue `("あいうえおかきくけこ", 0, 9000)`, `split_max_duration_ms=6000`, tokens available, and `time_policy.pick` returning `None`
- **WHEN** `CharacterBoundarySplitProcessor(token_map_by_index={1: tokens}, time_policy=linear_policy).process([sub], cfg)` is called
- **THEN** the result is identical to what `LinearSplitBoundaryPolicy` + `LinearSplitTimePolicy` would produce
- **AND** a DEBUG log entry MUST be emitted with reason `"no_silence"`

#### Scenario: Fallback activates when token map is empty for the cue

- **GIVEN** a cue `("あいうえおかきくけこ", 0, 9000)`, `split_max_duration_ms=6000`, `token_map_by_index={}`, and `time_policy.pick` returning a non-None midpoint
- **WHEN** `CharacterBoundarySplitProcessor(token_map_by_index={}, time_policy=stub_policy).process([sub], cfg)` is called
- **THEN** the grammar-based fallback path is used
- **AND** a DEBUG log entry MUST be emitted with reason `"empty_token_map"`

#### Scenario: None token_map_by_index treated as empty dict

- **GIVEN** `CharacterBoundarySplitProcessor()` constructed with no `token_map_by_index` argument
- **WHEN** the processor runs against any oversized cue
- **THEN** the processor MUST behave as if `token_map_by_index={}` were passed (fallback path for all cues)
