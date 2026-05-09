## ADDED Requirements

### Requirement: Each tool is a separate decorated function (ISP)

The system SHALL register each MCP tool as its own `@mcp.tool()`-decorated function. No tool function SHALL bundle multiple unrelated responsibilities, and no fat dispatcher SHALL stand in for individual tool registration.

#### Scenario: Tool catalogue contains seven distinct tools

- **WHEN** the MCP server is started
- **THEN** exactly the following tools SHALL be registered: `summary`, `get_vad_segments`, `get_vad_frames`, `get_subtitles`, `get_pre_postprocess_subtitles`, `get_transcription_results`, `diagnostics`
- **AND** each tool SHALL be implemented as a distinct decorated function

### Requirement: Tools depend on `ProjectSnapshot`, not on filesystem paths (DIP)

Each tool function SHALL delegate its work to a pure helper that takes `ProjectSnapshot` plus the tool's parameters and returns the response value. Helpers SHALL NOT read from the filesystem, network, or any global mutable state.

#### Scenario: Helper is unit-testable without FastMCP

- **WHEN** a test constructs a fixture `ProjectSnapshot` and calls a tool helper directly
- **THEN** the helper SHALL return the expected dict
- **AND** the test SHALL NOT require the `mcp` package to be installed

### Requirement: `summary` returns aggregate counts and audio duration

The `summary` tool SHALL return aggregate counts derived from the snapshot, including at least `n_vad_segments`, `n_vad_frames`, `n_chunks`, `n_transcription_results`, `n_subtitles`, `n_pre_postprocess_subtitles`, and `audio_duration_ms`.

#### Scenario: Summary over a populated snapshot

- **WHEN** `summary()` is invoked against a snapshot containing 12 VAD segments and 30 subtitles
- **THEN** the response SHALL include `n_vad_segments == 12` and `n_subtitles == 30`
- **AND** the response SHALL include `audio_duration_ms` matching `snapshot.audio_info.duration_ms`

### Requirement: Time-range tools accept optional millisecond bounds

The `get_vad_segments`, `get_vad_frames`, `get_subtitles`, and `get_pre_postprocess_subtitles` tools SHALL accept optional integer parameters `start_ms` and `end_ms` in milliseconds. When both are absent, the full collection SHALL be returned. When provided, items overlapping the inclusive range `[start_ms, end_ms]` SHALL be returned. Each tool's docstring SHALL state milliseconds explicitly.

#### Scenario: No bounds returns full collection

- **WHEN** `get_subtitles()` is invoked with no arguments
- **THEN** the response SHALL contain every subtitle in the snapshot

#### Scenario: Bounded range returns overlap only

- **WHEN** `get_vad_segments(start_ms=1000, end_ms=2000)` is invoked
- **THEN** the response SHALL include only segments whose `[start_ms, end_ms]` intersects `[1000, 2000]`

### Requirement: `get_transcription_results` filters by chunk index

The `get_transcription_results` tool SHALL accept an optional integer `chunk_index`. When absent, all transcription results SHALL be returned. When provided, only the result for that chunk SHALL be returned, or an empty list if no such chunk exists.

#### Scenario: Filter to a specific chunk

- **WHEN** `get_transcription_results(chunk_index=3)` is invoked
- **THEN** the response SHALL contain only the transcription result whose `chunk_index == 3`

#### Scenario: Unknown chunk index yields empty list

- **WHEN** `get_transcription_results(chunk_index=999)` is invoked against a snapshot with three chunks
- **THEN** the response SHALL be an empty list

### Requirement: `diagnostics` is derived purely from the snapshot

The `diagnostics` tool SHALL compute low-confidence cues, repetition flags, and no-speech flags entirely from `ProjectSnapshot.transcription_results` and `ProjectSnapshot.subtitles`. The tool SHALL NOT perform I/O and SHALL NOT call external services. Thresholds SHALL be read from `snapshot.config_snapshot` when present and SHALL fall back to documented defaults otherwise.

#### Scenario: Diagnostics surfaces low-confidence cues

- **WHEN** the snapshot contains a transcription result whose `avg_logprob` is below the threshold
- **THEN** `diagnostics()` SHALL include that cue in the low-confidence list with a reason field naming `avg_logprob`

#### Scenario: Diagnostics never reads from disk

- **WHEN** `diagnostics()` is invoked
- **THEN** no filesystem read SHALL occur during the call
