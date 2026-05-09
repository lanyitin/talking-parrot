# Tasks: vad-frames-per-backend

## 1. Data model — RawVadFrame gains backend tag

- [x] 1.1 Implement requirement `RawVadFrame is an immutable value object` (per the design decision "Tag frames with a single `backend: str` field on `RawVadFrame`") by adding the required `backend: str` field to `RawVadFrame` in `src/talking_parrot/models/vad.py` (frozen dataclass); update the module docstring to mention the tag's semantics; verified by `tests/unit/vad/test_raw_vad_frame_backend.py::test_raw_vad_frame_requires_backend` (constructing without `backend` raises `TypeError`).
- [x] 1.2 [P] Add `tests/unit/vad/test_raw_vad_frame_backend.py::test_raw_vad_frame_rejects_empty_backend` asserting that constructing with `backend=""` raises `ValueError` (enforced via `__post_init__`).
- [x] 1.3 Implement `RawVadFrame.__post_init__` in `src/talking_parrot/models/vad.py` raising `ValueError` when `backend` is empty; verified by 1.2's test.

## 2. Pipeline context — vad_frames field

- [x] 2.1 Implement requirement `PipelineContext fields` (per the design decision "Extend `PipelineContext` with `vad_frames` rather than threading frames through ad-hoc kwargs") by adding `vad_frames: list = field(default_factory=list)` to `PipelineContext` in `src/talking_parrot/models/context.py`; verified by `tests/unit/models/test_data_models.py::test_pipeline_context_vad_frames_default_empty` (new test asserting the default).
- [x] 2.2 Update existing fixture/test sites in `tests/unit/models/test_data_models.py` that construct `RawVadFrame` to pass `backend="silero_vad"` (or another concrete tag) explicitly so they stay green under the new required field.

## 3. VAD backends — preserve internal frame return shape

- [x] 3.1 Update `src/talking_parrot/vad/silero_vad.py::SileroVADBackend.analyze` to construct `RawVadFrame` with `backend=self.name`; existing `tests/unit/vad/test_silero_vad.py` updated where it asserts the frame shape.
- [x] 3.2 Update `src/talking_parrot/vad/ten_vad.py::TenVADBackend.analyze` symmetrically; existing `tests/unit/vad/test_ten_vad.py` updated where it asserts the frame shape.

## 4. VADStage — emit per-backend and composite frames

- [x] 4.1 Implement requirement `VADStage emits tagged per-backend and composite frames into PipelineContext` in `VADStage.process` (`src/talking_parrot/stages/vad_stage.py`): collect tagged backend frames into a single `list[RawVadFrame]`, append one `RawVadFrame(time_ms=t, prob=score, backend="composite")` per unified-timeline frame after Step 3 composite computation, and write the combined list to `ctx.vad_frames` via `dataclasses.replace`. Verified by `tests/unit/stages/test_vad_stage.py::test_vad_stage_emits_per_backend_and_composite_frames`.
- [x] 4.2 Add `tests/unit/stages/test_vad_stage.py::test_vad_stage_disabled_leaves_vad_frames_untouched` asserting that when `ctx.config.vad.enabled is False`, the returned context's `vad_frames` equals the input's (i.e., `[]` if not pre-populated).
- [x] 4.3 Update existing `tests/unit/stages/test_vad_stage.py` test cases that construct `RawVadFrame` to pass the `backend=` keyword; ensure all tests in `test_vad_stage.py` stay green.

## 5. ProjectFile / writer — persist vad_frames

- [x] 5.1 Implement requirement `ProjectFile is pure data` (per the design decision "Persist the composite timeline as a synthetic `"composite"` backend") by adding `vad_frames: list = field(default_factory=list)` to `ProjectFile` in `src/talking_parrot/models/project_file.py`; verified by `tests/unit/io/test_project_writer.py::test_project_file_vad_frames_round_trip` (new test) writing a `ProjectFile` containing a tagged `RawVadFrame` and confirming the JSON contains the `backend` field.
- [x] 5.2 In `src/talking_parrot/cli.py`, populate `ProjectFile.vad_frames` from `ctx.vad_frames` before calling `ProjectFileWriter.write`; verified by `tests/unit/io/test_project_writer.py::test_project_file_vad_frames_round_trip` and an end-to-end smoke check that an existing CLI test still passes.

## 6. Snapshot loader — legacy fallback

- [x] 6.1 Implement requirement `Legacy vad_frames without backend tag default to "unknown"` (per the design decision "Tolerate legacy `.tp` files without a `backend` field") in `FileSnapshotLoader._decode_list` (`src/talking_parrot/shared/snapshot_loader.py`): for each `vad_frames` item missing the `backend` key, substitute `"unknown"`; emit exactly one `logging.warning` per `load(...)` call containing the file path and the literal substring `legacy vad_frames without 'backend' tag`. Verified by `tests/unit/shared/test_snapshot_loader.py::test_legacy_vad_frames_default_backend_unknown`.
- [x] 6.2 Add `tests/unit/shared/test_snapshot_loader.py::test_modern_vad_frames_no_legacy_warning` asserting modern files (with `backend` keys) produce no `legacy vad_frames` warning.
- [x] 6.3 Add `tests/unit/shared/test_snapshot_loader.py::test_mixed_vad_frames_emit_one_warning` asserting a mixed file emits exactly one warning, not one per legacy frame.

## 7. Project snapshot — keep field declared shape, document new tag semantics

- [x] 7.1 [P] Update the docstring of `ProjectSnapshot` in `src/talking_parrot/shared/project_snapshot.py` to note that `vad_frames` items carry a `backend: str` tag (`"silero_vad"`, `"ten_vad"`, `"composite"`, or `"unknown"` for legacy files); no functional change. No new test required; verified by `tests/unit/shared/test_project_snapshot.py` staying green.

## 8. GUI — real per-backend arrays in /api/vad_probs

- [x] 8.1 Implement the design decision `Reuse the union-then-tolerance alignment in the GUI handler`: in `src/talking_parrot/gui/api.py`, define a module-private constant `_ALIGN_TOLERANCE_MS = 50` (matching `VADStage._align_frames`) and replace the zero-fill implementation in `_handle_vad_probs` with a grouping pass: bucket `snapshot.vad_frames` by `frame.backend`, build `times_ms` from the union of timestamps in `[start_ms, end_ms)` from frames whose backend is in `{"silero_vad", "ten_vad", "composite"}`, then nearest-neighbour-fill each backend column with the 50 ms tolerance window (zeros where no frame falls within tolerance). Apply the existing `downsample` query parameter via stride sampling after alignment.
- [x] 8.2 Update the existing `numpy` follow-up comment block at the top of `src/talking_parrot/gui/api.py` to reflect that the zero-fill workaround has been removed; remove any sentence claiming `silero`/`ten_vad` arrays are zero-filled.
- [x] 8.3 [P] Add `tests/unit/gui/test_api.py::test_vad_probs_returns_real_per_backend_arrays` constructing a fixture snapshot with tagged frames for `silero_vad`, `ten_vad`, and `composite` and asserting all three response arrays contain the expected non-zero values at the correct timestamps.
- [x] 8.4 [P] Add `tests/unit/gui/test_api.py::test_vad_probs_ignores_unknown_backend_frames` constructing a snapshot whose `vad_frames` includes frames with `backend="unknown"` and asserting they do not appear in any response column (the column for any backend with no in-range frames remains all zeros).
- [x] 8.5 [P] Update `tests/unit/gui/conftest.py::make_snapshot` so its `vad_frames` argument can supply tagged frames; default fixture frames SHALL carry a concrete `backend` tag rather than relying on a positional `RawVadFrame(time_ms, prob)` shape.

## 9. Quality gates

- [x] 9.1 Run `uv run ruff check .` and `uv run ruff format --check .` — zero errors.
- [x] 9.2 Run `uv run mypy src` — zero new errors introduced by this change (the pre-existing `japanese_backend.py:144` baseline error is out of scope).
- [x] 9.3 Run `uv run pytest` — full suite green (existing 691 + new tests).
