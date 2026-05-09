## ADDED Requirements

### Requirement: Legacy vad_frames without backend tag default to "unknown"

`FileSnapshotLoader.load` SHALL accept `.tp` files whose `vad_frames` items omit the `backend` key (legacy files written before the per-backend change). For each such item, the loader MUST substitute the literal string `"unknown"` for the missing `backend` field when constructing the `RawVadFrame`. The loader SHALL emit exactly one `logging.warning` per `load(...)` call when at least one such legacy frame is encountered; the warning's message MUST contain both the file path and the literal substring `legacy vad_frames without 'backend' tag`. Items that do supply `backend` MUST NOT trigger the warning.

#### Scenario: Legacy vad_frames load with backend "unknown"

- **GIVEN** a `.tp` file at path `P` whose `vad_frames` items contain only `{"time_ms": ..., "prob": ...}` (no `backend` key)
- **WHEN** `FileSnapshotLoader().load(P)` is called
- **THEN** every loaded `RawVadFrame` MUST have `backend == "unknown"`
- **THEN** exactly one `WARNING`-level log record MUST be emitted whose message contains the string representation of `P` and the substring `legacy vad_frames without 'backend' tag`

#### Scenario: Modern vad_frames load without warning

- **GIVEN** a `.tp` file whose `vad_frames` items each contain `{"time_ms": ..., "prob": ..., "backend": "silero_vad"}`
- **WHEN** `FileSnapshotLoader().load(...)` is called
- **THEN** every loaded `RawVadFrame` MUST have `backend == "silero_vad"`
- **THEN** no `WARNING`-level log record MUST be emitted whose message contains the substring `legacy vad_frames without 'backend' tag`

#### Scenario: Mixed vad_frames produce one warning

- **GIVEN** a `.tp` file whose `vad_frames` list contains 10 items where 3 carry `backend` and 7 omit it
- **WHEN** `FileSnapshotLoader().load(...)` is called
- **THEN** the 3 modern frames MUST keep their supplied `backend` and the 7 legacy frames MUST be loaded with `backend == "unknown"`
- **THEN** exactly one `WARNING` MUST be emitted (not seven)
