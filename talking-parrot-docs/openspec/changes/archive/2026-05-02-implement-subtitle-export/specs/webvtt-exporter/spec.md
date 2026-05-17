## ADDED Requirements

### Requirement: WebVTTExporter exposes format_name and file_extension

`WebVTTExporter` SHALL be a concrete subclass of `SubtitleExporter` (in `src/talking_parrot/io/subtitle_export/webvtt.py`) returning `"webvtt"` from `format_name` and `".vtt"` from `file_extension`.

#### Scenario: Properties report WebVTT identity

- **GIVEN** a `WebVTTExporter` instance
- **WHEN** `exporter.format_name` and `exporter.file_extension` are read
- **THEN** they return the strings `"webvtt"` and `".vtt"` respectively

### Requirement: WebVTTExporter writes the WEBVTT header followed by cues

The output file SHALL begin with the literal byte sequence `WEBVTT\n\n` (header line followed by a blank line). For each `Subtitle s` in input order, `WebVTTExporter.export` SHALL emit a cue block consisting of:

1. A line containing `{HH:MM:SS.mmm of s.start_ms} --> {HH:MM:SS.mmm of s.end_ms}` (timecode uses period `.` as the decimal separator, two-digit hours / minutes / seconds, three-digit milliseconds, all zero-padded)
2. The cue text `s.text` written verbatim (no escaping, no trimming, internal `\n` preserved)

Cue blocks SHALL be separated by exactly one blank line. No per-cue index identifier SHALL be written. The file SHALL end with a single trailing `\n` after the last cue's text. Line endings SHALL be `\n`.

#### Scenario: Two cues produce the canonical WebVTT layout

- **GIVEN** subtitles `[Subtitle(1, 0, 1500, "hello"), Subtitle(2, 1500, 3000, "world")]`
- **WHEN** `WebVTTExporter().export(subs, path)` is called
- **THEN** the file content is exactly `"WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nhello\n\n00:00:01.500 --> 00:00:03.000\nworld\n"`

#### Scenario: Hour-spanning timestamps use period decimal separator

- **GIVEN** a subtitle `Subtitle(1, 3_661_005, 3_662_500, "x")`
- **WHEN** the exporter writes the file
- **THEN** the timecode line reads `01:01:01.005 --> 01:01:02.500`

### Requirement: WebVTTExporter emits header-only file for empty input

When `subtitles == []`, `WebVTTExporter.export` SHALL write exactly the byte sequence `"WEBVTT\n\n"` to `output_path` and nothing else.

#### Scenario: Empty input produces a header-only WebVTT file

- **GIVEN** a `WebVTTExporter` and an empty subtitle list
- **WHEN** `exporter.export([], path)` is called
- **THEN** the file content is exactly `"WEBVTT\n\n"` and `path.stat().st_size == 8`
