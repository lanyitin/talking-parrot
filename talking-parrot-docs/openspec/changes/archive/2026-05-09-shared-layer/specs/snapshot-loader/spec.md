## ADDED Requirements

### Requirement: SnapshotLoader protocol

The system SHALL provide a `typing.Protocol` named `SnapshotLoader` in `src/talking_parrot/shared/snapshot_loader.py` declaring a single method `load(source: str | pathlib.Path) -> ProjectSnapshot`. The protocol MUST be decorated with `@typing.runtime_checkable` so that `isinstance(obj, SnapshotLoader)` succeeds for any object exposing a matching `load` attribute.

#### Scenario: Duck-typed loader satisfies the protocol

- **WHEN** a class `Stub` defining `def load(self, source): return snapshot` is instantiated as `s = Stub()`
- **THEN** `isinstance(s, SnapshotLoader)` MUST return `True`

### Requirement: FileSnapshotLoader default implementation

The system SHALL provide a class `FileSnapshotLoader` in `src/talking_parrot/shared/snapshot_loader.py` whose `load(source)` method reads the file at `source` as JSON and returns a fully populated `ProjectSnapshot`. `FileSnapshotLoader` MUST satisfy the `SnapshotLoader` protocol.

#### Scenario: Loading a well-formed file

- **WHEN** `FileSnapshotLoader().load(path)` is called on a `.tp` JSON file containing all required scalar fields and well-formed list fields
- **THEN** the returned object MUST be a `ProjectSnapshot` whose fields equal the file's contents

### Requirement: Tolerant defaults for missing list fields

`FileSnapshotLoader.load` SHALL default any of `vad_frames`, `vad_segments`, `chunks`, `transcription_results`, `pre_postprocess_subtitles`, and `subtitles` to an empty list when the underlying JSON omits the corresponding key. The loader MUST emit a `logging` debug-level message naming each list field that defaulted.

#### Scenario: Missing list field defaults to empty

- **WHEN** `FileSnapshotLoader().load(path)` is called on a file that contains all required scalar fields but omits `vad_frames`
- **THEN** the returned `ProjectSnapshot.vad_frames` MUST equal `[]` and a debug-level log message naming `vad_frames` MUST be emitted

### Requirement: Hard failure on missing required scalar field

`FileSnapshotLoader.load` SHALL raise `KeyError` whose message names the missing field when any of `version`, `created_at`, `source_path`, `config_snapshot`, or `audio_info` is absent from the JSON file. The loader MUST NOT silently substitute defaults for these fields.

#### Scenario: Missing required field

- **WHEN** `FileSnapshotLoader().load(path)` is called on a file lacking `version`
- **THEN** the call MUST raise `KeyError` and the error message MUST contain the string `"version"`

### Requirement: Underlying I/O errors propagate unchanged

`FileSnapshotLoader.load` SHALL propagate `FileNotFoundError` when `source` does not exist and `json.JSONDecodeError` when the file is not valid JSON. The loader MUST NOT wrap or suppress these errors.

#### Scenario: Missing file

- **WHEN** `FileSnapshotLoader().load("/nonexistent.tp")` is called
- **THEN** the call MUST raise `FileNotFoundError`

#### Scenario: Malformed JSON

- **WHEN** `FileSnapshotLoader().load(path)` is called on a file whose contents are not valid JSON
- **THEN** the call MUST raise `json.JSONDecodeError`
