# hallucination-filter-stage Specification

## Purpose

TBD - created by archiving change 'segment-level-postprocessing-pipeline'. Update Purpose after archive.

## Requirements

### Requirement: HallucinationFilterStage exists as a pipeline stage

The system SHALL provide `HallucinationFilterStage(PipelineStage)` constructed with a single argument `(config: HallucinationFilterConfig)`. Its `name` property SHALL return the literal string `"hallucination_filter"`. The stage MUST NOT mutate the input `PipelineContext`; it MUST return a new context via `dataclasses.replace`.

#### Scenario: Stage exposes correct name and shape

- **WHEN** an instance is constructed with a default `HallucinationFilterConfig`
- **THEN** `stage.name` MUST equal `"hallucination_filter"`
- **AND** calling `stage.process(ctx)` with any `PipelineContext` MUST return a `PipelineContext` distinct from the input (different object identity)


<!-- @trace
source: segment-level-postprocessing-pipeline
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - sample1.srt
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/post_processing/japanese.py
  - sample1.json
  - src/talking_parrot/config/models.py
  - src/talking_parrot/logging_config.py
  - CLAUDE.md
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/dedup.py
tests:
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/config/test_loader.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/post_processing/test_dedup.py
-->

---
### Requirement: HallucinationFilterStage filters TranscriptionResult entries by configured rules

When `enabled` is `True`, the stage SHALL drop any `TranscriptionResult` whose `text` or `metrics` matches at least one of the configured rules below. The stage SHALL preserve the relative order of surviving results. Each rule is independently toggleable via the corresponding `HallucinationFilterConfig` field; a disabled rule MUST NOT cause a drop.

Rules (each evaluated against a single `TranscriptionResult`):

1. **Exact-phrase match**: `result.text.strip()` exactly equals any phrase in the configured `known_hallucination_phrases` list.
2. **Bracketed-text only**: `result.text.strip()` matches the regex `^[\[\(（【][^\]\)）】]*[\]\)）】]$` (i.e. the entire text is wrapped in ASCII or full-width brackets).
3. **Long character repetition**: `result.text` contains five or more consecutive identical non-whitespace characters (regex `(\S)\1{4,}`).
4. **Low logprob with high no-speech probability**: `result.metrics.avg_logprob < min_avg_logprob` AND `result.metrics.no_speech_prob > max_no_speech_prob`.
5. **High compression ratio**: `result.metrics.compression_ratio > max_compression_ratio`.
6. **High repetition ratio**: `result.metrics.repetition_ratio > max_repetition_ratio`.

When `enabled` is `False`, the stage SHALL return the input context with `transcription_results` unchanged.

#### Scenario: Bracket-only text dropped

- **GIVEN** a `TranscriptionResult` with `text == "[音楽]"` and an enabled bracket rule
- **WHEN** the stage processes the context
- **THEN** the returned `transcription_results` MUST NOT contain that result

#### Scenario: Order preserved across drops

- **GIVEN** four results A (kept), B (drop: bracket), C (kept), D (drop: long repeat)
- **WHEN** the stage processes the context
- **THEN** the returned `transcription_results` MUST equal `[A, C]` in that order

#### Scenario: Disabled stage returns input unchanged

- **GIVEN** `HallucinationFilterConfig.enabled is False`
- **WHEN** the stage processes any context
- **THEN** the returned context's `transcription_results` MUST be reference-equal to the input's

##### Example: threshold table

| `avg_logprob` | `no_speech_prob` | `compression_ratio` | `repetition_ratio` | Rule fired                            | Dropped? |
| ------------- | ---------------- | ------------------- | ------------------ | ------------------------------------- | -------- |
| -0.3          | 0.1              | 1.6                 | 0.05               | (none)                                | no       |
| -1.5          | 0.7              | 1.8                 | 0.05               | low-logprob + high-no-speech          | yes      |
| -0.3          | 0.1              | 3.5                 | 0.05               | high compression                      | yes      |
| -0.3          | 0.1              | 1.6                 | 0.6                | high repetition                       | yes      |

(Threshold defaults: `min_avg_logprob = -1.0`, `max_no_speech_prob = 0.6`, `max_compression_ratio = 2.4`, `max_repetition_ratio = 0.5`.)


<!-- @trace
source: segment-level-postprocessing-pipeline
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - sample1.srt
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/post_processing/japanese.py
  - sample1.json
  - src/talking_parrot/config/models.py
  - src/talking_parrot/logging_config.py
  - CLAUDE.md
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/dedup.py
tests:
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/config/test_loader.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/post_processing/test_dedup.py
-->

---
### Requirement: HallucinationFilterStage logs filter activity

For every `process()` invocation when `enabled is True`, the stage SHALL emit one INFO-level log line containing the field names `before` (input result count), `after` (output result count), and `dropped` (count of removed results). The stage MAY emit DEBUG-level entries identifying the rule that matched per dropped result; if emitted, each entry MUST include the `chunk_index` and the rule name (one of `"phrase"`, `"bracket"`, `"repeat"`, `"low_logprob"`, `"compression"`, `"repetition"`).

#### Scenario: Summary log emitted

- **GIVEN** a context with 5 results, of which 2 are dropped
- **WHEN** the stage runs with default config
- **THEN** at least one INFO log entry MUST be emitted with `before=5`, `after=3`, `dropped=2`

<!-- @trace
source: segment-level-postprocessing-pipeline
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - sample1.srt
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/post_processing/japanese.py
  - sample1.json
  - src/talking_parrot/config/models.py
  - src/talking_parrot/logging_config.py
  - CLAUDE.md
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/dedup.py
tests:
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/config/test_loader.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/post_processing/test_dedup.py
-->