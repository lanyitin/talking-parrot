## Context

Stages 1–4 of the pipeline already exist and are exercised end-to-end up to `AlignmentStage`. `PipelineContext` carries `transcription_results: list[TranscriptionResult]` (each with optional `aligned_tokens: list[AlignedToken]`), `alignment_status: AlignmentStatus`, and `alignment_granularity: AlignmentGranularity | None`. Stage 5's job is to turn those structures into `subtitles: list[Subtitle]`.

ADR-0003 (對齊粒度與後處理策略) has already pinned the high-level strategy: a `GranularityAwareProcessorFactory` selects one of three ordered processor pairs (WORD / CHARACTER / fallback). What it does NOT pin is (a) how `TranscriptionResult` should be converted into the initial `Subtitle` sequence, (b) the exact merge/split algorithms each processor uses, and (c) how `PostProcessingConfig` should be extended to carry the thresholds the processors need. This document fills those gaps so implementers do not have to reverse-engineer them.

The current `PostProcessingConfig` (`enabled`, `max_line_length`, `max_lines_per_subtitle`) is missing the threshold fields described in `pipeline-data-models.md` (`merge_gap_threshold_ms`, `merge_max_duration_ms`, `split_max_duration_ms`). The architecture document is correct; the dataclass is incomplete. This change closes that gap by making the additions on the `PostProcessingConfig` model.

## Goals / Non-Goals

**Goals:**

- Define a single `SubtitleProcessor` interface that all six processors implement identically, so the Stage can apply them uniformly via a `for processor in factory.create(g): subs = processor.process(subs, cfg)` loop.
- Define the seed `Subtitle` sequence so the first processor in any group has a stable, deterministic input regardless of granularity.
- Define merge / split rules precise enough that two implementers would write equivalent code.
- Preserve existing fields on `PostProcessingConfig` so existing YAML configs continue to load.
- Honor the ADR-0003 `FAILED` rule: log a WARNING and fall through to time-based processors.

**Non-Goals:**

- Linguistically aware splitting (e.g. Japanese clause boundaries, English clause boundaries, MeCab) — character-boundary processors split at character boundaries by time-driven heuristics; clause/punctuation logic is future work.
- Adding new granularities to `AlignmentGranularity`; the enum stays `{WORD, CHARACTER}`.
- Wiring `PostProcessingStage` into the runtime CLI / Orchestrator end-to-end — orchestrator integration occurs in `implement-subtitle-export`.
- Persisting per-cue confidence scores onto `Subtitle` — `Subtitle` stays as `(index, start_ms, end_ms, text)`.
- Splitting based on character-display-width (CJK widths, surrogate pairs); `max_line_length` is interpreted as a Python `len()` on the cue text.

## Decisions

### D1. Seed `Subtitle` construction is one cue per `TranscriptionResult`

Rejected alternative: one `Subtitle` per `AlignedToken`. Reason: token-level cues are too granular to display, and rebuilding a "natural" cue stream from tokens is just inverting work the merge processors would immediately undo.

Decision: `_build_seed_subtitles(ctx)` yields one `Subtitle` per `TranscriptionResult`, with `index = i + 1` (1-based per SRT convention), `start_ms / end_ms = result.start_ms / result.end_ms`, and `text = result.text`. This holds for every granularity, so the seed is decoupled from the processor choice.

### D2. `SubtitleProcessor.process` is pure and side-effect-free

Decision: every implementation MUST return a new `list[Subtitle]` with newly constructed `Subtitle` instances (frozen dataclass). The input list is treated as immutable. After every processor runs, the Stage re-numbers `index` to `1..len(subs)` to keep the SRT contract intact even if a processor changes the cue count.

Rejected alternative: in-place mutation. Reason: `Subtitle` is `frozen=True`, and the rest of the pipeline relies on `dataclasses.replace` immutability — making one Stage exempt is a footgun.

### D3. Word-boundary processors consume `TranscriptionResult.aligned_tokens` *out-of-band*

Each `Subtitle` carries no token references. So word-boundary processors need a way to recover them. Options:

- Add `tokens: list[AlignedToken]` to `Subtitle`. Rejected — pollutes the export-facing model with internal state.
- Pass the full `transcription_results` into `process()`. Rejected — breaks the `SubtitleProcessor` ISP and forces every processor to accept arguments it does not use.
- **Chosen**: `WordBoundaryMergeProcessor` and `WordBoundarySplitProcessor` are constructed by the factory with the per-cue token lookup baked in. The factory receives `ctx` and builds a `dict[int_subtitle_index, list[AlignedToken]]` keyed off the seed `Subtitle.index`. Processors close over this map. As soon as a processor produces a new cue list with renumbered indices, it MUST also produce a fresh map for downstream processors — accomplished by a small helper `_with_token_map(new_subs, parent_index_to_tokens)` that aggregates parent tokens into the merged/split children.

### D4. Character-boundary processors do not need a token map

Character-level alignment yields one token per character. The text-position-to-time mapping is recoverable from `Subtitle.start_ms` / `end_ms` plus `len(text)` by linear interpolation, which is accurate enough for splitting decisions. CharacterBoundaryMerge / Split therefore use only `Subtitle` fields and `PostProcessingConfig`, simplifying their construction.

### D5. Merge rule (all groups)

Two adjacent cues `a` and `b` are merged when ALL of the following hold:

- `b.start_ms - a.end_ms <= cfg.merge_gap_threshold_ms`
- `b.end_ms - a.start_ms <= cfg.merge_max_duration_ms`
- `len(a.text) + 1 + len(b.text) <= cfg.max_line_length * cfg.max_lines_per_subtitle`

Word/Character variants additionally require that the join point lands on a token boundary (which the seed already guarantees, since each seed cue spans one whole `TranscriptionResult`; merges always concatenate whole texts with a single separator — `" "` for WORD, `""` for CHARACTER, `" "` for time-based fallback).

### D6. Split rule (all groups)

A cue with `end_ms - start_ms > cfg.split_max_duration_ms` is split. The number of pieces is `ceil(duration / cfg.split_max_duration_ms)`, producing equal-time slices.

- WORD: time slice boundaries are snapped to the nearest token boundary (the token whose `start_ms` is closest); text is split at the same token index.
- CHARACTER: time slice boundaries are snapped to character indices via linear interpolation `char_idx = round(slice_ms / cue_duration_ms * len(text))`; text is split at those indices.
- Time-based fallback: text is split proportionally by `len(text)` (no token data available); time boundaries are equal-time.

If a cue cannot be split (e.g. only one token, or `len(text) <= 1`), the processor leaves it intact and emits a DEBUG log.

### D7. Processor ordering within a group is `[Merge, Split]`

Rationale: merging short cues first reduces the input size for split, and any cue produced by merge that turns out too long is then handled by split — a single forward pass. The reverse order risks splitting a cue that should have been merged with its neighbor first.

### D8. `PostProcessingConfig` field defaults

Add three fields with non-zero defaults so existing YAML files (which don't specify them) keep working:

- `merge_gap_threshold_ms: int = 200`
- `merge_max_duration_ms: int = 6000`
- `split_max_duration_ms: int = 6000`

These match the order-of-magnitude values implied by ADR-0003 (single cues should not exceed ~6 seconds). `model_config = {"extra": "forbid"}` is preserved; adding fields is backwards-compatible because they have defaults.

### D9. Disabled-path semantics

`PostProcessingStage` returns the seed subtitles unchanged (one cue per `TranscriptionResult`, indices renumbered) when `ctx.config.post_processing is None` or `enabled is False`. The factory MUST NOT be consulted in this path. Rationale: downstream export still needs *something* to write; emitting nothing would fail the end-to-end run.

### D10. FAILED-alignment semantics

When `ctx.alignment_status == AlignmentStatus.FAILED`, the Stage MUST log a WARNING (`"alignment FAILED — falling back to time-based post-processing"`) and pass `granularity=None` to the factory regardless of `ctx.alignment_granularity`. `DISABLED` is silent (no warning).

## Risks / Trade-offs

- **Token-map plumbing (D3)** adds a thin layer of complexity that only the WORD group uses. The alternative (passing tokens via `Subtitle`) was deemed worse because it leaks across module boundaries. If future granularities also need token introspection, the same factory-baked-closure pattern can extend without changing the `SubtitleProcessor` interface.
- **D4's linear-interpolation assumption** is wrong for variable-pace speech — characters are not uttered at constant rate. For CJK, this is acceptable because cues are short and per-character timing differences are sub-cue-relevant. If quality complaints arise, future work can swap CharacterBoundary processors to consume the actual per-character token map (same plumbing as D3).
- **D5's `len(text)` budget** uses Python `len()`. For CJK content, `len()` is the codepoint count, which roughly matches displayable width; for emoji or surrogate pairs it under-counts. Acceptable for v1; revisit if subtitle layout breaks observed in regression tests.
- **D6's "leave intact and log DEBUG"** for unsplittable cues means oversized cues can slip through. This matches the principle that the Stage should never raise on data-quality issues; the regression test suite (separate TODO) is the right place to surface these.
- **D7's `[Merge, Split]` order** assumes Merge never produces a cue exceeding `split_max_duration_ms`. The Merge rule (D5) already enforces `merge_max_duration_ms` as the upper bound, so this holds as long as `merge_max_duration_ms <= split_max_duration_ms`. The defaults satisfy this; a config validator on `PostProcessingConfig` raises `ValueError` if the invariant is violated.
