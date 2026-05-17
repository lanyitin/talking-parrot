## ADDED Requirements

### Requirement: VADStage emits tagged per-backend and composite frames into PipelineContext

`VADStage.process` SHALL populate `ctx.vad_frames` with the union of:
1. Every backend's tagged frames — for each `VADBackend` in `self._backends`, every `RawVadFrame` returned from `analyze(...)` SHALL appear in `ctx.vad_frames` with its `backend` field set to that backend's `name` attribute.
2. A synthetic composite series — one `RawVadFrame` per unified-timeline frame produced by `_align_frames`, with `time_ms` equal to the unified time point, `prob` equal to the composite score computed by `FormulaEvaluator`, and `backend` equal to the literal string `"composite"`.

The composite frames SHALL be emitted only after composite scores have been computed (Step 3 in the stage pipeline), so every `"composite"` frame's `prob` is the value `FormulaEvaluator.evaluate(...)` returned for the corresponding unified time point.

When the stage is disabled (`ctx.config.vad is None` or `ctx.config.vad.enabled is False`), `ctx.vad_frames` SHALL remain unchanged from the input context (i.e., no frames are emitted).

#### Scenario: stage emits per-backend and composite frames

- **GIVEN** a `VADStage` configured with two backends named `"silero_vad"` and `"ten_vad"` returning two frames each at the same timestamps
- **WHEN** `process(ctx)` is called with VAD enabled
- **THEN** the returned context's `vad_frames` MUST contain at least one frame with `backend == "silero_vad"`, at least one with `backend == "ten_vad"`, and at least one with `backend == "composite"`
- **THEN** every frame's `prob` MUST be in `[0.0, 1.0]`

#### Scenario: stage disabled leaves vad_frames untouched

- **GIVEN** a `PipelineContext` with `ctx.config.vad.enabled == False` and `ctx.vad_frames == []`
- **WHEN** `process(ctx)` is called
- **THEN** the returned context's `vad_frames` MUST equal `[]`

##### Example: two backends and composite

- **GIVEN** ten_vad frames `[(0, 0.9), (16, 0.8)]` and silero_vad frames `[(0, 0.85), (16, 0.75)]`, with a composite formula yielding `0.875` at `t=0` and `0.775` at `t=16`
- **WHEN** `VADStage.process` runs
- **THEN** `ctx.vad_frames` contains at minimum: `RawVadFrame(0, 0.9, "ten_vad")`, `RawVadFrame(16, 0.8, "ten_vad")`, `RawVadFrame(0, 0.85, "silero_vad")`, `RawVadFrame(16, 0.75, "silero_vad")`, `RawVadFrame(0, 0.875, "composite")`, `RawVadFrame(16, 0.775, "composite")`
