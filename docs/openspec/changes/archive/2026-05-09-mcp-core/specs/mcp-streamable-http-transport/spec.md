## ADDED Requirements

### Requirement: Streamable HTTP is the default transport

The MCP server SHALL default to streamable HTTP when no `--transport` flag is provided. stdio SHALL be available only via explicit `--transport stdio`.

#### Scenario: Absent transport flag selects HTTP

- **WHEN** the server is started without `--transport`
- **THEN** streamable HTTP SHALL be the active transport
- **AND** a TCP listener SHALL be bound on the resolved host and port

#### Scenario: stdio is reachable only by explicit opt-in

- **WHEN** an operator wishes to run over stdio
- **THEN** they SHALL pass `--transport stdio` explicitly
- **AND** the system SHALL NOT silently fall back from HTTP to stdio under any other condition

### Requirement: Default bind is loopback host and port 8765

The streamable HTTP transport SHALL bind to host `127.0.0.1` and port `8765` when neither CLI flags nor environment variables override them.

#### Scenario: Defaults applied when nothing is set

- **WHEN** no `--host`, `--port`, `TALKING_PARROT_MCP_HOST`, or `TALKING_PARROT_MCP_PORT` is provided
- **THEN** the listener SHALL bind `127.0.0.1:8765`

#### Scenario: Environment variables override defaults

- **WHEN** `TALKING_PARROT_MCP_HOST=192.168.1.10` and `TALKING_PARROT_MCP_PORT=9000` are set and no CLI flags are passed
- **THEN** the listener SHALL bind `192.168.1.10:9000`

### Requirement: MCP endpoint path is `/mcp`

The streamable HTTP transport SHALL expose the MCP protocol on path `/mcp`.

#### Scenario: HTTP endpoint shape

- **WHEN** an MCP-aware agent connects to `http://<host>:<port>/mcp`
- **THEN** the server SHALL respond with the FastMCP streamable-HTTP protocol contract

### Requirement: Port collision surfaces a clear failure

The system SHALL surface a non-zero exit with a stderr message identifying the host and port when the bind fails because the address is already in use.

#### Scenario: Port already in use

- **WHEN** the configured port is occupied at startup
- **THEN** the process SHALL exit non-zero
- **AND** the stderr message SHALL name the host and port that failed to bind
