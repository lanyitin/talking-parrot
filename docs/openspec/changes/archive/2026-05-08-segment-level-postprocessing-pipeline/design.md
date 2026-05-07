## Context

The talking-parrot pipeline runs: VAD → chunking → transcription → alignment → post-processing → export. `ChunkingStage` greedily concatenates multiple `VadSegment` objects into one `Chunk`, which `TranscriptionStage` feeds to a Whisper backend in a single call. Whisper internally returns multiple segments with per-segment confidence metrics, but the current backends collapse those metrics into chunk-level aggregates (weighted mean for `avg_logprob`/`compression_ratio`, max for `no_speech_prob`, recomputed token-uniqueness for `repetition_ratio`) and emit one `TranscriptionResult` per chunk.

A reference implementation in `audio2subtitle` (peer project) keeps Whisper segments as the unit of work and applies three filters that talking-parrot lacks:

1. **Hallucination filter** — drops segments matching known phrase lists, bracket regex, ≥5 character repeats, or exceeding metric thresholds.
2. **Dedup** — merges consecutive near-identical cues, extending end timestamps to cover the duplicate run.
3. **Japanese cleanup** — filler removal and capped repetition.

Stakeholders: this is a single-developer project; the user has confirmed Japanese as the only target locale and approved breaking the backend contract to expose per-segment metrics.

Constraints worth recording up front:

- `PipelineContext` is frozen; stages return new contexts via `dataclasses.replace`. The `transcription_results` list is the only place segment-grain results live.
- Existing `granularity-aware-processor-factory` builds a per-result token map keyed by 1-based seed `Subtitle.index` (the post-filter position of each `TranscriptionResult`). This must remain stable after the filter shrinks the list.
- `AlignmentStage` currently slices audio with `ctx.chunks[result.chunk_index].start_ms/end_ms`; after the contract change a single `chunk_index` no longer identifies the audio range to align (multiple segments per chunk).
- The project follows TDD (`.spectra.yaml: tdd: true`) and audit (`audit: true`).

## Goals / Non-Goals

**Goals:**

- Expose Whisper-segment-level metrics so hallucination filtering can see them undiluted.
- Insert a hallucination filter between transcription and alignment so downstream stages do not waste compute on filtered segments.
- Add dedup as the first subtitle processor and Japanese cleanup as the last, without breaking the existing `[Merge, Split]` invariants for any granularity path.
- Preserve `granularity-aware-processor-factory`'s WORD-path token map correctness when the seed list is shorter (filter dropped some) or longer (one chunk → many segments) than before.
- Keep audit and TDD discipline: tests written first per task; new third-party integrations not introduced (no new dependencies beyond stdlib `difflib`).

**Non-Goals:**

- Re-architecting VAD or chunking. Chunks remain the unit of Whisper invocation; only the *result granularity* changes.
- Per-segment alignment retries, gap padding, snap-to-silence, or CPS limiting (these are explicitly out of scope per the proposal).
- Multi-language post-processing. English bypasses the Japanese pair.
- Rolling out behind a feature flag. The contract change is breaking and ships in one cut.

## Decisions

### Backend returns `list[TranscriptionResult]` instead of a single result

Each Whisper internal segment becomes one `TranscriptionResult`. `start_ms`/`end_ms` carry the segment's absolute timing (`chunk.start_ms + seg.start * 1000` and similarly for end). `chunk_index` is preserved for traceability and for any downstream debugging that wants to group segments back into chunks.

Alternatives considered and rejected:

- *Keep `TranscriptionResult` chunk-level and add `segments: list[SegmentInfo]` inside it.* Avoids the breaking change but every consumer that wants segment-level granularity (alignment, hallucination filter, post-processing) has to flatten manually. It also forces post-processing to seed multiple subtitles from one result, which contradicts the existing "one result → one seed" rule and complicates the WORD token map.
- *Filter at the chunk level using `no_speech_prob` (max).* Loses precision because `avg_logprob` is the strongest signal and is averaged. Rejected per user decision.

### Hallucination filter runs as its own stage between transcription and alignment

`HallucinationFilterStage` consumes `ctx.transcription_results`, returns a new context with the filtered list. Placement before alignment saves alignment compute on dropped segments. Placement before post-processing means the WORD-path token map (built in factory) sees only kept segments, keeping seed indexes contiguous.

Alternatives considered:

- *Inline the filter inside `TranscriptionStage`.* Couples concerns and makes the filter harder to disable/test independently.
- *Run after alignment.* Wastes alignment work and complicates rebuilding the token map after a mid-pipeline filter pass.

### `AlignmentStage` reads audio per result rather than per chunk

Audio range becomes `[result.start_ms, result.end_ms)`; aligned token offsets shift by `result.start_ms`. This is the only place where the chunk→segment contract change leaks into existing stages.

Alternative considered:

- *Keep reading the whole chunk audio and let CTC alignment localise the text within it.* Works for forced alignment in principle but wastes I/O and CPU and degrades alignment quality for short segments inside long chunks (more silence to walk through).

### Dedup added as the first processor in every granularity path

Running dedup before `[Merge, Split]` means the gap/duration heuristics in merge/split see a deduplicated input and won't decide to merge an already-collapsed run with its neighbours. It also keeps the dedup logic decoupled from granularity. Rule: walk the cue list, group consecutive cues whose pairwise text similarity is ≥ `similarity_threshold` (default 0.9 via `difflib.SequenceMatcher`) AND whose gap is ≤ `max_gap_ms` (default 600 ms); replace each group with a single cue using `start = group[0].start_ms`, `end = group[-1].end_ms`, `text = group[0].text`. Re-number indexes after replacement.

Alternative: putting dedup after merge/split. Rejected because merge can already create a multi-line cue out of two near-duplicates and extracting "is this duplicated?" from the merged text is brittle.

### Japanese processors appended only when `expected_language == "ja"`

The factory inspects `ctx.config.expected_language` and either adds `[JapaneseFillerProcessor, JapaneseRepetitionProcessor]` to the tail or omits them. Order: filler first (removes leading fillers, keeps timing), repetition next (collapses 3+ repeats to 2, with onomatopoeia whitelist). If a cue's text becomes empty after cleanup, the processor drops the cue.

Alternative: a single combined processor. Rejected because filler removal and repetition collapse are independently configurable in `audio2subtitle` and may need to be toggled separately during tuning.

### Repetition ratio is computed per-segment, not per-chunk

Per-segment `repetition_ratio` is `1 - unique_tokens / total_tokens` over the segment's text (whitespace-split). Computing it per-segment keeps the metric meaningful even on short segments — the chunk-level aggregate previously hid per-segment repetitions.

### Cascade condition aggregation moves from backend to stage

The existing cascade behaviour in `TranscriptionStage` evaluates a `condition` (e.g., `metrics.avg_logprob < -1.0`) per chunk to decide whether to retry with the next backend. That contract previously assumed a single chunk-level `TranscriptionResult` with aggregated metrics produced by the backend (weighted-mean / max).

With backends returning per-segment raw metrics, `TranscriptionStage` SHALL compute a chunk-level aggregate locally — using the same legacy rules (duration-weighted mean for `avg_logprob` and `compression_ratio`, max for `no_speech_prob`, `1 - unique/total` over the joined text for `repetition_ratio`) — and expose only that aggregate to the `ConditionEvaluator`. The aggregate is never persisted on any `TranscriptionResult`; it exists solely for cascade decisions. The per-segment results from the *winning* backend are then extended into `transcription_results`.

Net effect: cascade behaviour is preserved exactly; downstream sees segment-grain rows.

Alternative considered: evaluate the condition per segment and fallback only the failing segments. Rejected because (a) it complicates the cascade state machine, (b) consistent within-chunk behaviour matters for the user's tuning intuition, and (c) the hallucination filter already exists downstream to handle individual bad segments.

### No new dependency

`difflib.SequenceMatcher` is sufficient for dedup similarity. The hallucination phrase list and regex patterns are inlined as module constants ported from `audio2subtitle/postprocess/hallucination.py`. The Japanese onomatopoeia whitelist is similarly inlined from `audio2subtitle/postprocess/japanese.py`.

## Risks / Trade-offs

- **[Risk] Backend contract change breaks any external consumer of `TranscriptionBackend`.** → Mitigation: the project is single-tenant; we update both built-in backends and all tests in the same change. Spec delta marks the requirement as MODIFIED so any future backend implementer sees the new return type.
- **[Risk] WORD-path token map keys drift if the filter runs *after* the factory.** → Mitigation: filter runs before `PostProcessingStage`, so the factory builds the token map against the post-filter list. Order is captured in `pipeline-end-to-end-wiring`.
- **[Risk] More `TranscriptionResult` rows mean larger `PipelineContext` and more loop iterations downstream.** → Mitigation: alignment now reads smaller audio windows per call (cheaper); dedup at the head of post-processing collapses redundant rows quickly. Net effect on a typical Japanese speech file is expected to be neutral or slightly positive.
- **[Risk] Hallucination filter false positives drop legitimate segments.** → Mitigation: every check is independently toggleable in `HallucinationFilterConfig` with thresholds copied from the audio2subtitle defaults; filter logs the count dropped per chunk for visibility; tests assert that only borderline cases trigger.
- **[Trade-off] No CPS filter ported.** Acceptable because `[Merge, Split]` already enforces a duration cap and per-segment hallucination filtering removes the dense-text failure mode upstream.
- **[Trade-off] Japanese-only post-processing.** The factory branches on `expected_language` cleanly; adding more languages later is a localised edit to `factory.py`.
