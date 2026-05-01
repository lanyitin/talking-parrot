## Context

Stage 4 of the pipeline is `AlignmentStage`. It receives `ctx.transcription_results: list[TranscriptionResult]` (each with `aligned_tokens=None`) and `ctx.chunks: list[Chunk]`, and must produce per-chunk `AlignmentResult` plus populate `aligned_tokens` on each `TranscriptionResult` so that `PostProcessingStage` (next change) has word- or character-level timestamps to merge / split / re-time on.

Existing foundation:
- `models/transcription.py` defines frozen `AlignedToken(word: str, start_ms: int, end_ms: int, score: float)` and `TranscriptionResult(... aligned_tokens: list[AlignedToken] | None = None)`.
- `models/context.py` defines `AlignmentStatus(DISABLED|SUCCESS|FAILED)`, `AlignmentGranularity(WORD|CHARACTER)`, `GranularityPreference(WORD|CHARACTER|AUTO)`, and `AlignmentResult(chunk_index: int, tokens: list)`.
- `config/models.py` defines `AlignConfig(enabled: bool = True, granularity: str = "AUTO")`.
- `io/audio_reader.py` defines `AudioReader` ABC with `sample_rate: int` and `read(start_ms, end_ms) -> bytes` (16-bit PCM, 16 kHz mono).
- `docs/architecture/ADR-0003-對齊粒度與後處理策略.md` and `docs/architecture/pipeline-module-interfaces.md` already prescribe the design (factory pattern, three-state status, granularity declared by backend, granularity stored on `PipelineContext`).
- `whisperx.alignment` (m-bain/whisperX) is the reference algorithm. Its `align()`, `load_align_model()`, `get_trellis()`, `backtrack()`, `merge_repeats()`, and `interpolate_nans()` are mirrored here, simplified for the project's per-chunk model.

Optional dependencies are not yet installed: `torch`, `torchaudio`, `transformers`, `numpy`. They are added under a new `align` extra in `pyproject.toml` — the alignment subpackage lazy-imports them so a user without the extra can still construct the `Pipeline` and run with `align.enabled=False`.

## Goals / Non-Goals

**Goals:**
- Define `AlignmentBackend` ABC with read-only `language: str`, `granularity: AlignmentGranularity`, and `align(audio_data: bytes, sample_rate: int, transcript: str) -> AlignmentResult`.
- Implement the WhisperX CTC kernel as `alignment/ctc.py` once; share it between English and Japanese backends.
- Implement `EnglishAlignmentBackend` (torchaudio `WAV2VEC2_ASR_BASE_960H`, word tokenisation on `"|"` separator) and `JapaneseAlignmentBackend` (HuggingFace `jonatasgrosman/wav2vec2-large-xlsr-53-japanese`, character tokenisation, no space splitting).
- Implement `AlignmentBackendFactory` with a `(language, granularity) → backend_class` registry, AUTO routing, explicit-pref override, instance cache.
- Implement `AlignmentStage` with three-state `AlignmentStatus`, lazy chunk-window audio reads via injected `AudioReader`, and bounded per-chunk fallback on exceptions.

**Non-Goals:**
- Other languages, MPS device support, streaming alignment, diarisation, GPU memory tuning, model download progress UX, schema changes to `AlignConfig`, schema changes to `AlignmentResult`, replacing `AlignedToken.word` with a typed character variant.

## Decisions

### Backend interface mirrors pipeline-module-interfaces

`AlignmentBackend` is an `abc.ABC` declaring:
- `language: str` — abstract read-only property; concrete backends return `"en"`, `"ja"`, etc.
- `granularity: AlignmentGranularity` — abstract read-only property; concrete backends return `AlignmentGranularity.WORD` or `AlignmentGranularity.CHARACTER`.
- `align(audio_data: bytes, sample_rate: int, transcript: str) -> AlignmentResult` — abstract. Models load lazily on first call.

The returned `AlignmentResult.chunk_index` is set by `AlignmentStage` (the backend does not know its chunk index); backends may return `chunk_index=-1` and the stage rewrites it. To keep the contract clean, the backend instead returns `list[AlignedToken]` and the stage assembles the `AlignmentResult`. This avoids the awkward sentinel.

Final backend signature: `align(audio_data: bytes, sample_rate: int, transcript: str) -> list[AlignedToken]`. The pipeline-module-interfaces document is updated implicitly (this change clarifies the contract). The stage wraps the list into `AlignmentResult(chunk_index=result.chunk_index, tokens=tokens)`.

**Alternatives considered:**
- Threading `chunk_index` through the backend: rejected. The backend is language-bound, not pipeline-bound; introducing a chunk concept inside the backend bleeds responsibilities.

### Shared CTC kernel in alignment/ctc.py

Both backends share an internal kernel `ctc_align(emissions: torch.Tensor, dictionary: dict[str, int], transcript_tokens: list[str], blank_id: int, frame_rate_hz: float, *, segment_offset_ms: int) -> list[AlignedToken]`. The kernel:
1. Maps each token in `transcript_tokens` to its dictionary index, falling back to a wildcard column whose probability per frame is `max(emissions[t, non_blank])` (mirrors whisperX's `<unk>` / `*` handling).
2. Builds the trellis `T[t, j] = max(T[t-1, j] + emissions[t-1, blank], T[t-1, j-1] + emissions[t-1, tokens[j-1]])` with `T[0, 0] = 0` and `T[0, j>0] = -inf`.
3. Backtracks the optimal path producing `Point(token_index, time_index, score)` in chronological order.
4. `merge_repeats(path, transcript_tokens)` collapses runs of identical token indices into `Segment(label, start_frame, end_frame, score)`.
5. Converts each `Segment` to `AlignedToken(word=label, start_ms=segment_offset_ms + start_frame * 1000 / frame_rate_hz, end_ms=segment_offset_ms + end_frame * 1000 / frame_rate_hz, score=score)`.

Tokens whose dictionary lookup fails AND whose wildcard score is below a sentinel threshold get `start_ms=NaN, end_ms=NaN` placeholder tokens; a final pass `interpolate_nans(tokens)` fills NaN start/end values via nearest-neighbour from the surrounding non-NaN tokens, mirroring whisperX. If all tokens are NaN, the kernel sets every `start_ms`/`end_ms` to the segment span endpoints (degenerate fallback) and `score=0.0`.

`segment_offset_ms` allows the backend to call the kernel with a chunk-window emissions tensor and receive absolute timestamps.

**Alternatives considered:**
- Re-implementing the trellis in each backend: rejected — duplication invites drift between English and Japanese paths.
- Using `torchaudio.functional.forced_align`: rejected — the API is newer and not present in older torchaudio versions; mirroring whisperX's manual implementation keeps version requirements loose and matches the user's reference.

### Audio decoding inside backends, not in the kernel

`AlignmentBackend.align()` accepts `audio_data: bytes` (16-bit signed little-endian PCM at the given `sample_rate`). The backend is responsible for converting bytes → `torch.Tensor` of float32 `[1, num_samples]` normalised to `[-1, 1]` via `int16 / 32768.0`. The kernel works in tensor-space.

If the segment is shorter than 400 samples the backend zero-pads to 400 (whisperX threshold) before forward pass.

### EnglishAlignmentBackend uses torchaudio bundle

`EnglishAlignmentBackend` lazy-imports `torch` and `torchaudio` on first `align()` call. Raises `ImportError("Install with: uv add 'talking-parrot[align]'")` on `ModuleNotFoundError`.

It instantiates `bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H` once, calls `bundle.get_model().to(device)` and `bundle.get_labels()`. Device is `"cuda"` if `torch.cuda.is_available()` else `"cpu"`. The model and `labels` are cached on the instance.

The dictionary is `{label.lower(): idx for idx, label in enumerate(labels)}`. The blank id is `0` (torchaudio convention; verified by checking `labels[0] == "-"` or by overriding when `[pad]` / `<pad>` exists). The space token is `"|"`.

For an English transcript, the backend:
1. Lowercases the transcript and replaces `" "` with `"|"`.
2. Tokenises into characters; the resulting `transcript_tokens: list[str]` is the per-character sequence.
3. Forward-passes audio: `emissions, _ = model(audio_tensor)`. Applies `torch.log_softmax(emissions, dim=-1)`.
4. Calls `ctc_align(...)` to get character-level `AlignedToken`s.
5. Groups consecutive non-`"|"` characters back into words: each word's `start_ms` = first char's `start_ms`, `end_ms` = last char's `end_ms`, `score` = mean of char scores. Words separated by `"|"` segments are flushed.

The frame rate of `WAV2VEC2_ASR_BASE_960H` emissions is `sample_rate / 320 = 50 Hz` (its stride), so `frame_rate_hz = 50.0` is hard-coded and verified by an integration test.

### JapaneseAlignmentBackend uses HuggingFace XLSR

`JapaneseAlignmentBackend` lazy-imports `torch` and `transformers` on first `align()` call. Raises `ImportError("Install with: uv add 'talking-parrot[align]'")` on `ModuleNotFoundError`.

It loads `Wav2Vec2Processor.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-japanese")` and `Wav2Vec2ForCTC.from_pretrained(...)`. Device selection mirrors English. The dictionary is `processor.tokenizer.get_vocab()` keyed by lower-cased character, blank id is `processor.tokenizer.pad_token_id`. There is no `"|"` space token; whitespace in the transcript is stripped before tokenisation.

For a Japanese transcript:
1. Strips ASCII whitespace from the transcript.
2. Tokenises into characters: `transcript_tokens = list(stripped_transcript)`.
3. Forward-passes via `model(input_values=processor(...).input_values).logits`.
4. Applies `torch.log_softmax`.
5. Calls `ctc_align(...)` to get per-character `AlignedToken`s — these are returned directly, one per Japanese character (granularity=CHARACTER).

Frame rate for XLSR is also `50 Hz` (same convolutional stride). This is asserted with a test.

### AlignmentBackendFactory routes by (language, granularity)

`AlignmentBackendFactory` exposes `create(language: str, granularity_pref: GranularityPreference = GranularityPreference.AUTO) -> AlignmentBackend`.

Internal registry is a 2-D dict keyed by `(language, AlignmentGranularity)`:
```
{
  ("en", AlignmentGranularity.WORD):      EnglishAlignmentBackend,
  ("ja", AlignmentGranularity.CHARACTER): JapaneseAlignmentBackend,
}
```

Routing rules:
- `granularity_pref == AUTO`: look up the language's *default* backend. The default is the only entry for that language in the registry. If the language has multiple entries, pick the one matching the language's natural granularity (declared in a parallel `_DEFAULTS = {"en": WORD, "ja": CHARACTER}` dict).
- `granularity_pref == WORD`: look up `(language, WORD)`. If absent, raise `ValueError("No WORD-granularity alignment backend for language: <lang>")`.
- `granularity_pref == CHARACTER`: look up `(language, CHARACTER)`. If absent, raise the analogous error.
- Unknown `language`: raise `ValueError(f"No alignment backend for language: {language}")`.

The factory caches instances by `(language, AlignmentGranularity)` so repeated `create()` calls return the same `AlignmentBackend`.

**Alternatives considered:**
- Auto-detecting the language from the transcript: rejected. The transcription stage already resolves a language per chunk; using `ctx.config.expected_language` keeps the alignment stage deterministic and fast.

### AlignmentStage iterates per chunk with bounded fallback

`AlignmentStage(factory: AlignmentBackendFactory, audio_reader: AudioReader)`:

Disabled path (`ctx.config.align is None or ctx.config.align.enabled is False`):
- Return `dataclasses.replace(ctx, alignment_status=AlignmentStatus.DISABLED, alignment_granularity=None, alignment_results=[])` (logs DEBUG once).
- Each `TranscriptionResult.aligned_tokens` stays `None`.

Enabled path:
1. Parse `granularity_pref = GranularityPreference(ctx.config.align.granularity.upper())`.
2. Resolve `backend = factory.create(ctx.config.expected_language, granularity_pref)`.
   - On `ValueError` from the factory: log WARNING and return `alignment_status=AlignmentStatus.FAILED, alignment_granularity=None, alignment_results=[]`. Each `TranscriptionResult.aligned_tokens` stays `None`.
3. For each `result in ctx.transcription_results` (in input order):
   a. Look up the chunk: `chunk = ctx.chunks[result.chunk_index]` (assumes `chunk.index == result.chunk_index`).
   b. Read audio: `audio_bytes = audio_reader.read(chunk.start_ms, chunk.end_ms)`.
   c. Try `tokens = backend.align(audio_bytes, audio_reader.sample_rate, result.text)`.
   d. On exception: log WARNING `("alignment failed for chunk %d: %s", result.chunk_index, exc_type)`, mark this chunk's tokens as `[]` (empty list), continue with next chunk. Do NOT abort the run. The whole-run status remains `SUCCESS` if at least one chunk aligned successfully and `FAILED` if none did.
   e. On success: shift token timestamps from chunk-relative to absolute by adding `chunk.start_ms` to each token's `start_ms` and `end_ms`. *(Note: backends already return absolute timestamps when the kernel is given `segment_offset_ms=chunk.start_ms`. The stage passes `chunk.start_ms` as the segment offset by reading absolute audio. To keep the contract simple, the backend receives only chunk-relative audio bytes and returns chunk-relative timestamps; the stage shifts. This isolates the backend from chunk concepts — see "Backend interface mirrors pipeline-module-interfaces".)*
4. Build the new `TranscriptionResult` list via `dataclasses.replace(result, aligned_tokens=tokens)` for each result.
5. Build `alignment_results = [AlignmentResult(chunk_index=result.chunk_index, tokens=tokens) for ...]`.
6. Determine `final_status`:
   - `SUCCESS` if at least one chunk produced a non-empty token list.
   - `FAILED` if every chunk produced an empty token list (or `ctx.transcription_results` was empty AND the user enabled alignment — reasonable edge to flag).
7. Return `dataclasses.replace(ctx, transcription_results=new_results, alignment_results=alignment_results, alignment_status=final_status, alignment_granularity=backend.granularity)`.

### Whitespace handling in the audio reader path

`AudioReader.read` returns 16-bit PCM bytes. Backends decode to float32 `[1, N]` tensors via numpy: `np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0`. This matches whisperX's normalisation. No resampling — the chunking and IO contract guarantees 16 kHz mono.

## Risks / Trade-offs

- [Risk] The `align` extra requires PyTorch (~700 MB CPU wheel, larger with CUDA). → Mitigation: optional extra; users can opt out with `align.enabled=False`. ImportError messages explicitly name the extra.
- [Risk] `WAV2VEC2_ASR_BASE_960H` is English-only and word-trained on LibriSpeech (read speech). Domain mismatch (e.g. accented spontaneous speech) degrades alignment quality. → Mitigation: documented limitation; users may add their own backend in a future change. The factory registry is open for extension.
- [Risk] The Japanese model is a large XLSR (~1.2 GB) and slow on CPU. → Mitigation: device auto-select to CUDA when available; documented in user-facing notes (out of scope here).
- [Risk] CTC trellis on long chunks (e.g. 30 s) is O(T·N) memory where T=1500 frames at 50 Hz and N=transcript length. For dense Japanese characters this can spike RAM. → Mitigation: chunking already caps `max_chunk_seconds` upstream (default 30 s). No additional split inside alignment.
- [Risk] `interpolate_nans` produces non-monotonic timestamps when many adjacent tokens fail. → Mitigation: after interpolation the stage re-checks monotonicity and clamps any out-of-order `end_ms` to `>= start_ms` of the same token and `<= start_ms` of the next; this matches whisperX behaviour at the edges.
- [Risk] Mismatch between `chunk.index` and `result.chunk_index` (e.g. chunks were filtered upstream). → Mitigation: stage does direct indexing `ctx.chunks[result.chunk_index]` and lets `IndexError` propagate as a hard failure (chunk-index integrity is `ChunkingStage`'s contract; alignment trusts it).
