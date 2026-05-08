## 1. Config — split-time snap radius field

- [x] 1.1 Add failing tests in `tests/unit/config/test_models.py` covering Decision 5: New config field `split_time_snap_radius_ms` with range validation — default 250, accepted boundaries 0 and 2000, rejected -1 and 2001 — per the **PostProcessingConfig split-time snap radius field** requirement.
- [x] 1.2 Implement the field on `PostProcessingConfig` in `src/talking_parrot/config/models.py` with a pydantic field validator enforcing `[0, 2000]`; make tests from 1.1 pass.

## 2. SplitTimePolicy protocol and concrete policies

- [x] 2.1 [P] Add failing tests in `tests/unit/post_processing/test_split_time_policy.py` for the **SplitTimePolicy protocol defines the time-snap interface** requirement — `runtime_checkable`, return value strictly inside cue.
- [x] 2.2 [P] Add failing tests in the same file for the **LinearSplitTimePolicy returns the candidate unchanged** requirement — no-op behaviour, ignores cue bounds.
- [x] 2.3 [P] Add failing tests in the same file for the **VadAlignedSplitTimePolicy snaps to nearest silence midpoint within radius** requirement, exercising Decision 1: Introduce a `SplitTimePolicy` protocol parallel to `SplitBoundaryPolicy` AND Decision 2: Snap to silence midpoint, clamped to the open interval `(cue_start_ms, cue_end_ms)`: inside-radius hit, no-hit fallback, nearer-of-two, tie-break-prefers-smaller, midpoint-equals-cue-end is rejected, negative radius rejected at construction, constructor copy isolates from caller mutation.
- [x] 2.4 Create `src/talking_parrot/post_processing/split_time_policy.py` exporting `SplitTimePolicy` (`@runtime_checkable` Protocol), `LinearSplitTimePolicy`, and `VadAlignedSplitTimePolicy`; make tests from 2.1, 2.2, 2.3 pass.

## 3. CharacterBoundarySplitProcessor — time-policy injection

- [x] 3.1 Update `tests/unit/post_processing/test_character_boundary.py` to fail on the new behaviour mandated by Decision 4: Slice continuity — a single adjusted boundary serves both adjacent slices: default-constructor parity with both linear policies, stub time-policy snaps `(start_ms, end_ms)` pairs, time-boundary collision emits 1ms-minimum slice and DEBUG log, single-character cue does not call either policy. These cover the modified **CharacterBoundarySplitProcessor splits oversized cues by linear interpolation** requirement.
- [x] 3.2 Add `time_policy: SplitTimePolicy | None = None` to `CharacterBoundarySplitProcessor.__init__` in `src/talking_parrot/post_processing/character_boundary.py`; rebuild slice loop to compute `boundaries` from per-inner-boundary `time_policy.adjust` calls; implement the 1ms collision rule and DEBUG log.

## 4. TimeBasedSplitProcessor — time-policy injection

- [x] 4.1 Update `tests/unit/post_processing/test_time_based.py` with failing tests for the modified **TimeBasedSplitProcessor splits oversized cues proportionally by text length** requirement: default-constructor parity, stub time-policy snaps boundaries, collision emits 1ms slice and DEBUG log, sub-threshold cue still skips both policies.
- [x] 4.2 Add `time_policy: SplitTimePolicy | None = None` to `TimeBasedSplitProcessor.__init__` in `src/talking_parrot/post_processing/time_based.py`; rebuild slice loop using the same `boundaries` pattern as task 3.2.

## 5. Factory wiring

- [x] 5.1 [P] Update `tests/unit/post_processing/test_factory.py` with failing tests for the new **Factory injects SplitTimePolicy into split processors based on VAD context** requirement, covering Decision 3: Derive silence intervals from `vad_segments` gaps in the factory, not in the policy AND Decision 6: Apply the time policy to CHARACTER and time-based-fallback paths only — non-empty VAD + radius>0 → `VadAlignedSplitTimePolicy` for CHARACTER and None paths, empty `vad_segments` → `LinearSplitTimePolicy`, radius=0 → `LinearSplitTimePolicy`, WORD path receives no `time_policy` kwarg, non-positive gaps filtered.
- [x] 5.2 [P] Update `tests/unit/post_processing/test_factory.py` with failing tests for the modified **Factory injects SplitBoundaryPolicy into split processors based on language** requirement: `policy` and `time_policy` are independent and passed in the same constructor call.
- [x] 5.3 Implement `_build_time_policy(ctx)` and `_build_silences(ctx)` helpers in `src/talking_parrot/post_processing/factory.py`; pass `time_policy=...` to `CharacterBoundarySplitProcessor` (CHARACTER branch) and `TimeBasedSplitProcessor` (None branch); make tests from 5.1 and 5.2 pass.

## 6. Integration verification and regression

- [x] 6.1 Re-run `tests/integration/test_pipeline_smoke.py` end-to-end and confirm it still passes (it has no `vad_segments` fixture, so the factory path falls back to `LinearSplitTimePolicy()` and existing assertions hold).
- [x] 6.2 Run the full pre-commit gate: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` — all must report zero errors.
