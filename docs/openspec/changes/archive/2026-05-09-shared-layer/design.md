## Context

Three downstream initiatives — regression harness, analysis GUI, MCP server — all need to consume the same pipeline output. The existing `ProjectFile` dataclass (`src/talking_parrot/models/project_file.py`) only carries `media`, `config`, `vad_segments`, `transcription_results`, and `subtitles`, missing `vad_frames` (raw per-frame VAD probabilities), `chunks`, `pre_postprocess_subtitles`, per-result `aligned_tokens`, and aggregate audio statistics. The downstream tools need all of these.

The existing `ProjectFile` is referenced by `pipeline-data-models` capability and is currently the on-disk DTO. We must not break that contract — the on-disk format stays as-is until a future change extends the writer.

## Goals / Non-Goals

**Goals:**

- Provide a single, frozen, in-memory aggregate (`ProjectSnapshot`) that downstream tools depend on instead of `ProjectFile` or filesystem paths.
- Provide a swappable loader abstraction (`SnapshotLoader` protocol) so tests and downstream code can substitute fixtures or alternative sources.
- Provide empty-shape value objects (`ScoreCard`, `CueDiff`, `MetricBundle`) so the regression scorer can be designed in a later change without redefining types.

**Non-Goals:**

- Defining scoring algorithms (CER, confidence aggregation) — only the data shape.
- Modifying the on-disk `ProjectFile` writer or the `pipeline-data-models` requirements.
- Implementing any consumer (regression / GUI / MCP) — those are downstream changes.
- Adding new third-party dependencies.

## Decisions

### Use a Protocol, not an ABC, for the loader abstraction

`SnapshotLoader` is defined as `typing.Protocol` with one method `load(source: str | Path) -> ProjectSnapshot`. Rationale: structural typing fits this case (any object with `.load(...)` returning a snapshot is acceptable, including ad-hoc test stubs and lambdas wrapped in a small adapter). ABC would force inheritance and add ceremony for fixtures. Alternatives considered: ABC (rejected, ceremony) and a plain callable type alias (rejected, less self-documenting).

### `ProjectSnapshot` is a separate frozen dataclass, not an extension of `ProjectFile`

`ProjectSnapshot` lives in `shared/project_snapshot.py` as its own frozen dataclass with the full field set (audio_info, vad_frames, vad_segments, chunks, transcription_results, pre_postprocess_subtitles, subtitles, config_snapshot, version, created_at, source_path). `ProjectFile` is left untouched. Rationale: keeps the existing on-disk DTO contract under `pipeline-data-models` stable, and lets `ProjectSnapshot` carry richer fields that the writer does not yet emit. A `ProjectSnapshot.from_project_file(pf, *, vad_frames=..., chunks=..., aligned_tokens=...)` classmethod bridges the two when callers have a `ProjectFile` plus extras. Alternatives considered: extending `ProjectFile` in place (rejected — would change `pipeline-data-models` requirements and break the on-disk DTO boundary).

### Reuse existing model classes by reference, do not re-define them

`RawVadFrame`, `VadSegment`, `Chunk`, `TranscriptionResult`, `Subtitle`, `AlignedToken` are imported from `src/talking_parrot/models/`. The shared layer adds only the missing pieces: `AudioInfo`, `TranscriptionMetrics` (if not already present in `models/transcription.py`), and the snapshot aggregate itself. Rationale: SRP — `models/` owns pipeline-stage value objects; `shared/` owns the cross-tool aggregate.

### `ScoreCard` and friends are empty-shape this change

`ScoreCard`, `CueDiff`, `MetricBundle` are introduced with field declarations only — no scoring methods. The regression scorer in a later change will populate them. Rationale: locks in the field contract that GUI and MCP can also display, without coupling this change to scoring algorithm decisions.

### File-backed loader is the only implementation in this change

`shared/snapshot_loader.py` ships `FileSnapshotLoader` that reads a `.tp` JSON file and returns a `ProjectSnapshot`. It tolerates the current on-disk format (which lacks `vad_frames`, `chunks`, `aligned_tokens`, `pre_postprocess_subtitles`) by populating those fields with empty lists when absent. Rationale: keeps backward compatibility with existing `.tp` files written by the current pipeline; downstream changes can extend the writer when the richer fields are needed end-to-end.

## Implementation Contract

**Behavior:**

- After this change, `from talking_parrot.shared import ProjectSnapshot, SnapshotLoader, FileSnapshotLoader, ScoreCard, CueDiff, MetricBundle` succeeds.
- `FileSnapshotLoader().load(path)` returns a frozen `ProjectSnapshot` whose required scalar fields (`version`, `created_at`, `source_path`, `config_snapshot`, `audio_info`) are populated from the `.tp` file, and whose list fields (`vad_frames`, `vad_segments`, `chunks`, `transcription_results`, `pre_postprocess_subtitles`, `subtitles`) default to empty when the file omits them.
- `ProjectSnapshot` raises `dataclasses.FrozenInstanceError` on attribute reassignment.
- `SnapshotLoader` is satisfied structurally — any object with `load(source) -> ProjectSnapshot` qualifies; verified by a duck-typed test fixture.

**Interface / data shape:**

- `ProjectSnapshot` field set matches the classDiagram in `docs/planning/quality-and-tooling/shared-architecture.md` §3.
- `ScoreCard` carries: `sample_id: str`, `overall_score: float`, `metric_bundle: MetricBundle`, `cue_diffs: list[CueDiff]`. `MetricBundle` and `CueDiff` field shape is documented in the spec for `quality-metrics`.
- `SnapshotLoader.load(source: str | Path) -> ProjectSnapshot`.

**Failure modes:**

- Missing file → `FileNotFoundError` propagated unchanged.
- Malformed JSON → `json.JSONDecodeError` propagated unchanged.
- Missing required scalar field → `KeyError` with the field name; this is a hard failure, not a silent default.
- Missing list field → defaults to empty list, no error.

**Acceptance criteria:**

- `uv run pytest tests/unit/shared/` is green.
- `uv run ruff check src/talking_parrot/shared tests/unit/shared` reports no issues.
- `uv run mypy src/talking_parrot/shared` passes.
- A unit test exercises round-trip: a `ProjectFile` plus extras → `ProjectSnapshot.from_project_file(...)` → assertions on every field.
- A unit test confirms `ProjectSnapshot` rejects mutation.
- A unit test confirms `FileSnapshotLoader` defaults missing list fields to empty without raising.
- A unit test confirms a duck-typed loader (a plain class with a `.load` method) satisfies `SnapshotLoader` at runtime via `isinstance(obj, SnapshotLoader)` (Protocol with `runtime_checkable`).

**Scope boundaries:**

- In scope: `src/talking_parrot/shared/` package (new), corresponding `tests/unit/shared/` tests.
- Out of scope: `regression/`, `gui/`, `mcp/` packages; CLI entry points; `.tp` writer changes; `pipeline-data-models` spec edits; new dependencies.

## Risks / Trade-offs

- Duplication between `ProjectFile` and `ProjectSnapshot` field sets → Mitigation: `from_project_file` classmethod is the only sanctioned bridge; future change folds `ProjectFile` into the snapshot once the writer is extended.
- `FileSnapshotLoader` defaulting missing fields to empty lists may hide on-disk format drift → Mitigation: log a debug-level message naming each field that defaulted; a follow-up change will tighten this once the writer emits the richer fields.
- `Protocol` with `runtime_checkable` performs structural checks via `hasattr`, which is permissive → Mitigation: documented limitation; the protocol is a design tool, not a security boundary.
- `ScoreCard` is empty-shape and may be revised when the scorer lands → Mitigation: explicitly flagged as a non-goal of this change; the future regression-runner change owns the final shape.
