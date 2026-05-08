## Problem

In archived change `2026-05-08-segment-level-postprocessing-pipeline`'s end-to-end verification, the talking-parrot SRT for `test-samples/sample1` drops the demonstrative `その` from the phrase「**その**経験が今の仕事にも役立っていると感じています」. The output cue 13 starts at「経験が」, missing the leading word. The reference SRT (audio2subtitle output) does include `その`, and the ground-truth script at `/Users/lanyitin/Projects/personel/audio2subtitle/test-audio/sample1/sample1.txt` confirms it is spoken.

This is the only word-level drop observed across the entire 3-minute sample, so the failure is rare but real.

## Root Cause

Unknown. Three hypotheses, none yet confirmed:

1. **Filler-list false positive.** `JapaneseFillerProcessor`'s default `japanese_filler_words` list includes `そのー` AND `その`. If a cue happens to begin with the demonstrative `その` (genuine content, not a filler), the processor strips it. The Whisper transcription `そのー` filler form and the demonstrative `その` are spelled identically as a 2-character prefix, so this is the most plausible cause.
2. **Hallucination-filter drop.** A short low-confidence segment containing only `その` could be removed by `HallucinationFilterStage` if its `avg_logprob` is below the threshold and `no_speech_prob` is above. This is testable from the run logs.
3. **Whisper segment-boundary loss.** The word straddles a chunk boundary and is lost in either VAD or Whisper, before any post-processing sees it.

The diagnostic phase of this change SHALL identify which hypothesis is correct before any code change.

## Proposed Solution

Two phases:

**Phase 1 — Diagnose.** Add temporary structured logging to instrument the relevant pipeline points, re-run the sample, and read the logs to determine which stage drops `その`. Specifically, log every `HallucinationFilterStage` drop with text + chunk_index + reason, and every `JapaneseFillerProcessor` filler removal with the original cue text + matched filler + cue index. The current `HallucinationFilterStage` already emits per-drop DEBUG logs and an INFO summary; the per-drop log MUST include the dropped text. The current `JapaneseFillerProcessor` does NOT log per-removal — Phase 1 adds a DEBUG log entry per removal that includes the original text and the matched filler token.

**Phase 2 — Fix the confirmed cause.** Branch by finding:

- **If hypothesis 1 (filler false positive)**: Remove `その` from the default `japanese_filler_words` list. Rationale: `そのー` (with prolonged vowel mark) is the unambiguous filler form; bare `その` collides with the demonstrative pronoun and is a content word more often than a filler. Add a regression test: a cue starting with `その経験` is preserved.
- **If hypothesis 2 (hallucination drop)**: Investigate which rule fired and either tighten the threshold or carve out a min-text-length guard (e.g., do not drop cues whose duration is `>= 200ms` solely on `low_logprob_match`). Add a regression test that mirrors the dropped-segment metrics.
- **If hypothesis 3 (Whisper/VAD loss)**: Document the limitation in `docs/TODOs.md` as a known issue and close this change without code modification, since fixing upstream Whisper transcription is out of scope.

The proposal commits to running Phase 1 instrumentation; the Phase 2 fix is conditional on Phase 1 findings. This is documented in tasks.md.

## Non-Goals

- Generic Japanese accuracy improvements unrelated to the `その` drop.
- Tuning filler removal for other tokens (`あの`, `えっと`, etc.) — those have shown no false-positive evidence in this sample.
- Changing the alignment backend, Whisper model, or VAD configuration.
- Investigating other drops in other samples; this change is scoped to the one observed regression.

## Success Criteria

1. The pipeline log for `test-samples/sample1` clearly identifies which stage drops `その` (one of: `hallucination_filter`, `japanese_filler`, `transcription`/upstream).
2. After the conditional fix in Phase 2 (if applicable), the resulting SRT for `test-samples/sample1` contains the substring `その経験` (i.e., the drop is repaired). If the cause is upstream of post-processing (hypothesis 3), the success criterion is instead a documented entry in `docs/TODOs.md`.
3. A regression test (added in Phase 2 if the fix is in code) reproduces the original drop on the unfixed code path and passes on the fixed path.
4. Hypothesis 1 fix MUST NOT increase filler-removal coverage loss elsewhere — i.e., genuine `そのー` filler removal continues to work, verified by an existing or new test.

## Impact

- Affected code:
  - Modified:
    - `src/talking_parrot/post_processing/japanese.py` (Phase 1: add per-removal DEBUG log; Phase 2 hypothesis 1: default filler list)
    - `src/talking_parrot/config/models.py` (Phase 2 hypothesis 1: update `japanese_filler_words` default)
    - `src/talking_parrot/stages/hallucination_filter_stage.py` (Phase 1: ensure dropped text is in the per-drop log; conditional Phase 2 hypothesis 2)
    - `tests/unit/post_processing/test_japanese.py` (regression test if hypothesis 1 confirmed)
    - `tests/unit/stages/test_hallucination_filter_stage.py` (regression test if hypothesis 2 confirmed)
    - `tests/unit/config/test_models.py` (default-list assertion if hypothesis 1 confirmed)
    - `docs/TODOs.md` (entry if hypothesis 3 confirmed)
  - New: (none)
  - Removed: (none)
- Affected specs:
  - Modified: `japanese-postprocessors`, `pipeline-config` (only if hypothesis 1 confirmed); `hallucination-filter-stage` (only if hypothesis 2 confirmed). The proposal commits to making the appropriate spec delta during Phase 2; specs are NOT modified during Phase 1.
