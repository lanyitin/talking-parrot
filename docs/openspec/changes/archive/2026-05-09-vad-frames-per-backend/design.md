## Context

`gui-backend` shipped `GET /api/vad_probs` against a snapshot whose `vad_frames: list[RawVadFrame]` carries no backend identity, forcing the GUI to zero-fill `silero` and `ten_vad`. `VADStage._align_frames` already builds `dict[str, list[RawVadFrame]]` keyed by backend `name` for internal alignment, then discards the per-backend frames after computing per-segment statistics. The composite score is computed per unified time point but never persisted as an inspectable timeline. The shared layer (`ProjectSnapshot`) was just archived; this change extends one of its fields rather than introducing a new aggregate.

`ProjectFile` is the on-disk DTO and is serialised by `ProjectFileWriter.write` via `dataclasses.asdict` + `json.dump` — any new dataclass field is automatically round-tripped without bespoke encoder logic. `FileSnapshotLoader._decode_list` decodes `vad_frames` items via `RawVadFrame(**item)`, so an additional required field on `RawVadFrame` would break legacy `.tp` files unless the loader injects a fallback.

## Goals / Non-Goals

**Goals:**

- Per-backend probability arrays (`silero`, `ten_vad`, `composite`) returned by `/api/vad_probs` reflect real measured probabilities for every backend that produced frames during the run.
- The `composite` score becomes a first-class persisted timeline so the GUI and future MCP tooling can inspect the formula's per-frame output.
- The on-disk `.tp` schema stays additive: existing files keep loading, only with a `backend="unknown"` tag and a one-shot warning.
- `ProjectSnapshot.vad_frames` keeps its declared type `list[RawVadFrame]` so existing consumers (regression, MCP) require no shape changes.

**Non-Goals:**

- Adding new VAD backends, changing the composite formula, or altering segment-merging behaviour.
- Bumping `ProjectFile.version`. The disk format is additive.
- Renaming `RawVadFrame.prob` or splitting it into per-backend columns.
- Frontend SPA work (still gated to `gui-frontend-timeline`).

## Decisions

### Tag frames with a single `backend: str` field on `RawVadFrame`

A required `backend: str` field is added to `RawVadFrame`. Real backends use their `VADBackend.name` value (e.g., `"silero_vad"`, `"ten_vad"`); the unified composite series uses the literal string `"composite"`. This keeps `ProjectSnapshot.vad_frames` as a flat list and makes downstream filtering a one-liner (`frame for frame in vad_frames if frame.backend == "silero_vad"`).

Alternative considered: turn `ProjectSnapshot.vad_frames` into a `dict[str, list[RawVadFrame]]`. Rejected because it would change the snapshot field shape (breaking the `project-snapshot` spec), require a new on-disk JSON shape, and force every fixture and the snapshot loader's `_OPTIONAL_LIST_FIELDS` machinery to special-case this one field.

### Persist the composite timeline as a synthetic `"composite"` backend

`VADStage` already computes a composite score for each unified-timeline frame. After Step 3 (composite computation), the stage emits one `RawVadFrame(time_ms=t, prob=score, backend="composite")` per unified frame in addition to the per-backend frames. Storing the composite alongside real backends means the GUI does not need to recompute the formula at request time and means `/api/vad_probs` returns three arrays drawn from the same data structure.

Alternative considered: keep the composite series as a separate snapshot field. Rejected because it would double the persistence-and-loader surface for what is conceptually the same per-frame probability shape.

### Extend `PipelineContext` with `vad_frames` rather than threading frames through ad-hoc kwargs

`PipelineContext` gains `vad_frames: list[RawVadFrame] = field(default_factory=list)` so `VADStage.process` can write the tagged frames into the context the same way it writes `vad_segments`. `cli.py` then forwards `ctx.vad_frames` into `ProjectFile.vad_frames`. This mirrors the existing flow for `vad_segments` and avoids introducing a parallel out-of-band channel.

Alternative considered: pass per-backend frames out of band via a side channel (e.g., a logger or a writable buffer on the stage). Rejected for breaking the immutable-context discipline (`PipelineContext` is `frozen=True`, replaced via `dataclasses.replace`).

### Tolerate legacy `.tp` files without a `backend` field

`FileSnapshotLoader._decode_list` substitutes `"unknown"` for any frame missing a `backend` key and emits a `logging.warning` naming the file path once per `load(...)` call (not once per frame). The GUI's `_handle_vad_probs` ignores frames whose `backend` is not in the set `{"silero_vad", "ten_vad", "composite"}`, so legacy frames quietly drop out of the response. Users wanting clean per-backend curves re-run the pipeline.

Alternative considered: bump `ProjectFile.version` and reject legacy files. Rejected because the change is strictly additive and rejecting on-disk artefacts would be hostile to anyone with archived `.tp` files.

### Reuse the union-then-tolerance alignment in the GUI handler

`_handle_vad_probs` uses the union of all three backend timestamps in the requested interval as the unified `times_ms` axis, then nearest-neighbour-fills each backend column with a 50 ms tolerance window — identical to `VADStage._align_frames`. The `downsample` query parameter applies after alignment via stride sampling. The 50 ms tolerance constant is hoisted into a module-private `_ALIGN_TOLERANCE_MS` in `gui.api` to make the design link explicit and to avoid drift if the stage's tolerance ever changes. (If the stage tolerance changes in the future, that constant must be revisited.)

Alternative considered: store the unified timeline once on the snapshot and have the GUI read it directly. Rejected for this change because it adds a second persisted timeline; the recomputation cost in `_handle_vad_probs` is bounded by the requested interval and is acceptable for one-developer-at-a-time GUI use.

## Implementation Contract

**Behavior:**

- After running the pipeline, `ProjectSnapshot.vad_frames` SHALL contain tagged `RawVadFrame` instances for every backend that produced frames plus a synthetic `"composite"` backend covering the unified timeline. Each frame's `prob` is the same value previously held in the un-tagged frame (real backends) or the composite score (synthetic backend).
- `GET /api/vad_probs?start_ms=A&end_ms=B[&downsample=N]` SHALL return JSON of shape `{"times_ms": [int], "silero": [float], "ten_vad": [float], "composite": [float]}` where the four arrays have equal length, `times_ms` is the union (within the interval) of timestamps from frames whose `backend` is in `{"silero_vad", "ten_vad", "composite"}`, and each backend column is nearest-neighbour-filled with a 50 ms tolerance (zeros where no frame falls within tolerance).
- Loading a legacy `.tp` file without `backend` keys on `vad_frames` items SHALL succeed; the loader SHALL emit exactly one `logging.warning` whose message contains the file path and the substring `legacy vad_frames without 'backend' tag`. Frames so loaded SHALL have `backend == "unknown"` and SHALL be excluded from `/api/vad_probs` output.

**Interface / data shape:**

- `RawVadFrame` (frozen dataclass): `time_ms: int`, `prob: float`, `backend: str`. All three fields are required at construction.
- `PipelineContext` (frozen dataclass): existing fields plus `vad_frames: list[RawVadFrame]` (default factory: empty list).
- `ProjectFile` (frozen dataclass): existing fields plus `vad_frames: list = field(default_factory=list)`. Items are dataclass dicts of `RawVadFrame` after `dataclasses.asdict`.
- `gui.api._handle_vad_probs(snapshot, query) -> ApiResponse`: unchanged signature, new internal grouping by `frame.backend`.

**Failure modes:**

- Constructing `RawVadFrame` without `backend` raises `TypeError` (Python dataclass default).
- Loading a `.tp` file whose `vad_frames` items contain `backend` keys but missing `time_ms` or `prob` propagates `TypeError` from `RawVadFrame(**item)` (existing behavior, unchanged).
- `_handle_vad_probs` returns the same 400 errors as today for invalid `start_ms`/`end_ms`/`downsample`. When the interval contains no frames for a given backend, that column is an array of zeros of the same length as `times_ms` (not omitted).

**Acceptance criteria:**

- `tests/unit/vad/test_raw_vad_frame_backend.py::test_raw_vad_frame_requires_backend` — `RawVadFrame(time_ms=0, prob=0.5)` raises `TypeError`.
- `tests/unit/stages/test_vad_stage.py::test_vad_stage_emits_per_backend_and_composite_frames` — running `VADStage.process` with two backends produces `ctx.vad_frames` containing entries tagged `"silero_vad"`, `"ten_vad"`, and `"composite"`.
- `tests/unit/shared/test_snapshot_loader.py::test_legacy_vad_frames_default_backend_unknown` — loading a `.tp` whose `vad_frames` items omit `backend` yields frames with `backend == "unknown"` and emits exactly one `WARNING`-level log record matching the contracted substring.
- `tests/unit/gui/test_api.py::test_vad_probs_returns_real_per_backend_arrays` — fixture snapshot containing tagged frames for `silero_vad` and `ten_vad` and `composite` produces three non-zero arrays.
- `uv run pytest`, `uv run mypy src`, `uv run ruff check .`, `uv run ruff format --check .` all pass after the change.

**Scope boundaries:**

- In scope: `RawVadFrame` schema, `VADStage.process` output, `PipelineContext.vad_frames`, `ProjectFile.vad_frames`, `ProjectFileWriter` round-trip, `FileSnapshotLoader._decode_list` legacy fallback, `gui.api._handle_vad_probs` regrouping, fixture/test updates.
- Out of scope: VAD backend implementations (`silero_vad.py`, `ten_vad.py`) keep their existing internal behavior — they continue to return frames without a `backend` tag, and `VADStage.process` is responsible for tagging them. Frontend SPA, MCP bridge, alignment stage, post-processing stage, and any other pipeline stage are not modified.

## Risks / Trade-offs

- **Risk:** Tests that construct `RawVadFrame` positionally break because of the new required field. → **Mitigation:** task list enumerates every fixture site (search hits in `tests/unit/stages/test_vad_stage.py` and `tests/unit/models/test_data_models.py`); each site is updated to pass `backend=` keyword arg explicitly.
- **Risk:** Legacy `.tp` files become silently lossy in the GUI (their frames render as zeros). → **Mitigation:** loader emits one `WARNING` per legacy load naming the path; GUI design notes the symptom; users re-run the pipeline.
- **Risk:** Persisting the composite timeline doubles the on-disk frame count compared to today. → **Mitigation:** acceptable; frame counts are O(audio duration in frames) and the JSON is already compressed by the consumer's filesystem. No new file format. If profiling later shows this is a problem, a follow-up change can introduce a sparser composite encoding.
- **Trade-off:** The GUI re-runs nearest-neighbour alignment per request rather than reading a pre-aligned timeline. Acceptable for one-developer-at-a-time use; revisit only if profiling reveals an issue.

## Migration Plan

1. Land the change behind no flag; the `.tp` schema is additive.
2. On first load of an existing `.tp`, the loader emits one `WARNING` naming the path. Operators choose whether to re-run the pipeline.
3. No rollback steps are required: removing the `backend` field reverts `RawVadFrame` to its prior shape, and the loader's tolerant fallback already accepts files written by the new code (it just sees `backend="unknown"` if the writer were rolled back).

## Open Questions

None.
