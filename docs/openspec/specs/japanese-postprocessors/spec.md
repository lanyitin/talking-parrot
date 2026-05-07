# japanese-postprocessors Specification

## Purpose

TBD - created by archiving change 'segment-level-postprocessing-pipeline'. Update Purpose after archive.

## Requirements

### Requirement: JapaneseFillerProcessor strips leading filler words

The system SHALL provide `JapaneseFillerProcessor(SubtitleProcessor)` (in `src/talking_parrot/post_processing/japanese.py`). When `process(subtitles, config)` is called and `config.japanese_filler_enabled is True`, for each `Subtitle` the processor SHALL remove a leading filler token if the cue's `text` (after stripping leading whitespace) starts with any token from the configured filler list (default: `あの`, `あのー`, `えっと`, `えーと`, `えー`, `まあ`, `そのー`, `その`, `なんか`, `ね`).

The processor MUST NOT modify `start_ms`, `end_ms`, or `index`. It SHALL only modify `text`. After filler removal, leading whitespace SHALL be stripped.

If a cue's `text` becomes empty (whitespace-only) after filler removal, the processor SHALL drop that cue. After any drops, the returned list SHALL be renumbered 1-based.

When `config.japanese_filler_enabled is False`, the processor SHALL return the input list unchanged.

#### Scenario: Leading filler removed, timing preserved

- **GIVEN** a `Subtitle(text="あのー、こんにちは", start_ms=1000, end_ms=2000, index=1)` with default config
- **WHEN** the processor runs
- **THEN** the returned list MUST contain a single `Subtitle(text="こんにちは", start_ms=1000, end_ms=2000, index=1)`

#### Scenario: Cue dropped when only filler remains

- **GIVEN** a `Subtitle(text="えっと", start_ms=1000, end_ms=1500, index=1)` followed by a kept cue
- **WHEN** the processor runs with default config
- **THEN** the returned list MUST omit the filler-only cue and renumber survivors starting at 1

#### Scenario: Disabled processor returns input unchanged

- **GIVEN** `config.japanese_filler_enabled is False`
- **WHEN** the processor runs
- **THEN** every output `Subtitle` MUST be equal to its input counterpart


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
### Requirement: JapaneseRepetitionProcessor caps consecutive character repetitions at two

The system SHALL provide `JapaneseRepetitionProcessor(SubtitleProcessor)` (in `src/talking_parrot/post_processing/japanese.py`). When `process(subtitles, config)` is called and `config.japanese_repetition_enabled is True`, for each `Subtitle` the processor SHALL collapse any run of three or more identical adjacent characters in `text` to exactly two characters, **except** that runs whose underlying two-character cycle appears in the configured onomatopoeia whitelist (default: `どきどき`, `わくわく`, `きらきら`, `ぴかぴか`) MUST NOT be collapsed.

The processor MUST NOT modify `start_ms`, `end_ms`, or `index`. It SHALL only modify `text`. If `text` becomes empty (whitespace-only) after collapse, the processor SHALL drop that cue and renumber survivors 1-based.

When `config.japanese_repetition_enabled is False`, the processor SHALL return the input list unchanged.

#### Scenario: Three or more repeats collapsed to two

- **GIVEN** a `Subtitle(text="あああああ", start_ms=1000, end_ms=1500, index=1)`
- **WHEN** the processor runs with default config
- **THEN** the returned list MUST contain `Subtitle(text="ああ", start_ms=1000, end_ms=1500, index=1)`

#### Scenario: Onomatopoeia preserved

- **GIVEN** a `Subtitle(text="どきどきどき", ...)` and `"どきどき"` in the whitelist
- **WHEN** the processor runs
- **THEN** the cue's `text` MUST remain `"どきどきどき"` unchanged

#### Scenario: Disabled processor returns input unchanged

- **GIVEN** `config.japanese_repetition_enabled is False`
- **WHEN** the processor runs
- **THEN** every output `Subtitle` MUST be equal to its input counterpart

##### Example: repetition collapse decision table

| input text       | whitelist contains | output text   | dropped? |
| ---------------- | ------------------- | ------------- | -------- |
| `"あああああ"`    | (any)               | `"ああ"`      | no       |
| `"わわわ"`       | (default)           | `"わわ"`      | no       |
| `"どきどきどき"`  | `"どきどき"`         | `"どきどきどき"` | no       |
| `"〜〜〜"`       | (default)           | `"〜〜"`      | no       |

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