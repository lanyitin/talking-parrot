## Summary

Carry per-backend VAD frame timelines (with backend identity) end-to-end through the pipeline, persistence, and `ProjectSnapshot`, so `/api/vad_probs` can return real per-backend `silero`/`ten_vad`/`composite` arrays instead of zero-filled stubs.

## Motivation

The just-implemented `gui-backend` change exposed a follow-up: `GET /api/vad_probs` is contracted to return three equal-length arrays — `silero`, `ten_vad`, and `composite` — but the only data available on `ProjectSnapshot` is a flat `vad_frames: list[RawVadFrame]` with no backend identity. The current GUI implementation fills `composite` and zero-fills `silero` and `ten_vad`, which makes the timeline view in `gui-frontend-timeline` unusable for per-backend inspection.

The pipeline already computes per-backend frames inside `VADStage._align_frames` but discards them after computing `VadSegment` statistics. Persisting them is a small, well-bounded extension of the data model.

## Proposed Solution

Add a `backend: str` field to `RawVadFrame`. Treat the unified composite timeline as a synthetic backend named `"composite"` carried in the same flat list. Wire the per-backend frames through:

1. `RawVadFrame` — frozen dataclass gains required `backend: str` field. The field carries the backend's `name` (e.g., `"silero_vad"`, `"ten_vad"`) for real backends and the literal string `"composite"` for the unified composite series.
2. `VADStage.process` — collects each backend's tagged frames plus a derived `composite` series (one frame per unified time point) into a single `list[RawVadFrame]` and writes it to `PipelineContext.vad_frames`.
3. `PipelineContext` — gains a new field `vad_frames: list[RawVadFrame]` defaulting to `[]`.
4. `ProjectFile` — gains a new field `vad_frames: list = field(default_factory=list)`. `cli.py` populates it from `ctx.vad_frames` before writing. `ProjectFileWriter` already serialises any new dataclass field via `dataclasses.asdict`, so no encoder change is required.
5. `FileSnapshotLoader._decode_list` — decodes `vad_frames` items by passing the JSON dict to `RawVadFrame(**item)`; when `backend` is missing on disk (legacy `.tp` files) the loader SHALL substitute the literal string `"unknown"` and emit a `logging` warning naming the file path.
6. `gui/api.py:_handle_vad_probs` — groups `snapshot.vad_frames` by `backend`, builds `times_ms` from the union of all backend frame timestamps in the requested interval (mirroring `VADStage._align_frames`'s union-then-tolerance approach with the same 50 ms tolerance), then emits `silero`, `ten_vad`, `composite` arrays of equal length. Frames whose `backend` is neither `"silero_vad"`, `"ten_vad"`, nor `"composite"` are ignored. The current zero-fill comment in `gui/api.py` is removed.

## Non-Goals

- Adding new VAD backends or changing the VAD composite formula.
- Frontend SPA work (still gated to `gui-frontend-timeline`).
- Touching `RawVadFrame.prob` semantics — still per-frame probability in `[0.0, 1.0]`.
- Bumping the `.tp` project file `version`. The change is additive (new optional field on `RawVadFrame`); legacy files load with `backend="unknown"` and emit a warning.
- Changing the wire contract of `/api/vad_probs` in `gui-api-endpoints` — the contract already specifies three per-backend arrays; this change only makes the implementation honour it.
- Renaming the existing `RawVadFrame.prob` field or splitting it into per-backend columns.

## Alternatives Considered

- **Option B: keyed `dict[str, list[RawVadFrame]]` on `ProjectSnapshot`.** Closer to the internal `VADStage._align_frames` shape, but it would change `ProjectSnapshot.vad_frames`'s declared type (breaking the `project-snapshot` spec), require a new on-disk JSON shape, and force every test fixture and the snapshot loader's `_OPTIONAL_LIST_FIELDS` machinery to special-case this one field. Rejected because the flat-list-with-tag approach keeps the snapshot field shape stable and reuses existing serialisation paths.
- **Bumping the `.tp` project file `version`.** Considered for clean migration, but the change is strictly additive (legacy files still parse and yield runnable snapshots), so a warning-and-tag fallback is sufficient and cheaper for the user.

## Impact

- Affected specs:
  - `pipeline-data-models` — Modified: `RawVadFrame` gains `backend: str`; `PipelineContext` gains `vad_frames`.
  - `vad-stage` — Modified: `VADStage.process` populates `ctx.vad_frames` with tagged per-backend and composite frames.
  - `project-snapshot` — Modified: `vad_frames` items carry backend identity.
  - `snapshot-loader` — Modified: tolerate missing `backend` on legacy `.tp` files via `"unknown"` substitution and a warning log.
- Affected code:
  - Modified:
    - src/talking_parrot/models/vad.py
    - src/talking_parrot/models/context.py
    - src/talking_parrot/models/project_file.py
    - src/talking_parrot/io/project_writer.py
    - src/talking_parrot/stages/vad_stage.py
    - src/talking_parrot/vad/silero_vad.py
    - src/talking_parrot/vad/ten_vad.py
    - src/talking_parrot/shared/snapshot_loader.py
    - src/talking_parrot/shared/project_snapshot.py
    - src/talking_parrot/cli.py
    - src/talking_parrot/gui/api.py
    - tests/unit/models/test_data_models.py
    - tests/unit/stages/test_vad_stage.py
    - tests/unit/shared/test_snapshot_loader.py
    - tests/unit/shared/test_project_snapshot.py
    - tests/unit/gui/conftest.py
    - tests/unit/gui/test_api.py
  - New:
    - tests/unit/vad/test_raw_vad_frame_backend.py
  - Removed: (none)
