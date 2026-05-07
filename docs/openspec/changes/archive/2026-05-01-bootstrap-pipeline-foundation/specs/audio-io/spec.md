## ADDED Requirements

### Requirement: AudioReader interface for lazy interval reads

The system SHALL provide an `AudioReader` interface that exposes a read-only `sample_rate: int` property and a method `read(start_ms: int, end_ms: int) -> bytes` returning PCM audio bytes for the requested interval. An `AudioReader` instance is bound at construction time to a single media file path.

#### Scenario: Interval read returns PCM bytes

- **WHEN** `reader.read(1000, 2000)` is called on a reader bound to a 60-second media file
- **THEN** the method MUST return a `bytes` object containing exactly 1 second of PCM data at `reader.sample_rate`

#### Scenario: Out-of-range request raises

- **WHEN** `reader.read(start_ms, end_ms)` is called with `end_ms > media_duration_ms` or `start_ms < 0` or `start_ms >= end_ms`
- **THEN** the method MUST raise `ValueError`

### Requirement: Default AudioReader implementation uses ffmpeg with LRU cache

The system SHALL provide a default implementation `FfmpegAudioReader` that decodes via ffmpeg and caches the most recent N decoded intervals using an LRU policy. The cache size SHALL default to 4 and SHALL be configurable via the `AUDIO_CACHE_SIZE` environment variable.

#### Scenario: Repeated read uses cache

- **WHEN** `reader.read(1000, 2000)` is called twice in succession on the same `FfmpegAudioReader`
- **THEN** the underlying ffmpeg decode MUST execute only once

### Requirement: MediaHasher computes SHA-256

The system SHALL provide a `MediaHasher.hash(path: str) -> str` method that returns the SHA-256 hex digest of the file at `path`. The implementation MUST stream the file in chunks (not load it entirely into memory) to support large media files.

#### Scenario: Same content yields same hash

- **WHEN** `MediaHasher.hash()` is invoked twice on identical file contents at different paths
- **THEN** both calls MUST return the same 64-character lowercase hex string

### Requirement: ProjectFileWriter serializes ProjectFile to JSON

The system SHALL provide a `ProjectFileWriter.write(project_file: ProjectFile, output_path: str) -> None` method that serializes the `ProjectFile` to JSON and writes it to `output_path`. Enums SHALL be serialized by name (not by integer value). Datetime strings SHALL be in ISO 8601 format.

#### Scenario: Enum serialised by name

- **WHEN** a `ProjectFile` with `config.align.granularity = GranularityPreference.AUTO` is written
- **THEN** the resulting JSON MUST contain the literal string `"AUTO"` (not `2` or another integer)

#### Scenario: Output is valid JSON

- **WHEN** any `ProjectFile` is written to disk
- **THEN** the resulting file MUST be parseable by `json.loads()` without error
