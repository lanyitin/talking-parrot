## 1. Spec delta — Requirement: JapaneseSplitBoundaryPolicy snaps to nearest valid grammar boundary

- [x] 1.1 Update step 3 in `docs/openspec/specs/split-boundary-policy/spec.md` to describe the conditional tie-break (straddling no-split unit → larger; otherwise → smaller). The MODIFIED Requirement is "JapaneseSplitBoundaryPolicy snaps to nearest valid grammar boundary".
- [x] 1.2 Add a Scenario "Tie-break snaps PAST a straddling no-split unit" using `text="覚えています 卒業"`, `candidate_index=5`, `search_radius=2`, default config; expected return `6`.
- [x] 1.3 Bump `@trace updated:` to `2026-05-09`.

## 2. Helper extraction and tie-break branch

- [x] 2.1 Write a failing regression test `test_no_split_unit_straddle_tie_breaks_after_unit` in `tests/unit/post_processing/test_japanese.py` mirroring the spec scenario from 1.2.
- [x] 2.2 Write a guard test `test_no_straddle_keeps_smaller_on_tie` asserting `_straddles_no_split_unit` returns `False` for ASCII text where no unit applies (so the smaller-on-tie default still holds).
- [x] 2.3 Add a private `_straddles_no_split_unit(self, text, index) -> bool` helper to `JapaneseSplitBoundaryPolicy` in `src/talking_parrot/post_processing/japanese.py` carrying the existing Mid-no-split-unit straddle check.
- [x] 2.4 Refactor `is_valid` to call `_straddles_no_split_unit` instead of inlining the loop (no behavioural change).
- [x] 2.5 In `adjust`, compute `prefer_after_unit = self._straddles_no_split_unit(text, candidate_index)` once before the search loop. On `dist == best_dist`, when `prefer_after_unit` is `True`, accept the larger index (loop ascends → simply assign). Run tests 2.1 and 2.2 to green.

## 3. Verification

- [x] 3.1 `uv run pytest` — 618 tests pass (43 in `test_japanese.py` including the two new ones).
- [x] 3.2 `uv run ruff check` and `uv run ruff format --check` on the modified files — clean.
- [x] 3.3 Confirm pre-existing `mypy` error in `alignment/japanese_backend.py:144` is unrelated (verified by stashing this change and re-running `uv run mypy src` — same error persists).
- [x] 3.4 Re-run the pipeline against `test-samples/sample1` and inspect cue 10 manually. Confirmed: cue 10 no longer starts with `「ます 」`; `「覚えています」` stays whole in the previous cue.
