## ADDED Requirements

### Requirement: Entry point loads snapshot then dispatches transport

The system SHALL provide an entry point invokable as `uv run python -m talking_parrot.mcp` that requires a `--project <path>` argument, loads a `ProjectSnapshot` once via `SnapshotLoader`, installs it on the server module as a read-only module-level binding, and then dispatches to the selected transport. Snapshot loading SHALL complete before any tool is registered or any transport begins listening.

#### Scenario: Project flag missing

- **WHEN** the entry point is invoked without `--project`
- **THEN** the process SHALL exit non-zero with a stderr message naming the missing flag
- **AND** no transport SHALL bind a port and no stdio loop SHALL start

#### Scenario: Snapshot loads then HTTP transport binds

- **WHEN** the entry point is invoked with `--project <valid-path>` and no `--transport` flag
- **THEN** the snapshot SHALL be loaded synchronously before any port is bound
- **AND** the streamable HTTP transport SHALL begin listening on the resolved host and port
- **AND** the resolved host, port, and project path SHALL be logged to stdout via `logging`

### Requirement: Module-level snapshot is read-only after init

The server module SHALL hold the loaded `ProjectSnapshot` in a single module-level binding assigned exactly once during entry-point setup. Tools SHALL read this binding through a pure accessor and SHALL NOT reassign, replace, or mutate it.

#### Scenario: Tool reads snapshot via accessor

- **WHEN** any registered tool is invoked
- **THEN** the tool SHALL retrieve the snapshot via the module-level accessor
- **AND** the tool SHALL NOT call any setter or rebind the module-level binding

#### Scenario: Reload at runtime is unsupported

- **WHEN** a caller attempts to reassign the module-level snapshot binding after entry-point setup completes
- **THEN** the system SHALL document this path as unsupported and SHALL require process restart to load a different project

### Requirement: Configuration is injected via env vars and CLI flags

The system SHALL resolve transport, host, and port configuration from CLI flags, falling back to environment variables (`TALKING_PARROT_MCP_HOST`, `TALKING_PARROT_MCP_PORT`), falling back to documented built-in defaults. CLI flags SHALL take precedence over environment variables. No host, port, or transport value SHALL be hardcoded outside the documented defaults.

#### Scenario: CLI flag overrides env var

- **WHEN** `TALKING_PARROT_MCP_PORT=9000` is set and `--port 9100` is passed on the CLI
- **THEN** the resolved port SHALL be `9100`

#### Scenario: Env var overrides default

- **WHEN** `TALKING_PARROT_MCP_HOST=0.0.0.0` is set and no `--host` flag is passed
- **THEN** the resolved host SHALL be `0.0.0.0`

### Requirement: Transport selection supports HTTP default and stdio opt-in

The system SHALL accept `--transport http` (default when the flag is absent) and `--transport stdio`. Any other value SHALL cause non-zero exit with a stderr message naming the invalid value.

#### Scenario: Default transport is HTTP

- **WHEN** the entry point is invoked without `--transport`
- **THEN** the streamable HTTP transport SHALL be selected

#### Scenario: stdio is opt-in

- **WHEN** `--transport stdio` is passed
- **THEN** the stdio transport SHALL be selected
- **AND** no port SHALL be bound

#### Scenario: Invalid transport value

- **WHEN** `--transport grpc` is passed
- **THEN** the process SHALL exit non-zero with a stderr message naming `grpc` as invalid

### Requirement: Shutdown is graceful on SIGINT

The system SHALL handle SIGINT and SIGTERM by exiting the running transport cleanly without raising an unhandled exception to the user.

#### Scenario: SIGINT during HTTP serve

- **WHEN** SIGINT is received while the HTTP transport is listening
- **THEN** the transport SHALL stop accepting new connections and the process SHALL exit with status 0

### Requirement: Logging targets stdout only

The system SHALL emit all operational log output through Python `logging` to stdout / stderr. The application SHALL NOT register a file handler or write logs to disk.

#### Scenario: Startup log goes to stdout

- **WHEN** the entry point completes configuration resolution
- **THEN** the resolved configuration SHALL be emitted via `logging` to stdout
- **AND** no log file SHALL be created on the filesystem
