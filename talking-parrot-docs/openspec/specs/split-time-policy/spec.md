# split-time-policy Specification

## Purpose

TBD - created by archiving change 'snap-split-timestamps-to-vad-silence'. Update Purpose after archive.

## Requirements

### Requirement: SplitTimePolicy protocol defines the time-snap interface

The system SHALL provide a `SplitTimePolicy` protocol (in `src/talking_parrot/post_processing/split_time_policy.py`) declaring two methods:

```
def adjust(self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int) -> int
def pick(self, cue_start_ms: int, cue_end_ms: int) -> int | None
```

`adjust` SHALL accept a candidate slice-boundary timestamp produced by the calling processor's linear interpolation, and the enclosing cue's start and end timestamps. It SHALL return an integer in the open interval `(cue_start_ms, cue_end_ms)`. Implementations MUST be pure (no side effects). The protocol SHALL NOT be instantiable directly; it is a structural type used for dependency injection. The protocol SHALL be decorated with `@typing.runtime_checkable`.

`pick` SHALL accept the cue's `cue_start_ms` and `cue_end_ms`. It SHALL return the best silence midpoint (as an integer) strictly inside `(cue_start_ms, cue_end_ms)`, or `None` when no qualifying silence exists inside that window. Implementations MUST be pure (no side effects).

#### Scenario: Returned timestamp from adjust is strictly inside the cue

- **GIVEN** any `SplitTimePolicy` implementation, a cue with `cue_start_ms = 1000`, `cue_end_ms = 7000`, and any `candidate_ms` in `(1000, 7000)`
- **WHEN** `policy.adjust(candidate_ms, 1000, 7000)` is called
- **THEN** the returned integer MUST satisfy `1000 < value < 7000`

#### Scenario: pick returns None or a midpoint strictly inside the cue

- **GIVEN** any `SplitTimePolicy` implementation and a cue with `cue_start_ms = 0`, `cue_end_ms = 9000`
- **WHEN** `policy.pick(0, 9000)` is called
- **THEN** the return value MUST be either `None` or an integer satisfying `0 < value < 9000`


<!-- @trace
source: vad-driven-cue-split
updated: 2026-05-08
code:
  - uv.lock
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - pyproject.toml
tests:
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
-->

---
### Requirement: LinearSplitTimePolicy returns the candidate unchanged

The system SHALL provide a concrete `LinearSplitTimePolicy` (in `src/talking_parrot/post_processing/split_time_policy.py`) whose `adjust(candidate_ms, cue_start_ms, cue_end_ms)` SHALL return `candidate_ms` unmodified. Its `pick(cue_start_ms, cue_end_ms)` SHALL always return `None`. This is the default policy used for non-VAD pipelines and preserves the historical linear-interpolation split behaviour.

#### Scenario: Default policy adjust is a no-op

- **GIVEN** `policy = LinearSplitTimePolicy()`
- **WHEN** `policy.adjust(4500, 0, 9000)` is called
- **THEN** the returned integer MUST equal `4500`

#### Scenario: Default policy pick always returns None

- **GIVEN** `policy = LinearSplitTimePolicy()`
- **WHEN** `policy.pick(0, 9000)` is called
- **THEN** the return value MUST be `None`


<!-- @trace
source: vad-driven-cue-split
updated: 2026-05-08
code:
  - uv.lock
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - pyproject.toml
tests:
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
-->

---
### Requirement: VadAlignedSplitTimePolicy snaps to nearest silence midpoint within radius

The system SHALL provide `VadAlignedSplitTimePolicy(silences, search_radius_ms)` (in `src/talking_parrot/post_processing/split_time_policy.py`).

The constructor SHALL accept:

- `silences: Sequence[tuple[int, int]]` — a sequence of `(silence_start_ms, silence_end_ms)` half-open intervals representing pauses between speech. The constructor MUST copy `silences` into an internal immutable representation (e.g., `tuple`) so mutation of the caller-provided sequence does not affect the policy.
- `search_radius_ms: int` — a non-negative search radius in milliseconds. The constructor MUST raise `ValueError` if `search_radius_ms < 0`.

`adjust(candidate_ms, cue_start_ms, cue_end_ms)` SHALL:

1. Compute the search window `[lo, hi] = [candidate_ms - search_radius_ms, candidate_ms + search_radius_ms]`.
2. From the configured silences, select those whose midpoint `mid = (silence_start + silence_end) // 2` satisfies `lo <= mid <= hi` AND `cue_start_ms < mid < cue_end_ms`.
3. From the surviving candidates, choose the silence whose `mid` minimises `abs(mid - candidate_ms)`. Ties SHALL be broken by selecting the smaller `mid`.
4. Return the chosen `mid`.
5. If no silence satisfies the constraints, return `candidate_ms` unchanged.

The policy SHALL NOT mutate the cue's `text` and SHALL NOT consume any field of `Subtitle`. Time complexity SHALL be linear in the number of configured silences.

#### Scenario: Snaps to a silence midpoint within radius

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[(4400, 4700)], search_radius_ms=300)`
- **WHEN** `policy.adjust(candidate_ms=4500, cue_start_ms=0, cue_end_ms=9000)` is called
- **THEN** the returned integer MUST equal `4550`

#### Scenario: Falls back to candidate when no silence within radius

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[(0, 100), (8800, 9000)], search_radius_ms=200)`
- **WHEN** `policy.adjust(candidate_ms=4500, cue_start_ms=0, cue_end_ms=9000)` is called
- **THEN** the returned integer MUST equal `4500`

#### Scenario: Snaps to nearer of two silences in window

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[(4200, 4400), (4700, 4900)], search_radius_ms=500)`
- **WHEN** `policy.adjust(candidate_ms=4700, cue_start_ms=0, cue_end_ms=9000)` is called (mid `4300` is `400` away, mid `4800` is `100` away)
- **THEN** the returned integer MUST equal `4800`

##### Example: Tie-break prefers smaller midpoint

| candidate_ms | silences                                       | radius | expected |
| ------------ | ---------------------------------------------- | ------ | -------- |
| 5000         | `[(4500, 4700), (5300, 5500)]` (both 400 away) | 500    | 4600     |

#### Scenario: Silence midpoint outside cue bounds is ignored

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[(8900, 9100)], search_radius_ms=500)`
- **WHEN** `policy.adjust(candidate_ms=8800, cue_start_ms=0, cue_end_ms=9000)` is called and the silence midpoint `9000` equals `cue_end_ms`
- **THEN** the returned integer MUST equal `8800` (silence rejected because `mid < cue_end_ms` does not hold)

#### Scenario: Negative radius rejected at construction

- **WHEN** `VadAlignedSplitTimePolicy(silences=[], search_radius_ms=-1)` is constructed
- **THEN** `ValueError` MUST be raised

#### Scenario: Constructor copy isolates from caller mutation

- **GIVEN** `silences = [(4400, 4700)]` and `policy = VadAlignedSplitTimePolicy(silences=silences, search_radius_ms=300)`
- **WHEN** the caller mutates `silences` via `silences.append((0, 100))` and then calls `policy.adjust(50, 0, 9000)`
- **THEN** the returned integer MUST equal `50` (the appended silence SHALL NOT influence the result)

<!-- @trace
source: snap-split-timestamps-to-vad-silence
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/character_boundary.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/post_processing/time_based.py
tests:
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
  - tests/unit/post_processing/test_time_based.py
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/config/test_models.py
-->

---
### Requirement: VadAlignedSplitTimePolicy.pick returns best silence midpoint inside cue window

`VadAlignedSplitTimePolicy.pick(cue_start_ms, cue_end_ms)` SHALL:

1. Compute the linear midpoint `center_ms = (cue_start_ms + cue_end_ms) // 2`.
2. From the configured silences, select those whose midpoint `mid = (silence_start + silence_end) // 2` satisfies `cue_start_ms < mid < cue_end_ms`.
3. From the surviving candidates, choose the silence whose `mid` minimises `abs(mid - center_ms)`. Ties SHALL be broken by selecting the smaller `mid`.
4. Return the chosen `mid` as an integer.
5. If no silence satisfies the constraints, return `None`.

The method SHALL NOT consume any `Subtitle` fields and SHALL NOT have side effects. Time complexity SHALL be linear in the number of configured silences.

#### Scenario: pick returns midpoint of silence inside the cue

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[(4400, 4700)], search_radius_ms=300)`
- **WHEN** `policy.pick(cue_start_ms=0, cue_end_ms=9000)` is called
- **THEN** the returned integer MUST equal `4550`

#### Scenario: pick returns None when no silence is inside the cue

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[(100, 200), (8900, 9100)], search_radius_ms=500)`
- **WHEN** `policy.pick(cue_start_ms=500, cue_end_ms=8500)` is called (both silence midpoints lie outside `(500, 8500)`)
- **THEN** the return value MUST be `None`

#### Scenario: pick returns None for empty silence list

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[], search_radius_ms=300)`
- **WHEN** `policy.pick(cue_start_ms=0, cue_end_ms=9000)` is called
- **THEN** the return value MUST be `None`

#### Scenario: pick tie-breaks to smaller midpoint when equidistant from center

- **GIVEN** `policy = VadAlignedSplitTimePolicy(silences=[(3800, 4200), (5800, 6200)], search_radius_ms=1000)` with `center_ms = 5000` (cue 0..10000)
- **WHEN** `policy.pick(cue_start_ms=0, cue_end_ms=10000)` is called (both midpoints 4000 and 6000 are 1000 from center)
- **THEN** the return value MUST equal `4000`

<!-- @trace
source: vad-driven-cue-split
updated: 2026-05-08
code:
  - uv.lock
  - docs/TODOs.md
  - src/talking_parrot/post_processing/factory.py
  - src/talking_parrot/post_processing/split_time_policy.py
  - src/talking_parrot/post_processing/character_boundary.py
  - pyproject.toml
tests:
  - tests/unit/post_processing/test_character_boundary.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/post_processing/test_split_time_policy.py
-->