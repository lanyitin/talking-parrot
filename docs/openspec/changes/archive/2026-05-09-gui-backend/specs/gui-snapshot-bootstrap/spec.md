## ADDED Requirements

### Requirement: Snapshot loaded once at startup

The CLI entry point `gui.cli.main` SHALL resolve the project path from CLI flag `--project` (overriding) or environment variable `TALKING_PARROT_GUI_PROJECT`, instantiate `talking_parrot.shared.snapshot_loader.FileSnapshotLoader`, call `loader.load(path)` exactly once, and pass the resulting `ProjectSnapshot` to `gui.http_server.serve`. The loader call MUST occur before the server binds its socket. If neither CLI flag nor environment variable supplies a project path, `gui.cli.main` MUST exit with a non-zero status and a stderr message naming `--project` and `TALKING_PARROT_GUI_PROJECT`.

#### Scenario: Loader invoked exactly once

- **WHEN** `gui.cli.main(["--project", "/tmp/x.tp"])` is invoked with `FileSnapshotLoader.load` patched to count calls
- **THEN** the recorded call count MUST equal `1`

#### Scenario: Missing project path exits non-zero

- **WHEN** `gui.cli.main([])` is invoked with the environment variable `TALKING_PARROT_GUI_PROJECT` unset
- **THEN** the call MUST exit with a non-zero status and the captured stderr MUST contain both `--project` and `TALKING_PARROT_GUI_PROJECT`

### Requirement: Snapshot held read-only after bootstrap

The HTTP server SHALL store the snapshot on the `ThreadingHTTPServer` instance as the attribute `snapshot` and MUST NOT reassign that attribute after the first call to `serve`. Request handlers MUST read the snapshot only via `self.server.snapshot` and MUST NOT mutate any field of the snapshot or any list it references.

#### Scenario: Reassignment attempt is rejected

- **WHEN** code calls `serve(snapshot, config)` once and then attempts to call `serve(other_snapshot, config)` on the same server instance
- **THEN** the second call MUST raise `RuntimeError` whose message names `snapshot already bound`

#### Scenario: Snapshot remains frozen during request handling

- **WHEN** any endpoint handler completes successfully
- **THEN** the bound `snapshot` MUST remain a `ProjectSnapshot` whose `frozen=True` invariant still holds (i.e. attribute reassignment still raises `dataclasses.FrozenInstanceError`)

### Requirement: Reuse of shared layer types

The `gui` package SHALL import `ProjectSnapshot`, `AudioInfo`, `FileSnapshotLoader`, and `SnapshotLoader` from `talking_parrot.shared` and MUST NOT redefine those types. The package MUST NOT contain any class or dataclass named `ProjectSnapshot`, `AudioInfo`, or `SnapshotLoader`.

#### Scenario: No duplicate definitions in gui package

- **WHEN** the `talking_parrot.gui` package is searched for class definitions
- **THEN** zero classes named `ProjectSnapshot`, `AudioInfo`, `FileSnapshotLoader`, or `SnapshotLoader` MUST be found

### Requirement: Configuration injected, never hardcoded

`GuiConfig` SHALL be the only source of truth for host, port, and project path inside `gui.http_server` and `gui.api`. No string literal naming a network host (e.g. `"127.0.0.1"`, `"0.0.0.0"`, `"localhost"`) and no integer port literal (e.g. `8765`, `8000`) MAY appear in `gui.http_server` or `gui.api` outside of the `GuiConfig` default-resolution helper.

#### Scenario: GuiConfig is the only literal source

- **WHEN** the source files `gui/http_server.py` and `gui/api.py` are scanned for the substrings `127.0.0.1`, `0.0.0.0`, `localhost`, and `8765`
- **THEN** zero matches MUST be found in `gui/api.py`, and any matches in `gui/http_server.py` MUST appear only inside the `GuiConfig` default-resolution helper or its docstring
