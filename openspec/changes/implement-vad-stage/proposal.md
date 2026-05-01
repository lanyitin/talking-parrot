## Why

The pipeline requires a Voice Activity Detection (VAD) stage to identify speech segments in audio before chunking and transcription. Without it, downstream stages receive no time boundaries and cannot operate correctly.

## What Changes

- Introduce `VADBackend` abstract interface with `analyze()` returning `List[RawVadFrame]`
- Implement `TenVADBackend` and `SileroVADBackend` as concrete backends
- Implement `VADStage` that coordinates backends, applies `FormulaEvaluator` for composite scoring, and outputs `VadSegment` list
- Update `VadSegment` model to match the architecture spec (`ten_vad_prob`, `silero_vad_prob`, `composite_score` replacing `confidence`)
- Add `RawVadFrame` model
- Update `VadConfig` to include `formula` and `neg_threshold` fields (currently missing)

## Capabilities

### New Capabilities

- `vad-backend`: Abstract `VADBackend` interface and `RawVadFrame` model
- `ten-vad-backend`: `TenVADBackend` — wraps TEN VAD library to produce per-frame speech probabilities
- `silero-vad-backend`: `SileroVADBackend` — wraps Silero VAD model to produce per-frame speech probabilities
- `vad-stage`: `VADStage` — coordinates backends, computes composite score via `FormulaEvaluator`, segments audio into `VadSegment` list

### Modified Capabilities

(none)

## Impact

- Affected code:
  - New: `src/talking_parrot/vad/__init__.py`
  - New: `src/talking_parrot/vad/backend.py`
  - New: `src/talking_parrot/vad/ten_vad.py`
  - New: `src/talking_parrot/vad/silero_vad.py`
  - New: `src/talking_parrot/stages/vad_stage.py`
  - New: `tests/unit/vad/__init__.py`
  - New: `tests/unit/vad/test_backend.py`
  - New: `tests/unit/vad/test_ten_vad.py`
  - New: `tests/unit/vad/test_silero_vad.py`
  - New: `tests/unit/stages/__init__.py`
  - New: `tests/unit/stages/test_vad_stage.py`
  - Modified: `src/talking_parrot/models/vad.py`
  - Modified: `src/talking_parrot/config/models.py`
