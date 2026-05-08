## 1. [P] Write failing tests for SplitTimePolicy.pick() (RED)

- [x] 1.1 Write unit tests for `LinearSplitTimePolicy.pick` returning `None` — covers modified Requirement `LinearSplitTimePolicy returns the candidate unchanged`, Decision 2: LinearSplitTimePolicy.pick always returns None. Tests MUST fail before implementation. File: `tests/unit/post_processing/test_split_time_policy.py`.
- [x] 1.2 Write unit tests for `VadAlignedSplitTimePolicy.pick` — covers added Requirement `VadAlignedSplitTimePolicy.pick returns best silence midpoint inside cue window` including pick midpoint selection, pick returns None when no silence inside cue, pick tie-breaks to smaller midpoint (Decision 2: VadAlignedSplitTimePolicy.pick, tie-breaking). Tests MUST fail before implementation. File: `tests/unit/post_processing/test_split_time_policy.py`.

## 2. Implement SplitTimePolicy.pick() on both concrete classes (GREEN)

- [x] 2.1 Extend the `SplitTimePolicy` protocol with `pick(cue_start_ms: int, cue_end_ms: int) -> int | None` — satisfies modified Requirement `SplitTimePolicy protocol defines the time-snap interface`, Decision 2: SplitTimePolicy gains a pick() method. File: `src/talking_parrot/post_processing/split_time_policy.py`.
- [x] 2.2 Implement `LinearSplitTimePolicy.pick` returning `None` unconditionally — satisfies modified Requirement `LinearSplitTimePolicy returns the candidate unchanged`, Decision 2. File: `src/talking_parrot/post_processing/split_time_policy.py`.
- [x] 2.3 Implement `VadAlignedSplitTimePolicy.pick` using `center_ms = (cue_start_ms + cue_end_ms) // 2` as reference, same tie-breaking as `adjust` — satisfies added Requirement `VadAlignedSplitTimePolicy.pick returns best silence midpoint inside cue window`, Decision 2: VAD-driven algorithm. File: `src/talking_parrot/post_processing/split_time_policy.py`.

## 3. [P] Write failing tests for CharacterBoundarySplitProcessor VAD-driven path (RED)

- [x] 3.1 Write unit tests for VAD-driven primary path (silence midpoint found + tokens present → char idx from binary search) — covers modified Requirement `CharacterBoundarySplitProcessor splits oversized cues by linear interpolation`, Decision 3: VAD-driven algorithm — silence pick then token binary search. File: `tests/unit/post_processing/test_character_boundary.py`.
- [x] 3.2 Write unit tests for fallback when `pick()` returns `None` and fallback when token map is empty for cue — covers Decision 4: Fallback when pick() returns None or token map is empty, and Scenario `None token_map_by_index treated as empty dict`. File: `tests/unit/post_processing/test_character_boundary.py`.

## 4. [P] Write failing tests for factory CHARACTER token map injection (RED)

- [x] 4.1 Write unit tests verifying `CharacterBoundarySplitProcessor.token_map_by_index` is populated by the factory — covers modified Requirement `Factory returns character-boundary group for CHARACTER granularity`, Scenario `CHARACTER path injects token map into CharacterBoundarySplitProcessor`, Decision 1: Factory threads token_map_by_index into CharacterBoundarySplitProcessor. File: `tests/unit/post_processing/test_factory.py`.

## 5. Implement CharacterBoundarySplitProcessor with token_map_by_index and pick() (GREEN)

- [x] 5.1 Add `token_map_by_index: dict[int, list[AlignedToken]] | None = None` to `CharacterBoundarySplitProcessor` constructor, stored as `self._token_map_by_index` defaulting to `{}` — satisfies modified Requirement `CharacterBoundarySplitProcessor splits oversized cues by linear interpolation`, Decision 1. File: `src/talking_parrot/post_processing/character_boundary.py`.
- [x] 5.2 Implement primary VAD-driven path: call `time_policy.pick`, binary-search tokens by `start_ms` for `silence_midpoint`, derive `char_idx` — satisfies Decision 3: VAD-driven algorithm — silence pick then token binary search. File: `src/talking_parrot/post_processing/character_boundary.py`.
- [x] 5.3 Implement fallback path with DEBUG log entries for `"no_silence"` and `"empty_token_map"` reasons — satisfies Decision 4: Fallback when pick() returns None or token map is empty. File: `src/talking_parrot/post_processing/character_boundary.py`.

## 6. Extend factory CHARACTER path to inject token_map_by_index (GREEN)

- [x] 6.1 In `DefaultGranularityAwareProcessorFactory.create` CHARACTER branch, call `_build_token_map(ctx.transcription_results)` and pass result as `token_map_by_index` to `CharacterBoundarySplitProcessor` — satisfies modified Requirement `Factory returns character-boundary group for CHARACTER granularity` and Decision 1: Factory threads token_map_by_index into CharacterBoundarySplitProcessor. WORD branch and `None` branch MUST remain unchanged (Decision 5: WORD path and TIME-based path are unchanged). File: `src/talking_parrot/post_processing/factory.py`.

## 7. Integration verification and lint/type checks

- [x] 7.1 Verify full CHARACTER pipeline end-to-end: factory produces `CharacterBoundarySplitProcessor` with both `VadAlignedSplitTimePolicy` and `token_map_by_index` when VAD context is non-empty and `split_time_snap_radius_ms > 0`; primary VAD-driven path executes without fallback when qualifying silence exists (Decision 6: Data-flow diagram). File: `tests/unit/post_processing/test_factory.py`.
- [x] 7.2 Run full test suite, ruff lint, ruff format check, and mypy — zero errors required before marking this change ready for apply.
