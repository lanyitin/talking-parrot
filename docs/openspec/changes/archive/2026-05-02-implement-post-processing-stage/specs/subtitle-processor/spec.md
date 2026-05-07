## ADDED Requirements

### Requirement: SubtitleProcessor abstract base class

The system SHALL provide an abstract base class `SubtitleProcessor` (in `src/talking_parrot/post_processing/base.py`) declaring exactly one abstract method: `process(subtitles: list[Subtitle], config: PostProcessingConfig) -> list[Subtitle]`. Direct instantiation of `SubtitleProcessor` SHALL raise `TypeError`. Subclasses MUST implement `process` to be instantiable.

#### Scenario: Direct instantiation raises TypeError

- **WHEN** code calls `SubtitleProcessor()` directly
- **THEN** Python MUST raise `TypeError`

#### Scenario: Subclass without process is not instantiable

- **GIVEN** a subclass `Foo(SubtitleProcessor)` that does not implement `process`
- **WHEN** code calls `Foo()`
- **THEN** Python MUST raise `TypeError`

---

### Requirement: SubtitleProcessor input immutability

Every concrete `SubtitleProcessor.process` implementation SHALL NOT mutate the input `subtitles` list, SHALL NOT mutate any `Subtitle` instance in the input list (the dataclass is `frozen=True`, so mutation will raise; this requirement is restated to make the contract explicit), and SHALL return a newly constructed list. The returned list MAY share `Subtitle` instances with the input only when no transformation occurred.

#### Scenario: Input list identity is preserved

- **GIVEN** a processor `P` and input `subs_in: list[Subtitle]`
- **WHEN** `P.process(subs_in, config)` returns `subs_out`
- **THEN** `subs_out is not subs_in` MUST hold
- **AND** `subs_in` MUST equal its pre-call value

---

### Requirement: SubtitleProcessor output ordering and timestamp invariants

Every concrete `SubtitleProcessor.process` implementation SHALL return a list whose `Subtitle` entries are ordered by non-decreasing `start_ms`. For every output `Subtitle`, `end_ms >= start_ms` MUST hold. For every adjacent pair `(a, b)` in the output, `b.start_ms >= a.start_ms` MUST hold. Processors MAY produce output with overlapping cues (`b.start_ms < a.end_ms`) only when the input also contained overlapping cues at the corresponding positions.

#### Scenario: Output is sorted by start_ms

- **GIVEN** any processor `P` and any sorted input `subs_in`
- **WHEN** `P.process(subs_in, config)` returns `subs_out`
- **THEN** for all `i in 0..len(subs_out) - 2`, `subs_out[i].start_ms <= subs_out[i + 1].start_ms` MUST hold

#### Scenario: Each output cue has non-negative duration

- **WHEN** any processor produces output
- **THEN** for every `s` in output, `s.end_ms >= s.start_ms` MUST hold

---

### Requirement: SubtitleProcessor handles empty input

Every concrete `SubtitleProcessor.process` implementation SHALL accept an empty list and return an empty list without raising.

#### Scenario: Empty input returns empty output

- **GIVEN** any concrete processor `P`
- **WHEN** `P.process([], config)` is called
- **THEN** the result MUST equal `[]`
- **AND** no exception MUST be raised
