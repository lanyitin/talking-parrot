## 1. Config models & validation

- [x] 1.1 Extend `PostProcessingConfig` in `src/talking_parrot/config/models.py` with the four new fields per the **PostProcessingConfig Japanese split-boundary fields** requirement (`japanese_split_search_radius`, `japanese_split_no_split_units`, `japanese_split_no_leading_particles`, `japanese_split_no_leading_finals`) and add pydantic validators that reject (a) `japanese_split_search_radius` outside `[0, 20]` and (b) empty-string entries in any of the three list fields. TDD: write the failing validator tests in `tests/unit/config/test_models.py` first (one test per scenario in the spec).

## 2. Split boundary policy module

- [x] 2.1 Create `src/talking_parrot/post_processing/split_policy.py` exporting the `SplitBoundaryPolicy` protocol and the `LinearSplitBoundaryPolicy` concrete class per the **SplitBoundaryPolicy protocol defines the snap interface** and **LinearSplitBoundaryPolicy returns the candidate unchanged** requirements. Public symbols MUST have docstrings. TDD: write the failing protocol/no-op tests in `tests/unit/post_processing/test_split_policy.py` first, including the "search radius is ignored" example.
- [x] 2.2 [P] Add `JapaneseSplitBoundaryPolicy` to `src/talking_parrot/post_processing/japanese.py` per the **JapaneseSplitBoundaryPolicy snaps to nearest valid grammar boundary** requirement. Constructor takes a `PostProcessingConfig`. Implement the five validity rules (Mid-katakana, Mid-digit, Mid-no-split-unit, Leading-particle, Leading-final) exactly as listed in the spec, the windowing logic, and the "smallest distance, ties to smaller index" selection. TDD: add the four scenarios from the spec (auxiliary snap, all-katakana fallback, radius zero, leading-particle example) as parametrised tests in `tests/unit/post_processing/test_japanese.py` first.

## 3. Split processors accept policy

- [x] 3.1 Modify `src/talking_parrot/post_processing/character_boundary.py` so `CharacterBoundarySplitProcessor.__init__` accepts `policy: SplitBoundaryPolicy | None = None`, defaults to `LinearSplitBoundaryPolicy()` when `None`, calls `policy.adjust(text, candidate_i, config.japanese_split_search_radius)` after computing the linear candidate, and uses the returned index as the actual text-split point per the modified **CharacterBoundarySplitProcessor splits oversized cues by linear interpolation** requirement. Time-split positions MUST be unchanged by the policy. Handle the equal-consecutive-indices case (emit empty-text child + DEBUG log). TDD: update `tests/unit/post_processing/test_character_boundary.py` first to cover the four scenarios in the modified spec.
- [x] 3.2 [P] Modify `src/talking_parrot/post_processing/time_based.py` so `TimeBasedSplitProcessor.__init__` accepts `policy: SplitBoundaryPolicy | None = None`, defaults to `LinearSplitBoundaryPolicy()` when `None`, and calls `policy.adjust` per the modified **TimeBasedSplitProcessor splits oversized cues proportionally by text length** requirement. TDD: update `tests/unit/post_processing/test_time_based.py` first to cover the three scenarios in the modified spec.

## 4. Factory wiring

- [x] 4.1 Update `DefaultGranularityAwareProcessorFactory.create()` in `src/talking_parrot/post_processing/factory.py` to construct a `JapaneseSplitBoundaryPolicy(ctx.config.post_processing)` when `ctx.config.expected_language == "ja"` and a `LinearSplitBoundaryPolicy()` otherwise, and inject it into the `CharacterBoundarySplitProcessor` (CHARACTER granularity branch) and the `TimeBasedSplitProcessor` (None granularity branch). Do NOT pass any policy to `WordBoundarySplitProcessor`. This satisfies the **Factory injects SplitBoundaryPolicy into split processors based on language** requirement. TDD: extend `tests/unit/post_processing/test_factory.py` first to cover the four scenarios (CHARACTER+ja, CHARACTER+en, None+ja, WORD-no-policy).

## 5. Final verification

- [x] 5.1 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` — all MUST pass with zero errors before marking the change ready for archive.
- [x] 5.2 Run `/spectra-audit` over the diff to confirm no new sharp edges (the new config fields are populated by default; lists reject empty strings; radius is clamped).
- [x] 5.3 Manual eyeball: re-run the CLI on `test-samples/sample1` (the Japanese fixture used by the previous archived change). Diff the new SRT against the prior `sample1.srt`. Verify that at least four of the six previously-reported mid-word splits (`専攻しておりまし / た`, `印象深 / いのは`, `持つよ / うになり`, `携わったプロジェクトの中で、特に印象深 / いのは`, `日本料理にも挑戦し / ていて`, `日本語の勉強を通じて、日本の文化や考え方にも興味を持つよ / うになり`) now break at a grammatically clean boundary. Record the before/after counts.

## 6. Design-decision coverage map

This section exists so the analyzer can verify every design decision is implemented by at least one task above. No additional work — these are pointers, not new tasks.

- [x] 6.1 Decision 1: Introduce a `SplitBoundaryPolicy` abstraction injected into split processors → covered by tasks 2.1, 3.1, 3.2.
- [x] 6.2 Decision 2: Snap by searching a bounded character window with rule-based validity → covered by task 2.2.
- [x] 6.3 Decision 3: Wire the policy via the factory based on `expected_language` → covered by task 4.1.
- [x] 6.4 Decision 4: Rule-based, no new dependency → covered by task 2.2 (implementation uses only stdlib regex/character-class checks; no import of `fugashi`, `mecab-python3`, or `sudachipy`). Verify in task 5.1 that `pyproject.toml` has no new dependency.
- [x] 6.5 Decision 5: Defaults for the configurable lists are populated, not empty → covered by task 1.1 (defaults specified in spec are non-empty) and verified by the "Default fields populated" scenario.
