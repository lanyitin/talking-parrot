# subtitle-exporter Specification

## Purpose

TBD - created by archiving change 'implement-subtitle-export'. Update Purpose after archive.

## Requirements

### Requirement: SubtitleExporter abstract base class

The system SHALL provide an abstract class `SubtitleExporter` (in `src/talking_parrot/io/subtitle_export/base.py`) declaring two read-only properties `format_name: str` and `file_extension: str`, plus an abstract method `export(subtitles: list[Subtitle], output_path: str) -> None`. Direct instantiation of `SubtitleExporter` SHALL raise `TypeError`.

#### Scenario: Instantiating the ABC directly raises TypeError

- **GIVEN** the `SubtitleExporter` ABC
- **WHEN** code calls `SubtitleExporter()`
- **THEN** Python raises `TypeError` because `format_name`, `file_extension`, and `export` are abstract

#### Scenario: A concrete subclass overriding all abstract members is constructible

- **GIVEN** a subclass `_FakeExporter(SubtitleExporter)` that returns `"fake"` / `".fake"` from the properties and writes a fixed string in `export`
- **WHEN** `_FakeExporter()` is constructed
- **THEN** the instance is created without error and `isinstance(instance, SubtitleExporter)` is `True`


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
### Requirement: SubtitleExporter writes UTF-8 with no BOM

Every concrete `SubtitleExporter.export` implementation SHALL write the file contents encoded as UTF-8 without a byte-order mark. Line endings within the file SHALL be `\n` (LF), never `\r\n`.

#### Scenario: Output file is decodable as UTF-8 without BOM

- **GIVEN** any `SubtitleExporter` concrete instance and a list of subtitles containing non-ASCII characters (e.g. `"こんにちは"`)
- **WHEN** `exporter.export(subs, path)` writes the file
- **THEN** the first byte SHALL NOT be `0xEF` (no UTF-8 BOM), and the file decodes cleanly with `path.read_bytes().decode("utf-8")`


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
### Requirement: SubtitleExporter writes atomically

`SubtitleExporter.export` SHALL write to a temporary file alongside `output_path` (with suffix `.tmp`) and then atomically rename it to `output_path` via `os.replace`. If the process is interrupted before the rename, `output_path` SHALL be left in its prior state (either nonexistent or holding the previous version).

#### Scenario: A failure during write does not leave a half-written output_path

- **GIVEN** a concrete exporter whose write step is patched to raise `IOError` after creating the `.tmp` file
- **WHEN** `exporter.export(subs, path)` is called
- **THEN** `IOError` propagates and `path` does NOT exist (or retains its prior contents); only the `.tmp` file may remain


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
### Requirement: SubtitleExporter handles empty subtitle input

`SubtitleExporter.export` SHALL accept an empty `subtitles` list. The exact byte content for the empty case is format-specific (see `srt-exporter` and `webvtt-exporter`), but the call SHALL NOT raise.

#### Scenario: Empty input does not raise

- **GIVEN** any concrete `SubtitleExporter` instance and `subtitles == []`
- **WHEN** `exporter.export([], path)` is called
- **THEN** the call returns `None` without raising and `path` exists on disk

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