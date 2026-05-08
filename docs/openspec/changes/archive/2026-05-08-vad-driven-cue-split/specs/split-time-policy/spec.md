## MODIFIED Requirements

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

---

## ADDED Requirements

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
