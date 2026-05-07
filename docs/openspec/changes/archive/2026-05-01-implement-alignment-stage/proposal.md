## Why

Stage 4 of the pipeline (`AlignmentStage`) is the missing link between `TranscriptionStage` (which now produces `TranscriptionResult` per chunk with `aligned_tokens=None`) and downstream `PostProcessingStage`. Without forced alignment, every word in the final subtitle inherits the chunk-level start/end timestamp, which is unusable for word-level subtitle merging or split decisions. ADR-0003 and `docs/architecture/pipeline-module-interfaces.md` already prescribe the design (`AlignmentBackend` interface, language-routed factory, three-state `AlignmentStatus`); we now realise it.

The reference implementation is `whisperx.alignment` from the WhisperX project: torchaudio's `WAV2VEC2_ASR_BASE_960H` bundle for English (word-level) and a HuggingFace `Wav2Vec2ForCTC` model for Japanese (character-level), both driven by a CTC forced-alignment trellis (`get_trellis` / `backtrack` / `merge_repeats`) and `interpolate_nans` for unalignable tokens. We mirror that algorithm, adapted to the project's `AudioReader`/`AlignedToken`/`AlignmentResult` abstractions.

## What Changes

- Introduce a new `alignment/` subpackage with `AlignmentBackend` abstract interface, `EnglishAlignmentBackend` (torchaudio wav2vec2, word-level), `JapaneseAlignmentBackend` (HF wav2vec2 XLSR Japanese, character-level), and `AlignmentBackendFactory` that routes by `(language, GranularityPreference)`.
- Implement the WhisperX-derived CTC forced-alignment kernel as a shared internal helper (`_ctc_align`) used by both backends: log-softmax emissions, `get_trellis`, `backtrack`, `merge_repeats`, plus NaN-aware nearest-neighbour interpolation for unalignable segments.
- Implement `AlignmentStage` constructed with `(factory: AlignmentBackendFactory, audio_reader: AudioReader)`. It resolves a single backend per pipeline run from `(ctx.config.expected_language, ctx.config.align.granularity)`, iterates `ctx.transcription_results`, calls `backend.align(audio_bytes, sample_rate, text)` per chunk, and writes `aligned_tokens` back onto each `TranscriptionResult` while writing `alignment_results`, `alignment_status`, and `alignment_granularity` into the returned `PipelineContext`.
- Implement three-state failure handling: when `align` is disabled returns `alignment_status=DISABLED`; on backend success returns `SUCCESS`; on any backend exception returns `FAILED`, logs `WARNING`, and keeps existing `aligned_tokens` `None`.
- Add a new optional dependency extra `align` to `pyproject.toml` listing `torch`, `torchaudio`, `transformers`, `numpy` so the alignment subsystem only loads when explicitly installed.
- Wire the new `AlignmentStage` into `src/talking_parrot/stages/__init__.py` exports.

## Non-Goals

- Implementing `PostProcessingStage`, `SubtitleProcessor` family, or subtitle export — separate changes per `TODOs.md`.
- Adding alignment backends for languages other than English and Japanese. The factory's registry remains open for future additions but only those two language codes are mapped here.
- Streaming or incremental alignment. Each chunk is aligned in a single forward pass.
- Diarisation, speaker labels, or sentence-level boundary detection.
- GPU device autoselection beyond `"cuda" if torch.cuda.is_available() else "cpu"` — no MPS branch, no quantisation knobs.
- Replacing `AlignedToken.word: str` with a separate `AlignedChar` type. Japanese character entries reuse the same dataclass with single-character `word` strings (each entry is one character).
- Modifying `AlignConfig` schema (it already declares `enabled: bool` and `granularity: str` defaulting to `"AUTO"`). The stage parses the string into `GranularityPreference` at runtime.
- Modifying `AlignmentResult` to carry `granularity`. Granularity lives on `PipelineContext.alignment_granularity` per ADR-0003; the per-chunk `AlignmentResult(chunk_index, tokens)` shape is unchanged.

## Capabilities

### New Capabilities

- `alignment-backend`: Abstract `AlignmentBackend` interface plus the shared CTC forced-alignment kernel that subclasses delegate to.
- `english-alignment-backend`: `EnglishAlignmentBackend` — wraps the torchaudio `WAV2VEC2_ASR_BASE_960H` bundle, `language="en"`, `granularity=AlignmentGranularity.WORD`.
- `japanese-alignment-backend`: `JapaneseAlignmentBackend` — wraps a HuggingFace `Wav2Vec2ForCTC` Japanese model, `language="ja"`, `granularity=AlignmentGranularity.CHARACTER`.
- `alignment-backend-factory`: `AlignmentBackendFactory` — `(language, GranularityPreference) → AlignmentBackend` registry, instance cache, AUTO mode, explicit-pref override, unknown-language error.
- `alignment-stage`: `AlignmentStage` — orchestrates per-chunk alignment, populates `aligned_tokens` on each `TranscriptionResult`, sets `alignment_status` / `alignment_granularity` / `alignment_results` on the returned context, and applies bounded fallback on backend exceptions.

### Modified Capabilities

(none)

## Impact

- Affected specs: `alignment-backend` (new), `english-alignment-backend` (new), `japanese-alignment-backend` (new), `alignment-backend-factory` (new), `alignment-stage` (new)
- Affected code:
  - New: src/talking_parrot/alignment/__init__.py
  - New: src/talking_parrot/alignment/backend.py
  - New: src/talking_parrot/alignment/ctc.py
  - New: src/talking_parrot/alignment/english_backend.py
  - New: src/talking_parrot/alignment/japanese_backend.py
  - New: src/talking_parrot/alignment/factory.py
  - New: src/talking_parrot/stages/alignment_stage.py
  - New: tests/unit/alignment/__init__.py
  - New: tests/unit/alignment/test_backend.py
  - New: tests/unit/alignment/test_ctc.py
  - New: tests/unit/alignment/test_english_backend.py
  - New: tests/unit/alignment/test_japanese_backend.py
  - New: tests/unit/alignment/test_factory.py
  - New: tests/unit/stages/test_alignment_stage.py
  - Modified: src/talking_parrot/stages/__init__.py
  - Modified: pyproject.toml
