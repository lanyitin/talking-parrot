## ADDED Requirements

### Requirement: FlaggedRegion value object

The system SHALL provide a frozen dataclass `FlaggedRegion` in `src/talking_parrot/gui/http_server.py` with fields `start_ms: int`, `end_ms: int`, and `label: str | None`. The dataclass MUST be declared with `frozen=True` and `slots=True`.

#### Scenario: Reassignment rejected

- **WHEN** code attempts `region.label = "x"` on a constructed `FlaggedRegion` instance
- **THEN** the system MUST raise `dataclasses.FrozenInstanceError`

### Requirement: Public read-only accessor for MCP bridge

The `gui.http_server` module SHALL expose a public function `get_flagged_regions() -> tuple[FlaggedRegion, ...]` that returns a tuple snapshot of the currently-flagged regions in the order they were posted. The returned object MUST be a `tuple` (immutable). The function MUST NOT expose the underlying mutable list.

#### Scenario: Accessor returns immutable tuple

- **WHEN** `get_flagged_regions()` is called after two regions have been posted
- **THEN** the returned object MUST be an instance of `tuple` of length `2`

#### Scenario: Mutating the returned value does not affect server state

- **WHEN** the caller calls `get_flagged_regions()`, then issues another `POST /api/flagged_regions` with a different region list
- **THEN** the previously-returned tuple MUST remain unchanged in length and contents

### Requirement: Atomic replacement under lock

The internal write helper SHALL acquire a `threading.Lock` for the duration of replacing the in-process region list, so that concurrent `POST /api/flagged_regions` requests cannot interleave to produce a partially-written list. The lock MUST be a module-level singleton.

#### Scenario: Concurrent posts produce a coherent end state

- **WHEN** two `POST /api/flagged_regions` requests run concurrently, one with two regions and one with three regions
- **THEN** a subsequent `get_flagged_regions()` call MUST return either exactly the two-region list or exactly the three-region list, and never a mixed combination

### Requirement: Cleared by POST with empty list

`POST /api/flagged_regions` with body `{"regions": []}` SHALL clear the in-process region list. After such a request, `get_flagged_regions()` MUST return an empty tuple and `GET /api/flagged_regions` MUST return `{"status": "empty", "regions": []}`.

#### Scenario: Empty post clears prior regions

- **WHEN** a region was previously posted, then a POST with body `{"regions": []}` is issued
- **THEN** `get_flagged_regions()` MUST return `()` and the next `GET /api/flagged_regions` body MUST satisfy `status == "empty"`

### Requirement: MCP integration boundary documented

The `gui.http_server` module SHALL document, in the docstring of `get_flagged_regions`, that the function is the sole sanctioned interface for any future MCP bridge to read flagged regions, and that no other code outside `talking_parrot.gui` MAY import the underlying region list. The docstring MUST contain the substring `MCP bridge`.

#### Scenario: Docstring mentions MCP bridge

- **WHEN** `inspect.getdoc(gui.http_server.get_flagged_regions)` is called
- **THEN** the returned string MUST contain the substring `MCP bridge`
