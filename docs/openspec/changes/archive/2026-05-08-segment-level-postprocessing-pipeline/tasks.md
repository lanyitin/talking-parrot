## 1. Config models & validation

- [x] 1.1 Add `HallucinationFilterConfig` pydantic model to `src/talking_parrot/config/models.py` with fields per the **HallucinationFilterConfig schema** requirement (enabled, four numeric thresholds, phrase list, six per-rule toggles); register it on `PipelineConfig` as `hallucination_filter: HallucinationFilterConfig | None = None`. Write the failing pydantic-roundtrip test in `tests/unit/config/test_models.py` first.
- [x] 1.2 [P] Extend `PostProcessingConfig` in `src/talking_parrot/config/models.py` with the new fields described in the **PostProcessingConfig dedup and Japanese fields** requirement (dedup_enabled, similarity threshold, max_gap_ms, japanese toggles, filler list, onomatopoeia whitelist), including pydantic validators that reject out-of-range similarity / negative gap. Write the failing validator tests first.
- [x] 1.3 [P] Update `src/talking_parrot/config/loader.py` (or equivalent) to surface unknown-field rejection covering the new sub-section, mirroring the existing `ConfigLoader rejects unknown fields` behaviour.

## 2. Transcription backend contract — segment-level results

- [x] 2.1 Update the abstract `TranscriptionBackend` in `src/talking_parrot/transcription/backend.py` to declare `transcribe(...) -> list[TranscriptionResult]` per the **TranscriptionBackend interface defines the contract for all transcription backends** requirement; write a failing abstract-contract test in `tests/unit/transcription/test_backend.py` first.
- [x] 2.2 Update the **TranscriptionResult populated by backend** contract enforcement: tighten or add tests asserting per-segment `start_ms`/`end_ms` and the empty-list permitted scenario.
- [x] 2.3 Update the **TranscriptionMetrics contract for cascade conditions** rules in spec compliance: backends now emit raw per-segment metrics; remove backend-side aggregation. Write failing tests in `tests/unit/transcription/test_backend.py` covering "Per-segment values not averaged" and the segment-level repetition-ratio scenario referenced by the design decision **Repetition ratio is computed per-segment, not per-chunk**.
- [x] 2.4 Refactor `src/talking_parrot/transcription/faster_whisper_backend.py` to satisfy **FasterWhisperBackend assembles TranscriptionResult per the backend contract**: emit one `TranscriptionResult` per yielded segment, drop chunk-level `_compute_metrics` aggregation, set `start_ms`/`end_ms` from segment timestamps. Update `tests/unit/transcription/test_faster_whisper_backend.py` first (multi-segment fixture + empty-iterator scenario).
- [x] 2.5 [P] Refactor `src/talking_parrot/transcription/mlx_whisper_backend.py` to satisfy **MLXWhisperBackend assembles TranscriptionResult per the backend contract**: same per-segment assembly. Update `tests/unit/transcription/test_mlx_whisper_backend.py` first.
- [x] 2.6 Implement the design decision **Backend returns `list[TranscriptionResult]` instead of a single result**: ensure both backends and any backend factory tests have been migrated; remove the now-unused `_compute_metrics` helpers if they are not referenced elsewhere.

## 3. Transcription stage — extend list & cascade aggregate

- [x] 3.1 Modify `src/talking_parrot/stages/transcription_stage.py` to extend (not append) per-chunk segment results into `ctx.transcription_results`, satisfying **TranscriptionStage produces one TranscriptionResult per Chunk** (renamed semantics) and the multi-result-per-chunk scenarios. TDD: update `tests/unit/stages/test_transcription_stage.py` to assert chunk-index ordering across multiple segments per chunk, then implement.
- [x] 3.2 Implement the local cascade aggregator inside `TranscriptionStage` per the design decision **Cascade condition aggregation moves from backend to stage** and the modified **TranscriptionStage drives a cascade across transcribing[] steps** requirement (duration-weighted mean / max / unique-token aggregate; never persisted). Add cascade-table-with-multi-segment tests; cover empty-result-list aggregate (all zeros).
- [x] 3.3 Verify **TranscriptionStage exposes only TranscriptionMetrics fields to ConditionEvaluator** still holds against the new aggregate (variables dict has exactly four keys); add a regression test if missing.
- [x] 3.4 Update the data-model invariants captured in **TranscriptionResult exposes metrics for condition evaluation** (segment bounds within parent chunk, ascending non-overlapping order); add an integration-style test in `tests/unit/models/test_transcription.py` or `tests/unit/stages/test_transcription_stage.py` asserting these invariants on stage output.

## 4. Hallucination filter stage

- [x] 4.1 Create `src/talking_parrot/stages/hallucination_filter_stage.py` implementing **HallucinationFilterStage exists as a pipeline stage** (constructor takes `HallucinationFilterConfig`, `name == "hallucination_filter"`, returns new context). Write the constructor/name test in `tests/unit/stages/test_hallucination_filter_stage.py` first.
- [x] 4.2 Implement the six rules (phrase, bracket, repeat, low-logprob+no-speech, compression, repetition) per **HallucinationFilterStage filters TranscriptionResult entries by configured rules**, each independently toggleable. Add the threshold decision-table cases as parametrised tests; cover "Disabled stage returns input unchanged" and "Order preserved across drops".
- [x] 4.3 Add the INFO summary log and DEBUG per-drop entries per **HallucinationFilterStage logs filter activity**; assert log fields with `structlog`'s testing utilities.
- [x] 4.4 Implement the design decision **Hallucination filter runs as its own stage between transcription and alignment**: confirm via a test that the stage modifies only `transcription_results` and leaves other context fields untouched (frozen-context contract).

## 5. Alignment stage — read audio per result

- [x] 5.1 Update `src/talking_parrot/stages/alignment_stage.py` to satisfy the modified **AlignmentStage aligns each chunk and shifts timestamps to absolute** requirement and the design decision **`AlignmentStage` reads audio per result rather than per chunk**: read `(result.start_ms, result.end_ms)`, shift tokens by `result.start_ms`. TDD: update `tests/unit/stages/test_alignment_stage.py` first to assert audio_reader called with per-segment bounds and tokens shifted by `result.start_ms`, including "Multiple segments from one chunk aligned independently".

## 6. Post-processing — Dedup

- [x] 6.1 Create `src/talking_parrot/post_processing/dedup.py` implementing the **DedupSubtitleProcessor merges runs of near-duplicate consecutive cues** requirement using `difflib.SequenceMatcher`; renumber post-merge per the design decision **Dedup added as the first processor in every granularity path**. TDD: write the four scenarios from the spec plus the similarity/gap decision-table examples in `tests/unit/post_processing/test_dedup.py` first.

## 7. Post-processing — Japanese

- [x] 7.1 [P] Create `JapaneseFillerProcessor` in `src/talking_parrot/post_processing/japanese.py` implementing **JapaneseFillerProcessor strips leading filler words** (timing preserved, drop empty cues, renumber). TDD in `tests/unit/post_processing/test_japanese.py` first.
- [x] 7.2 [P] Add `JapaneseRepetitionProcessor` to the same module implementing **JapaneseRepetitionProcessor caps consecutive character repetitions at two** with onomatopoeia whitelist; cover the repetition decision-table examples.
- [x] 7.3 Confirm both processors honour the design decision **Japanese processors appended only when `expected_language == "ja"`** at the factory level (covered by the factory tests in §8 but explicitly cross-reference here).

## 8. Factory wiring

- [x] 8.1 Update `DefaultGranularityAwareProcessorFactory.create()` in `src/talking_parrot/post_processing/factory.py` to satisfy the modified **Factory returns word-boundary group for WORD granularity**, **Factory returns character-boundary group for CHARACTER granularity**, and **Factory returns time-based group for None** requirements: prepend `DedupSubtitleProcessor`, conditionally append the two Japanese processors based on `ctx.config.expected_language`. TDD: extend `tests/unit/post_processing/test_factory.py` first to cover all six order/inclusion scenarios.

## 9. CLI wiring & end-to-end

- [x] 9.1 Update `src/talking_parrot/cli.py` to satisfy the modified **cli.py builds the full five-stage pipeline** requirement: insert `HallucinationFilterStage` between `TranscriptionStage` and `AlignmentStage` (or before `PostProcessingStage` when align is None), gated by `cfg.hallucination_filter is not None`. Update `tests/unit/cli/test_cli_wiring.py` for the new ordering scenarios.
- [x] 9.2 Run the integration smoke test (`tests/integration/test_pipeline_smoke.py`); add a fixture variant exercising all six stages end-to-end on a tiny synthetic audio fixture to guard the pipeline-end-to-end-wiring contract.

## 10. Final verification

- [x] 10.1 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` — all MUST pass with zero errors before marking the change ready for archive.
- [x] 10.2 Run `/spectra-audit` over the diff to confirm no security or data-handling regressions (no new third-party deps; honour the design decision **No new dependency**).
- [x] 10.3 Manual eyeball: run the CLI on a real Japanese audio fixture; inspect the hallucination-filter log (count dropped) and dedup log (count merged); diff the resulting SRT against the audio2subtitle baseline to confirm cue boundaries are aligning.
