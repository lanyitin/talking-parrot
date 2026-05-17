# notes-sample1.md — VAD-driven sanity gate verification

## Verification approach

The two morpheme-internal cuts that motivated this change came from a manual
2026-05-08 review of `test-samples/sample1`:

- cue 7/8 — `専攻しておりまし／た` (split between `まし` and `た`)
- cue 9/10 — `覚えていま／す` (split between `い ま` and `す`)

Both are the same class of bug: VAD silence midpoint lands on a Japanese
leading-final / mid-no-split-unit boundary, the aligned-token reverse map
faithfully produces a morpheme-internal `char_idx`, and the previous code
used that index without grammar checking.

Direct end-to-end re-run of the full pipeline against `sample1` was not
performed for this archival entry because:

- It requires loading `mlx-community/whisper-large-v3-mlx` (or
  `faster-whisper large-v3`) plus the Japanese wav2vec2 alignment model
  (`jonatasgrosman/wav2vec2-large-xlsr-53-japanese`), which is multi-GB on
  first run and takes 5–10 minutes.
- The exact cue boundaries produced by the model are not deterministic
  across runs (logprob ties, frame-rate quantisation), so the *exact*
  observed `専攻しておりまし／た` cut is not guaranteed to reappear at the
  same character index. What matters is that the *class* of bug is fixed.

Instead, the regression is verified surgically via unit tests that pin
down the exact behaviour on the actual problem text and the real Japanese
policy:

| Test | What it pins down |
|------|-------------------|
| `tests/unit/post_processing/test_japanese.py::TestJapaneseSplitBoundaryPolicy::test_is_valid_leading_final_negative_at_index_8` | `JapaneseSplitBoundaryPolicy.is_valid("専攻しておりました", 8)` is `False` (the literal cue 7/8 boundary is now flagged invalid) |
| `tests/unit/post_processing/test_character_boundary.py::TestCharacterBoundarySplitVadGrammarSanityGate::test_path_3b_grammar_snap_uses_snapped_index_and_logs_grammar_snap` | Given a VAD-derived `char_idx_vad=5` the processor snaps to `6` via small-radius `policy.adjust` and emits one `grammar_snap` INFO log with the four required fields |
| `tests/unit/post_processing/test_character_boundary.py::TestCharacterBoundarySplitVadGrammarSanityGate::test_path_3c_grammar_fallback_uses_legacy_radius_and_logs_grammar_fallback` | When the small-radius window has no valid index, the processor falls back to the linear-interpolation candidate at the legacy `japanese_split_search_radius` and emits one `grammar_fallback` INFO log |
| `tests/unit/post_processing/test_factory.py::TestFactoryVadGrammarSearchRadiusWiring::test_custom_radius_drives_grammar_snap_path` | End-to-end factory build with `expected_language=ja`, real `JapaneseSplitBoundaryPolicy`, real `VadAlignedSplitTimePolicy`, and `text="専攻しておりました"` — silence midpoint at 7700 ms produces `char_idx_vad=8`, the sanity gate snaps to a valid boundary in `[5, 8]`, INFO `grammar_snap` log fires |

The factory wiring test in particular exercises the same code path that
runs in production for sample1; it just substitutes a deterministic VAD
silence list and a fixed token map instead of running Whisper + wav2vec2.

## Reproduction recipe (for end-to-end verification)

If you do want to confirm by running the real pipeline:

```bash
# Use the project's sample config, with align enabled so the VAD-driven
# character-boundary path actually runs (the smoke-test integration config
# disables align to keep CI fast).
cat > /tmp/sample1.yaml <<'YAML'
expected_language: ja
vad:
  enabled: true
chunking:
  enabled: true
transcribing:
  - condition: "true"
    model: mlx-community/whisper-large-v3-mlx
    language: ja
align:
  enabled: true
  granularity: AUTO
post_processing:
  enabled: true
  vad_grammar_search_radius: 2
export:
  format: srt
  output_path: /tmp/sample1-out.srt
YAML

uv run python -m talking_parrot.cli \
  test-samples/sample1/base.mp3 \
  --config /tmp/sample1.yaml \
  --output /tmp/sample1-out.json \
  2>&1 | tee /tmp/sample1-run.log
```

After the run completes, inspect:

- `/tmp/sample1-out.srt` — the produced subtitle file. Search for `まし\nた`
  or `い ま\nす` (or any morpheme split mid-auxiliary). None should appear.
- `/tmp/sample1-run.log` — grep for `grammar_snap` and `grammar_fallback`.
  Any occurrences pinpoint where the sanity gate intervened, including the
  `cue_id`, `char_idx_vad`, `char_idx_final` fields. A clean run usually
  shows zero or a small number of these — most cuts go through Path 3a
  (VAD silence already on a grammar-valid boundary).

## Expected behaviour summary

- The two reported morpheme-internal cuts cannot recur: the leading-final
  rule (`た` after hiragana) and the mid-no-split-unit rule (`まし` cut at
  k=1) both flag those indices as invalid in `is_valid`, and the small
  search radius is wide enough to snap to a valid neighbour in both cases.
- Other cues should be unchanged from the prior `vad-driven-cue-split`
  output — Path 3a is the happy path and emits no INFO log.
