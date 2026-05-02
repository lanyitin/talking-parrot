## ADDED Requirements

### Requirement: SRTExporter exposes format_name and file_extension

`SRTExporter` SHALL be a concrete subclass of `SubtitleExporter` (in `src/talking_parrot/io/subtitle_export/srt.py`) returning `"srt"` from `format_name` and `".srt"` from `file_extension`.

#### Scenario: Properties report SRT identity

- **GIVEN** an `SRTExporter` instance
- **WHEN** `exporter.format_name` and `exporter.file_extension` are read
- **THEN** they return the strings `"srt"` and `".srt"` respectively

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

### Requirement: SRTExporter emits a zero-byte file for empty input

When `subtitles == []`, `SRTExporter.export` SHALL create `output_path` with zero bytes of content.

#### Scenario: Empty input produces a zero-byte file

- **GIVEN** an `SRTExporter` and an empty subtitle list
- **WHEN** `exporter.export([], path)` is called
- **THEN** `path` exists and `path.stat().st_size == 0`
