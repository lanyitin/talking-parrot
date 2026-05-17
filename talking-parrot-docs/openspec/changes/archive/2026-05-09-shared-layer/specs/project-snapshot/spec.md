## ADDED Requirements

### Requirement: ProjectSnapshot frozen aggregate

The system SHALL provide a frozen dataclass `ProjectSnapshot` in `src/talking_parrot/shared/project_snapshot.py` containing the following fields: `version: str`, `created_at: str`, `source_path: str`, `config_snapshot: dict`, `audio_info: AudioInfo`, `vad_frames: list[RawVadFrame]`, `vad_segments: list[VadSegment]`, `chunks: list[Chunk]`, `transcription_results: list[TranscriptionResult]`, `pre_postprocess_subtitles: list[Subtitle]`, `subtitles: list[Subtitle]`. List fields MUST default to empty lists when not supplied. The dataclass MUST be declared with `frozen=True`.

#### Scenario: Default initialization with required fields

- **WHEN** `ProjectSnapshot(version="1", created_at="2026-05-09T00:00:00Z", source_path="/x/y.tp", config_snapshot={}, audio_info=ai)` is constructed
- **THEN** `vad_frames`, `vad_segments`, `chunks`, `transcription_results`, `pre_postprocess_subtitles`, and `subtitles` MUST each equal `[]`

#### Scenario: Mutation rejected

- **WHEN** code attempts `snapshot.subtitles = []` after construction
- **THEN** the system MUST raise `dataclasses.FrozenInstanceError`

### Requirement: ProjectSnapshot reuses existing pipeline value objects

The system SHALL import `RawVadFrame`, `VadSegment`, `Chunk`, `TranscriptionResult`, and `Subtitle` from `src/talking_parrot/models/` rather than redefining them. The shared layer MUST NOT introduce duplicate definitions of these types.

#### Scenario: Type identity is preserved

- **WHEN** a `Subtitle` instance constructed via `talking_parrot.models.subtitle.Subtitle` is placed into `ProjectSnapshot.subtitles`
- **THEN** `isinstance(snapshot.subtitles[0], talking_parrot.models.subtitle.Subtitle)` MUST be `True`

### Requirement: AudioInfo value object

The system SHALL provide a frozen dataclass `AudioInfo` with fields `sample_rate: int`, `duration_ms: int`, `rms_mean: float`, `rms_peak: float`. `AudioInfo` MUST live in `src/talking_parrot/shared/project_snapshot.py` (or an adjacent module under `shared/`) and MUST be the type of `ProjectSnapshot.audio_info`.

#### Scenario: AudioInfo is frozen

- **WHEN** code attempts to reassign any field of an `AudioInfo` instance
- **THEN** the system MUST raise `dataclasses.FrozenInstanceError`

### Requirement: from_project_file bridge

`ProjectSnapshot` SHALL provide a classmethod `from_project_file(project_file: ProjectFile, *, audio_info: AudioInfo, vad_frames: list[RawVadFrame] | None = None, chunks: list[Chunk] | None = None, pre_postprocess_subtitles: list[Subtitle] | None = None) -> ProjectSnapshot` that constructs a snapshot by copying scalar fields and `vad_segments`, `transcription_results`, and `subtitles` from the supplied `ProjectFile`, while populating `vad_frames`, `chunks`, and `pre_postprocess_subtitles` from the keyword arguments (defaulting to empty lists when omitted).

#### Scenario: Round-trip preserves transcription results

- **WHEN** a `ProjectFile` carrying three `TranscriptionResult` entries is passed to `ProjectSnapshot.from_project_file(pf, audio_info=ai)`
- **THEN** the resulting `ProjectSnapshot.transcription_results` MUST contain the same three entries in the same order
