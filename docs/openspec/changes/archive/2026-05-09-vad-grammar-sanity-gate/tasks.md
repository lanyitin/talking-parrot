## 1. Config field

- [x] 1.1 [P] Write failing pydantic tests in `tests/unit/config/test_models.py` covering `PostProcessingConfig exposes vad_grammar_search_radius`: default value `2`, accepts `0`, rejects `-1` with `ValidationError`.
- [x] 1.2 [P] Write failing loader tests in `tests/unit/config/test_loader.py` for the YAML round-trip: omitted key → `2`; explicit `0` → `0`; explicit `-1` → `ValidationError`.
- [x] 1.3 Add `vad_grammar_search_radius: int = 2` to `PostProcessingConfig` in `src/talking_parrot/config/models.py` with a `>= 0` validator, then run the tests from 1.1 and 1.2 to green.

## 2. SplitBoundaryPolicy protocol and implementations

- [x] 2.1 [P] Write failing tests in `tests/unit/post_processing/test_split_policy.py` for `SplitBoundaryPolicy protocol declares public is_valid method`: assert the protocol has an `is_valid` attribute, and assert the radius-0 fixed-point contract holds for both shipped implementations.
- [x] 2.2 [P] Write failing tests in `tests/unit/post_processing/test_split_policy.py` for `LinearSplitBoundaryPolicy.is_valid always returns True`: every index in `[1, len(text)-1]` returns `True` for assorted texts.
- [x] 2.3 [P] Write failing tests in `tests/unit/post_processing/test_japanese.py` for `JapaneseSplitBoundaryPolicy.is_valid exposes the existing rule check`: cover one positive case (valid index) and one negative case per rule (mid-katakana, mid-digit, mid-no-split-unit, leading-particle, leading-final). Include the `専攻しておりました` index `8` case from ADR-0004.
- [x] 2.4 Add `is_valid(self, text, index) -> bool` to the `SplitBoundaryPolicy` protocol in `src/talking_parrot/post_processing/split_policy.py`. Implement `LinearSplitBoundaryPolicy.is_valid` to return `True` unconditionally for in-range indices.
- [x] 2.5 Refactor `JapaneseSplitBoundaryPolicy` in `src/talking_parrot/post_processing/japanese.py` so the existing private `_is_valid` rule check is exposed as the public `is_valid`, and `adjust` routes through the same predicate (no duplicated rule logic). Run tests 2.1–2.3 to green.

## 3. CharacterBoundarySplitProcessor sanity gate

- [x] 3.1 Write failing unit tests in `tests/unit/post_processing/test_character_boundary.py` for `CharacterBoundarySplitProcessor splits oversized cues by linear interpolation` covering the three sanity-gate sub-paths: 3a (VAD valid, no log), 3b (grammar snap with INFO `grammar_snap` log), 3c (grammar fallback with INFO `grammar_fallback` log). Use stub `time_policy` and `policy` to drive each branch deterministically.
- [x] 3.2 [P] Write failing log-assertion tests verifying the structured INFO log fields `cue_id`, `char_idx_vad`, `char_idx_final`, `fallback_reason` for sub-paths 3b and 3c, and verifying that sub-path 3a emits no INFO log with these reasons.
- [x] 3.3 [P] Write failing regression tests for the legacy fallback path (`silence_midpoint is None` and empty `token_map`): existing DEBUG `no_silence` / `empty_token_map` log behavior is unchanged and no new INFO log is emitted.
- [x] 3.4 Implement the three-stage sanity gate in `CharacterBoundarySplitProcessor` (`src/talking_parrot/post_processing/character_boundary.py`): after computing `char_idx_vad`, branch on `policy.is_valid` (3a) → `policy.adjust` with `config.vad_grammar_search_radius` then `is_valid` recheck (3b) → linear-candidate `policy.adjust` with the legacy fallback radius (3c). Time boundary stays `silence_midpoint` in all three sub-paths.
- [x] 3.5 Wire the new INFO log calls in `character_boundary.py` using the project's structured logging conventions (`logging_config.py`). Run tests 3.1–3.3 to green.

## 4. Integration and verification

- [x] 4.1 Update `src/talking_parrot/post_processing/factory.py` (and any wiring that constructs `CharacterBoundarySplitProcessor` from `PostProcessingConfig`) to pass `config.vad_grammar_search_radius` through to the processor. Add a wiring test in `tests/unit/post_processing/test_factory.py`.
- [x] 4.2 Run the full pipeline against `test-samples/sample1` and confirm the previously broken cuts (`専攻しておりまし／た`, `覚えていま／す`) are now snapped to a valid boundary or pushed back via fallback. Capture the resulting cue list and the emitted `grammar_snap` / `grammar_fallback` INFO logs in the change directory under `notes-sample1.md` for archival.
- [x] 4.3 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` — all must pass with zero errors before the change is ready to archive.
