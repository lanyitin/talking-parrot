# transcription-stage Specification

## Purpose

TBD - created by archiving change 'implement-transcription-stage'. Update Purpose after archive.

## Requirements

### Requirement: TranscriptionStage produces one TranscriptionResult per Chunk

The system SHALL provide `TranscriptionStage(PipelineStage)` constructed with `(factory: TranscriptionBackendFactory, evaluator: ConditionEvaluator)`. Its `name` property SHALL return `"transcription"`. Its `process(ctx)` method SHALL append exactly one `TranscriptionResult` to `ctx.transcription_results` for every `Chunk` in `ctx.chunks`, in the same order, with `chunk_index` matching the chunk's `index`.

The stage MUST return a new `PipelineContext` via `dataclasses.replace`; it MUST NOT mutate the input context.

#### Scenario: One result per chunk in input order

- **GIVEN** `ctx.chunks` with `index=[0, 1, 2]`
- **WHEN** `TranscriptionStage.process(ctx)` is called
- **THEN** the returned `ctx.transcription_results` MUST have length `3` with `chunk_index` values `[0, 1, 2]` in that order

#### Scenario: Empty chunks short-circuits

- **GIVEN** `ctx.chunks == []`
- **WHEN** `TranscriptionStage.process(ctx)` is called
- **THEN** the returned context MUST equal the input context (no `transcription_results` appended) and the factory MUST NOT be consulted


<!-- @trace
source: implement-transcription-stage
updated: 2026-05-01
code:
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/transcription_stage.py
  - tests/unit/transcription/__init__.py
tests:
  - tests/unit/transcription/test_factory.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
-->

---
### Requirement: TranscriptionStage drives a cascade across transcribing[] steps

For each `Chunk`, `TranscriptionStage` SHALL iterate `ctx.config.transcribing` in declared order. For each step it SHALL call `evaluator.evaluate(step.condition, latest_metrics)`. When the result is truthy, the stage MUST resolve `backend = factory.create(step.backend)` and call `backend.transcribe(media_path, chunk, step.model, step.language or ctx.config.expected_language)`, replacing the chunk's running result and updating `latest_metrics` from `result.metrics`. When the result is falsy, the stage MUST stop iterating steps for the current chunk and keep the prior step's result.

Each step MUST execute at most once per chunk. After all steps are processed, the running result is the chunk's final `TranscriptionResult`.

#### Scenario: Step 0 always runs with empty metrics

- **GIVEN** `ctx.config.transcribing[0].condition == "true"` (enforced by `pipeline-config`)
- **WHEN** the stage processes any chunk
- **THEN** the evaluator MUST be called with `expression="true"` and `variables={}` for step 0

#### Scenario: Cascade halts on falsy condition

- **GIVEN** three transcribing steps and step 1's condition evaluates `False` against step 0's metrics
- **WHEN** the stage processes a chunk
- **THEN** step 0's backend MUST have been called once, step 1's backend MUST NOT have been called, step 2's evaluator MUST NOT have been invoked, and the chunk's final result MUST equal step 0's result

#### Scenario: Cascade upgrades on truthy condition

- **GIVEN** two steps where step 1's condition evaluates `True` against step 0's metrics
- **WHEN** the stage processes a chunk
- **THEN** both backends MUST have been called once and the chunk's final result MUST equal step 1's result

##### Example: cascade decision table

- **GIVEN** the transcribing list:
  | Step | condition                  | backend          | model     |
  |------|----------------------------|------------------|-----------|
  | 0    | `"true"`                   | `faster-whisper` | `base`    |
  | 1    | `"avg_logprob < -1.0"`     | `faster-whisper` | `medium`  |
  | 2    | `"repetition_ratio > 0.4"` | `faster-whisper` | `large-v3`|
- **WHEN** step 0 produces metrics `avg_logprob=-1.5, repetition_ratio=0.2` and step 1 produces metrics `avg_logprob=-0.5, repetition_ratio=0.1`
- **THEN** the cascade MUST execute steps 0 and 1, MUST skip step 2 (repetition_ratio 0.1 < 0.4), and the final result MUST be step 1's result


<!-- @trace
source: implement-transcription-stage
updated: 2026-05-01
code:
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/transcription_stage.py
  - tests/unit/transcription/__init__.py
tests:
  - tests/unit/transcription/test_factory.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
-->

---
### Requirement: TranscriptionStage exposes only TranscriptionMetrics fields to ConditionEvaluator

When evaluating any step's condition (other than step 0 which uses an empty dict), `TranscriptionStage` SHALL pass exactly the four metric fields from the latest `TranscriptionResult.metrics` as the variables dict: `avg_logprob`, `compression_ratio`, `no_speech_prob`, `repetition_ratio`.

The stage MUST NOT expose chunk timestamps, segment counts, model names, or any other state to the evaluator.

#### Scenario: Variable dict shape

- **WHEN** evaluator is invoked for step `N>0`
- **THEN** the variables dict MUST contain exactly the keys `{"avg_logprob", "compression_ratio", "no_speech_prob", "repetition_ratio"}` and no others


<!-- @trace
source: implement-transcription-stage
updated: 2026-05-01
code:
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/transcription_stage.py
  - tests/unit/transcription/__init__.py
tests:
  - tests/unit/transcription/test_factory.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
-->

---
### Requirement: TranscriptionStage falls back to prior result on backend failure for steps after step 0

If `backend.transcribe(...)` raises any exception while processing step `N>=1`, `TranscriptionStage` SHALL log a `WARNING`-level message identifying step index, backend name, model, and exception type, then keep the prior step's running result and stop the cascade for the current chunk. Step 0 failures MUST propagate unchanged (there is no prior result to fall back to).

#### Scenario: Step 1 backend failure preserves step 0 result

- **GIVEN** two steps where step 1's condition evaluates `True` and step 1's backend raises `RuntimeError`
- **WHEN** the stage processes a chunk
- **THEN** the chunk's final result MUST equal step 0's result and a `WARNING` log entry MUST have been emitted naming step index `1`

#### Scenario: Step 0 backend failure propagates

- **GIVEN** step 0's backend raises `ImportError`
- **WHEN** the stage processes a chunk
- **THEN** `process()` MUST raise the same `ImportError`

<!-- @trace
source: implement-transcription-stage
updated: 2026-05-01
code:
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/stages/__init__.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/factory.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - docs/TODOs.md
  - src/talking_parrot/transcription/__init__.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/stages/transcription_stage.py
  - tests/unit/transcription/__init__.py
tests:
  - tests/unit/transcription/test_factory.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
-->