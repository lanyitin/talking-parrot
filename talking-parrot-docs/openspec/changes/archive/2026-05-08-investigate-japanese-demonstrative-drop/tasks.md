## 1. Phase 1 — Instrument

- [x] 1.1 Add a DEBUG-level `structlog` log in `src/talking_parrot/post_processing/japanese.py` `JapaneseFillerProcessor.process()` that fires once per filler removal and includes fields: `original_text` (the cue text before stripping), `matched_filler` (the exact filler token from the configured list that matched), `cue_index` (the original cue's `index`), and `start_ms`. Place the log call immediately before the filler is stripped from the cue. TDD: extend `tests/unit/post_processing/test_japanese.py` with a test asserting the log entry's keys and values via `structlog.testing.capture_logs()` or the existing logging fixture pattern used elsewhere in the test suite.
- [x] 1.2 [P] Verify in `src/talking_parrot/stages/hallucination_filter_stage.py` that the existing per-drop DEBUG log includes the dropped cue's `text` field. If it does not, add `text=result.text` (or the truncated equivalent if a length cap is in force — cap at 200 characters) to the log keyword arguments. Update `tests/unit/stages/test_hallucination_filter_stage.py` to assert `text` is present in the per-drop log.

## 2. Phase 1 — Reproduce and identify

- [x] 2.1 Run the CLI on `test-samples/sample1` with log level `DEBUG` redirected to a file. Grep the log for the substring `その`. Identify which stage's log mentions `その` last before the SRT writer runs. Record the finding in this task's checkbox text by editing tasks.md to add one of these three suffixes after this task title: `→ HYPOTHESIS-1-CONFIRMED (filler false positive)`, `→ HYPOTHESIS-2-CONFIRMED (hallucination drop)`, or `→ HYPOTHESIS-3-CONFIRMED (upstream loss)`. The suffix selects which Phase 2 task group runs. → HYPOTHESIS-1-CONFIRMED (filler false positive)
- [x] 2.2 If task 2.1 logs show `JapaneseFillerProcessor` removed a filler matching `その` against a cue whose original text starts with `その経` or `そのけい` (where the next character is content, not a vowel-extension `ー`), confirm hypothesis 1. If `HallucinationFilterStage` dropped a segment whose text equals or starts with `その`, confirm hypothesis 2. If neither stage's log shows `その` at all (i.e., `その` was never present in `transcription_results`), confirm hypothesis 3. Annotate the finding in tasks.md as instructed in 2.1.

## 3. Phase 2 — Fix (run only the group matching the confirmed hypothesis)

### 3a. If HYPOTHESIS-1-CONFIRMED

- [x] 3a.1 Create a `tests/unit/post_processing/test_japanese.py` test that constructs a `Subtitle(text="その経験が今の仕事にも", start_ms=10000, end_ms=15000, index=1)` and runs `JapaneseFillerProcessor` with the CURRENT default config. Assert the test FAILS (i.e., the cue is incorrectly stripped to `経験が今の仕事にも`). This is the regression test that documents the bug.
- [x] 3a.2 Remove the bare `その` entry from `japanese_filler_words` in `src/talking_parrot/config/models.py`'s `PostProcessingConfig` default. Keep `そのー` (with `ー`). Update the `pipeline-config` spec by writing a delta spec that modifies the **PostProcessingConfig dedup and Japanese fields** requirement to drop `その` from the default list (write the delta via `spectra new artifact spec pipeline-config --change investigate-japanese-demonstrative-drop --stdin` only after this branch is selected).
- [x] 3a.3 Update the test from 3a.1 to assert the cue is now PRESERVED. Add a second test that asserts a cue starting with `そのー、こんにちは` (the genuine filler form) is still stripped to `こんにちは`. Both tests MUST pass.
- [x] 3a.4 Update `tests/unit/config/test_models.py` to assert the default `japanese_filler_words` list does NOT contain `その` and DOES contain `そのー`.
- [x] 3a.5 Run the CLI on `test-samples/sample1` again and grep the resulting SRT for `その経験`. Confirm the substring is now present.

### 3b. If HYPOTHESIS-2-CONFIRMED

- [x] 3b.1 From the log captured in 2.1, extract the dropped segment's `avg_logprob`, `no_speech_prob`, `compression_ratio`, `repetition_ratio`, `text`, `start_ms`, `end_ms`, and the rule name that fired.
- [x] 3b.2 Create a regression test in `tests/unit/stages/test_hallucination_filter_stage.py` that constructs a `TranscriptionResult` with the exact metrics and text from 3b.1 and runs `HallucinationFilterStage` with the default config. Assert the test FAILS (segment is dropped).
- [x] 3b.3 Add a min-duration guard to `HallucinationFilterStage` for the rule that fired: if the segment's `(end_ms - start_ms) >= 200` AND the dropping rule is one of `low_logprob_no_speech`, the segment SHALL NOT be dropped on that rule alone. (Adjust the rule name to match whatever 3b.1 reports.) Write a delta spec under `specs/hallucination-filter-stage/spec.md` that adds this guard to the relevant rule requirement.
- [x] 3b.4 Update the test from 3b.2 so the segment is now PRESERVED. Add a second test confirming a clearly-hallucination short segment (e.g., 50ms with very low logprob) IS still dropped.
- [x] 3b.5 Run the CLI on `test-samples/sample1` and grep the SRT for `その経験`. Confirm presence.

### 3c. If HYPOTHESIS-3-CONFIRMED

- [x] 3c.1 Append an entry under `## 品質與工具` in `docs/TODOs.md` reading: "Whisper/VAD drops the demonstrative `その` in `test-samples/sample1` before any post-processing stage sees it. Out of scope for this change; revisit when upgrading Whisper model or tuning VAD." Include the date `2026-05-08`.
- [x] 3c.2 Document the finding (which stage's log first lacks `その`, the chunk_index of the relevant chunk, and the chunk's audio time range) inline in the TODOs.md entry as a one-line summary.

## 4. Phase 1 cleanup (always run)

- [x] 4.1 Verify the DEBUG logs added in 1.1 and 1.2 are still appropriate to keep (they aid future diagnostics; they do not affect runtime when log level is INFO or above). If any is overly verbose at INFO level due to Phase 1 testing changes, downgrade to DEBUG. Do NOT remove the logs — they pay for themselves the next time a similar drop occurs.

## 5. Final verification

- [x] 5.1 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` — all MUST pass with zero errors.
- [x] 5.2 Confirm the success criterion from the proposal: either (a) `test-samples/sample1`'s SRT now contains `その経験`, OR (b) `docs/TODOs.md` contains the documented entry from 3c.1. Exactly one of these MUST hold.
