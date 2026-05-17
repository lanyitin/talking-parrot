## Why

The three quality-and-tooling initiatives (regression harness, analysis GUI, MCP server) all need to consume the same pipeline output: VAD frames/segments, chunks, transcription results with per-token alignment, pre/post-processing subtitles, and audio metadata. Without a shared, frozen, in-memory representation, each initiative would re-parse the on-disk project file and define its own field shape — leading to drift between the three tools and forcing every downstream change to ripple into three places.

This change establishes the shared data layer first so that regression, GUI, and MCP can be built in parallel against a stable contract.

## What Changes

- Add a new `src/talking_parrot/shared/` sub-package containing the in-memory abstractions used by all three downstream tools.
- Introduce `ProjectSnapshot`, a frozen value object that carries every pipeline intermediate (audio info, raw VAD frames, VAD segments, chunks, transcription results with aligned tokens, pre-postprocess subtitles, final subtitles, config snapshot).
- Introduce a `SnapshotLoader` protocol plus a default file-backed implementation that loads a `.tp` project file from disk into a `ProjectSnapshot` and never mutates it after load.
- Introduce `ScoreCard`, `CueDiff`, and `MetricBundle` value objects in `shared/metrics.py` that downstream regression scoring will populate.
- Keep the existing `ProjectFile` dataclass unchanged for now — it remains the on-disk serialisation DTO; `ProjectSnapshot` is the richer in-memory view derived from it.
- No CLI, no HTTP server, no MCP tool is added in this change — only the shared library code, its public API, and tests.

## Non-Goals

- Defining the regression scoring algorithm (CER, confidence aggregation) — that belongs to a later `regression-runner` change. This change only introduces the empty value-object shapes.
- Producing the `.tp` writer. Pipeline-side serialisation continues to use the existing `ProjectFile` path; extending the writer to emit the new fields is out of scope and will be addressed when the regression runner needs to author snapshots.
- Touching `regression/`, `gui/`, or `mcp/` packages — those are downstream changes that depend on this one.
- Changing the existing `pipeline-data-models` capability requirements. `RawVadFrame`, `VadSegment`, `Chunk`, `TranscriptionResult`, `Subtitle` are reused as-is.
- Adding new third-party dependencies.

## Capabilities

### New Capabilities

- `project-snapshot`: Frozen in-memory aggregate of every pipeline intermediate, consumed by regression / GUI / MCP. Defines field shape and immutability contract.
- `snapshot-loader`: Protocol + default file-backed implementation for materialising a `ProjectSnapshot` from a `.tp` project file. Defines the abstraction boundary that lets downstream code depend on a port rather than a filesystem path.
- `quality-metrics`: Value objects (`ScoreCard`, `CueDiff`, `MetricBundle`) that the future regression scorer will populate. Defines field shape only — no scoring logic.

### Modified Capabilities

(none)

## Impact

- Affected specs: three new capabilities listed above.
- Affected code:
  - New:
    - src/talking_parrot/shared/__init__.py
    - src/talking_parrot/shared/project_snapshot.py
    - src/talking_parrot/shared/snapshot_loader.py
    - src/talking_parrot/shared/metrics.py
    - tests/unit/shared/__init__.py
    - tests/unit/shared/test_project_snapshot.py
    - tests/unit/shared/test_snapshot_loader.py
    - tests/unit/shared/test_metrics.py
  - Modified: (none)
  - Removed: (none)
- Dependencies: no new third-party packages.
- Downstream: unblocks future `regression-runner`, `gui-backend`, and `mcp-core` changes (all depend on `shared/`).
