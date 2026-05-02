# srt-exporter Specification

## Purpose

TBD - created by archiving change 'implement-subtitle-export'. Update Purpose after archive.

## Requirements

### Requirement: SRTExporter exposes format_name and file_extension

`SRTExporter` SHALL be a concrete subclass of `SubtitleExporter` (in `src/talking_parrot/io/subtitle_export/srt.py`) returning `"srt"` from `format_name` and `".srt"` from `file_extension`.

#### Scenario: Properties report SRT identity

- **GIVEN** an `SRTExporter` instance
- **WHEN** `exporter.format_name` and `exporter.file_extension` are read
- **THEN** they return the strings `"srt"` and `".srt"` respectively


<!-- @trace
source: implement-subtitle-export
updated: 2026-05-02
code:
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/stages/post_processing_stage.py
  - tests/unit/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/__init__.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/cli.py
  - tests/unit/post_processing/__init__.py
tests:
  - tests/unit/config/test_export_config.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/stages/test_post_processing_stage.py
-->

---
### Requirement: SRTExporter serializes cues using SubRip syntax

For each `Subtitle s` in `subtitles` (in input order), `SRTExporter.export` SHALL emit a cue block consisting of:

1. A line containing `s.index` as a decimal integer
2. A line containing `{HH:MM:SS,mmm of s.start_ms} --> {HH:MM:SS,mmm of s.end_ms}` (timecode uses comma `,` as the decimal separator, two-digit hours / minutes / seconds, three-digit milliseconds, all zero-padded)
3. The cue text `s.text` written verbatim (no escaping, no trimming, internal `\n` preserved)

Cue blocks SHALL be separated by exactly one blank line. The file SHALL end with a single trailing `\n` after the last cue's text (no extra trailing blank line). Line endings SHALL be `\n`.

#### Scenario: Two cues produce the canonical SRT layout

- **GIVEN** subtitles `[Subtitle(1, 0, 1500, "hello"), Subtitle(2, 1500, 3000, "world")]`
- **WHEN** `SRTExporter().export(subs, path)` is called
- **THEN** the file content is exactly `"1\n00:00:00,000 --> 00:00:01,500\nhello\n\n2\n00:00:01,500 --> 00:00:03,000\nworld\n"`

#### Scenario: A cue with multi-line text preserves internal newlines

- **GIVEN** a subtitle `Subtitle(1, 0, 1000, "line one\nline two")`
- **WHEN** the exporter writes the file
- **THEN** the file contains `"1\n00:00:00,000 --> 00:00:01,000\nline one\nline two\n"`

#### Scenario: Hour-spanning timestamps are zero-padded correctly

- **GIVEN** a subtitle `Subtitle(1, 3_661_005, 3_662_500, "x")` (1h 01m 01.005s start)
- **WHEN** the exporter writes the file
- **THEN** the timecode line reads `01:01:01,005 --> 01:01:02,500`


<!-- @trace
source: implement-subtitle-export
updated: 2026-05-02
code:
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/stages/post_processing_stage.py
  - tests/unit/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/__init__.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/cli.py
  - tests/unit/post_processing/__init__.py
tests:
  - tests/unit/config/test_export_config.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/stages/test_post_processing_stage.py
-->

---
### Requirement: SRTExporter emits a zero-byte file for empty input

When `subtitles == []`, `SRTExporter.export` SHALL create `output_path` with zero bytes of content.

#### Scenario: Empty input produces a zero-byte file

- **GIVEN** an `SRTExporter` and an empty subtitle list
- **WHEN** `exporter.export([], path)` is called
- **THEN** `path` exists and `path.stat().st_size == 0`

<!-- @trace
source: implement-subtitle-export
updated: 2026-05-02
code:
  - src/talking_parrot/io/subtitle_export/webvtt.py
  - src/talking_parrot/post_processing/base.py
  - src/talking_parrot/post_processing/time_based.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/stages/post_processing_stage.py
  - tests/unit/io/subtitle_export/__init__.py
  - docs/TODOs.md
  - src/talking_parrot/post_processing/__init__.py
  - src/talking_parrot/io/subtitle_export/base.py
  - src/talking_parrot/stages/__init__.py
  - tests/unit/cli/__init__.py
  - src/talking_parrot/post_processing/word_boundary.py
  - src/talking_parrot/io/subtitle_export/factory.py
  - src/talking_parrot/io/subtitle_export/__init__.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/io/subtitle_export/srt.py
  - src/talking_parrot/cli.py
  - tests/unit/post_processing/__init__.py
tests:
  - tests/unit/config/test_export_config.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/io/subtitle_export/test_factory.py
  - tests/unit/io/subtitle_export/test_webvtt.py
  - tests/unit/io/subtitle_export/test_base.py
  - tests/unit/post_processing/test_base.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/io/subtitle_export/test_srt.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_word_boundary.py
  - tests/unit/stages/test_post_processing_stage.py
-->