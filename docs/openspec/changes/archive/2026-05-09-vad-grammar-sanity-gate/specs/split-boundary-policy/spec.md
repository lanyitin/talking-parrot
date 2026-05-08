## ADDED Requirements

### Requirement: SplitBoundaryPolicy protocol declares public is_valid method

The `SplitBoundaryPolicy` protocol (in `src/talking_parrot/post_processing/split_policy.py`) SHALL declare an additional method:

```python
def is_valid(self, text: str, index: int) -> bool
```

`is_valid` SHALL accept the cue text and a candidate split index, and SHALL return `True` if the implementation considers `index` a valid (non-forbidden) cut point inside `text`, otherwise `False`. Implementations MUST be pure (no side effects) and MUST NOT mutate `text`. The method SHALL be safely callable for any integer `index` in `[1, len(text) - 1]`; behavior outside that range is unspecified and callers SHALL clamp the input first.

The protocol contract SHALL satisfy: for any implementation `P`, if `P.is_valid(text, i)` returns `True`, then `P.adjust(text, i, 0)` SHALL return `i`. (i.e., a valid index is a fixed point of `adjust` at radius 0.)

#### Scenario: Valid index is a fixed point of adjust at radius 0

- **GIVEN** any `SplitBoundaryPolicy` implementation `P`, a non-empty `text` of length `n >= 2`, and an index `i` in `[1, n - 1]`
- **WHEN** `P.is_valid(text, i)` returns `True`
- **THEN** `P.adjust(text, i, 0)` MUST return `i`

#### Scenario: is_valid is pure

- **GIVEN** any `SplitBoundaryPolicy` implementation `P` and inputs `text`, `i`
- **WHEN** `P.is_valid(text, i)` is called twice with identical arguments
- **THEN** both calls MUST return the same boolean value
- **AND** `text` MUST NOT be mutated

### Requirement: LinearSplitBoundaryPolicy.is_valid always returns True

`LinearSplitBoundaryPolicy.is_valid(text, index)` SHALL return `True` for every input where `1 <= index <= len(text) - 1`. This preserves Liskov substitutability: the linear policy treats every in-range index as a valid cut point, matching its no-op `adjust` behavior.

#### Scenario: Linear policy considers any in-range index valid

- **GIVEN** `policy = LinearSplitBoundaryPolicy()` and `text = "abcdefgh"` (length 8)
- **WHEN** `policy.is_valid(text, i)` is called for every `i` in `[1, 7]`
- **THEN** every call MUST return `True`

### Requirement: JapaneseSplitBoundaryPolicy.is_valid exposes the existing rule check

`JapaneseSplitBoundaryPolicy.is_valid(text, index)` SHALL return `False` if and only if `index` is INVALID under the rule set already defined for `JapaneseSplitBoundaryPolicy.adjust` (the union of Mid-katakana, Mid-digit, Mid-no-split-unit, Leading-particle, and Leading-final rules, evaluated against the policy's configured `japanese_split_no_split_units`, `japanese_split_no_leading_particles`, and `japanese_split_no_leading_finals`). Otherwise `is_valid` SHALL return `True`.

The implementation SHALL share its rule evaluation with `adjust` such that the two methods cannot disagree (e.g., by routing both through a single internal predicate).

#### Scenario: Mid-auxiliary index is invalid

- **GIVEN** `policy = JapaneseSplitBoundaryPolicy(default_config)` and `text = "専攻しておりました"` (length 9)
- **WHEN** `policy.is_valid(text, 8)` is called (would split between `まし` and `た`; `text[7]='し'` is hiragana and `text[8:]` starts with `た` which is a configured leading-final)
- **THEN** the return value MUST be `False`

#### Scenario: Boundary outside any forbidden rule is valid

- **GIVEN** the same `policy` and `text = "専攻しておりました"`
- **WHEN** `policy.is_valid(text, 2)` is called (boundary between `専攻` and `してお…`; no rule triggered)
- **THEN** the return value MUST be `True`

#### Scenario: is_valid agrees with adjust at radius 0

- **GIVEN** `policy = JapaneseSplitBoundaryPolicy(default_config)`, any `text`, any `index` in `[1, len(text) - 1]`
- **WHEN** `policy.is_valid(text, index)` returns `True`
- **THEN** `policy.adjust(text, index, 0)` MUST return `index`
- **AND** when `policy.is_valid(text, index)` returns `False`, `policy.adjust(text, index, 0)` MUST also return `index` (per existing radius-0 no-op rule), but the index remains semantically invalid
