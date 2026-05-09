# vad-stage Specification

## Purpose

TBD - created by archiving change 'implement-vad-stage'. Update Purpose after archive.

## Requirements

### Requirement: VADStage is disabled when vad config is absent or disabled

The system SHALL return the input `PipelineContext` unchanged when `ctx.config.vad` is `None` or `ctx.config.vad.enabled` is `False`.

#### Scenario: stage skipped when vad is disabled

- **WHEN** `VADStage.process()` is called with `ctx.config.vad.enabled = False`
- **THEN** the returned context is identical to the input context
- **THEN** `ctx.vad_segments` remains an empty list


<!-- @trace
source: implement-vad-stage
updated: 2026-05-01
code:
  - src/talking_parrot/vad/ten_vad.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/vad/__init__.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/stages/chunking_stage.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/backend.py
  - tests/unit/vad/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/vad_stage.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/vad/test_backend.py
  - tests/unit/vad/test_silero_vad.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_backend.py
-->

---
### Requirement: VADStage aligns frames from multiple backends by nearest-neighbour

The system SHALL compute a unified timeline from the union of all backend frame `time_ms` values. For each time point, each backend's probability SHALL be the `prob` of its closest frame within a 50 ms tolerance window. If no frame falls within tolerance, the probability SHALL default to `0.0`.

#### Scenario: frame alignment with two backends at different rates

- **WHEN** TenVADBackend returns frames at 16 ms intervals and SileroVADBackend at 32 ms intervals
- **THEN** the unified timeline contains time points from both backends
- **THEN** each unified point has a probability from both backends (or 0.0 if none within 50 ms)

##### Example: nearest-neighbour alignment

- **GIVEN** ten_vad frames: `[(0, 0.9), (16, 0.8), (32, 0.7)]` (time_ms, prob)
- **GIVEN** silero_vad frames: `[(0, 0.85), (32, 0.75)]`
- **WHEN** alignment is computed
- **THEN** unified points include at minimum: `0 ms`, `16 ms`, `32 ms`
- **THEN** at `16 ms`: `ten_vad_prob=0.8`, `silero_vad_prob=0.85` (closest silero frame is at 0 ms, within 50 ms)


<!-- @trace
source: implement-vad-stage
updated: 2026-05-01
code:
  - src/talking_parrot/vad/ten_vad.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/vad/__init__.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/stages/chunking_stage.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/backend.py
  - tests/unit/vad/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/vad_stage.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/vad/test_backend.py
  - tests/unit/vad/test_silero_vad.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_backend.py
-->

---
### Requirement: VADStage computes composite score per frame using FormulaEvaluator

The system SHALL call `FormulaEvaluator.evaluate(formula, variables)` for each unified frame, where `variables` is `{f"{backend.name}_prob": aligned_prob, ...}` for all configured backends.

#### Scenario: composite score computed from formula

- **WHEN** `formula = "(ten_vad_prob * 0.9) + (silero_vad_prob * 0.1)"` and `ten_vad_prob=0.95`, `silero_vad_prob=0.82`
- **THEN** composite score equals `(0.95 * 0.9) + (0.82 * 0.1) = 0.937`

##### Example: composite score calculation

| formula                                          | ten_vad_prob | silero_vad_prob | expected composite_score |
|--------------------------------------------------|--------------|-----------------|--------------------------|
| `(ten_vad_prob + silero_vad_prob) / 2`           | 0.9          | 0.7             | 0.8                      |
| `(ten_vad_prob * 0.9) + (silero_vad_prob * 0.1)` | 0.95         | 0.82            | 0.937                    |
| `ten_vad_prob`                                   | 0.6          | 0.0             | 0.6                      |


<!-- @trace
source: implement-vad-stage
updated: 2026-05-01
code:
  - src/talking_parrot/vad/ten_vad.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/vad/__init__.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/stages/chunking_stage.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/backend.py
  - tests/unit/vad/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/vad_stage.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/vad/test_backend.py
  - tests/unit/vad/test_silero_vad.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_backend.py
-->

---
### Requirement: VADStage merges frames into segments using hysteresis thresholds

The system SHALL use a two-threshold state machine to merge frames into raw segments:
- Transition SILENCE → SPEECH when `composite_score >= activity_threshold`
- Transition SPEECH → SILENCE when `composite_score < neg_threshold`

`neg_threshold` SHALL be less than `activity_threshold` in valid configurations.

#### Scenario: segment starts when score crosses activity_threshold

- **WHEN** frames have composite scores `[0.3, 0.6, 0.8]` with `activity_threshold=0.5`
- **THEN** a segment starts at the frame with score `0.6`

#### Scenario: segment ends when score drops below neg_threshold

- **WHEN** frames have composite scores `[0.8, 0.7, 0.3]` with `neg_threshold=0.35`
- **THEN** the segment ends when score drops to `0.3`

#### Scenario: hysteresis prevents re-triggering between activity_threshold and neg_threshold

- **WHEN** frames have composite scores `[0.6, 0.4, 0.6]` with `activity_threshold=0.5`, `neg_threshold=0.35`
- **THEN** only one segment is produced (score 0.4 does not end the segment because 0.4 >= neg_threshold)


<!-- @trace
source: implement-vad-stage
updated: 2026-05-01
code:
  - src/talking_parrot/vad/ten_vad.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/vad/__init__.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/stages/chunking_stage.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/backend.py
  - tests/unit/vad/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/vad_stage.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/vad/test_backend.py
  - tests/unit/vad/test_silero_vad.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_backend.py
-->

---
### Requirement: VADStage applies post-merge refinement steps in order

After raw segment extraction, the system SHALL apply these steps in sequence:
1. **Gap merging**: merge adjacent segments whose silence gap is `< min_silence_duration_ms`
2. **Short-segment filtering**: discard segments shorter than `min_speech_duration_ms`
3. **Long-segment splitting**: split segments longer than `max_speech_duration_ms` at the midpoint
4. **Speech padding**: extend each segment's `start_ms` earlier and `end_ms` later by `speech_pad_ms`, clamped to `[0, audio_duration_ms]`

#### Scenario: short segments are discarded

- **WHEN** a raw segment has duration `100 ms` and `min_speech_duration_ms = 250`
- **THEN** the segment is not present in the output

#### Scenario: adjacent segments with small gap are merged

- **WHEN** segment A ends at `500 ms`, segment B starts at `550 ms`, and `min_silence_duration_ms = 100`
- **THEN** segments A and B are merged into one segment spanning A.start_ms to B.end_ms

#### Scenario: long segment is split at midpoint

- **WHEN** a segment spans `0 ms` to `40000 ms` and `max_speech_duration_ms = 30000`
- **THEN** two segments are produced: `[0, 20000]` and `[20000, 40000]`

#### Scenario: speech padding is applied and clamped

- **WHEN** a segment spans `10 ms` to `990 ms`, `speech_pad_ms = 30`, and `audio_duration_ms = 1000`
- **THEN** the padded segment spans `max(0, 10-30)=0 ms` to `min(1000, 990+30)=1000 ms`


<!-- @trace
source: implement-vad-stage
updated: 2026-05-01
code:
  - src/talking_parrot/vad/ten_vad.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/vad/__init__.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/stages/chunking_stage.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/backend.py
  - tests/unit/vad/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/vad_stage.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/vad/test_backend.py
  - tests/unit/vad/test_silero_vad.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_backend.py
-->

---
### Requirement: VADStage outputs VadSegment list with per-backend and composite statistics

Each output `VadSegment` SHALL contain:
- `start_ms`, `end_ms` (after all refinement steps)
- `ten_vad_prob`: mean of the aligned `ten_vad` probabilities across the segment's frames
- `silero_vad_prob`: mean of the aligned `silero_vad` probabilities across the segment's frames
- `composite_score`: mean of the composite scores across the segment's frames

#### Scenario: VadSegment statistics reflect frame averages

- **WHEN** a segment covers frames with `ten_vad_prob` values `[0.9, 0.8]` and `silero_vad_prob` values `[0.7, 0.6]` and composite scores `[0.85, 0.75]`
- **THEN** the segment has `ten_vad_prob=0.85`, `silero_vad_prob=0.65`, `composite_score=0.80`

<!-- @trace
source: implement-vad-stage
updated: 2026-05-01
code:
  - src/talking_parrot/vad/ten_vad.py
  - tests/unit/transcription/__init__.py
  - src/talking_parrot/vad/silero_vad.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/vad/__init__.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/stages/chunking_stage.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/__init__.py
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/vad/backend.py
  - tests/unit/vad/__init__.py
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/vad_stage.py
tests:
  - tests/unit/stages/test_chunking_stage.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/vad/test_ten_vad.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/vad/test_backend.py
  - tests/unit/vad/test_silero_vad.py
  - tests/unit/transcription/test_factory.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/config/test_models.py
  - tests/unit/transcription/test_backend.py
-->

---
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

<!-- @trace
source: vad-frames-per-backend
updated: 2026-05-09
code:
  - docs/planning/quality-and-tooling/adr-0002-mcp-streamable-http-default.md
  - docs/planning/quality-and-tooling/README.md
  - src/talking_parrot/cli.py
  - src/talking_parrot/models/context.py
  - tests/unit/gui/__init__.py
  - docs/planning/quality-and-tooling/01-regression-harness.md
  - src/talking_parrot/gui/__init__.py
  - docs/planning/quality-and-tooling/shared-architecture.md
  - src/talking_parrot/gui/static/index.html
  - src/talking_parrot/gui/cli.py
  - src/talking_parrot/shared/snapshot_loader.py
  - docs/planning/quality-and-tooling/adr-0001-gui-browser-spa.md
  - src/talking_parrot/stages/vad_stage.py
  - src/talking_parrot/gui/api.py
  - tests/unit/shared/__init__.py
  - docs/TODOs.md
  - tests/unit/gui/conftest.py
  - src/talking_parrot/gui/http_server.py
  - src/talking_parrot/vad/ten_vad.py
  - src/talking_parrot/vad/silero_vad.py
  - docs/planning/quality-and-tooling/03-mcp-server.md
  - docs/planning/quality-and-tooling/02-analysis-gui.md
  - src/talking_parrot/models/vad.py
  - src/talking_parrot/shared/project_snapshot.py
  - src/talking_parrot/shared/metrics.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/shared/__init__.py
tests:
  - tests/unit/gui/test_cli.py
  - tests/unit/gui/test_design_alignment.py
  - tests/unit/shared/test_snapshot_loader.py
  - tests/unit/gui/test_http_server_imports.py
  - tests/unit/vad/test_raw_vad_frame_backend.py
  - tests/unit/shared/test_project_snapshot.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/gui/test_http_server.py
  - tests/unit/gui/test_api.py
  - tests/unit/models/test_data_models.py
  - tests/unit/stages/test_vad_stage.py
  - tests/unit/vad/test_backend.py
  - tests/unit/shared/test_metrics.py
  - tests/unit/gui/test_dependency_direction.py
  - tests/unit/shared/test_public_api.py
-->