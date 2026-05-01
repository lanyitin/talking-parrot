## ADDED Requirements

### Requirement: AlignmentBackendFactory routes by language and granularity

The system SHALL provide `AlignmentBackendFactory` with an instance method `create(language: str, granularity_pref: GranularityPreference = GranularityPreference.AUTO) -> AlignmentBackend`.

The factory SHALL maintain an internal registry keyed by `(language, AlignmentGranularity)` populated with at least these entries:
- `("en", AlignmentGranularity.WORD) → EnglishAlignmentBackend`
- `("ja", AlignmentGranularity.CHARACTER) → JapaneseAlignmentBackend`

A parallel `_DEFAULTS: dict[str, AlignmentGranularity]` SHALL declare each language's natural granularity:
- `"en" → AlignmentGranularity.WORD`
- `"ja" → AlignmentGranularity.CHARACTER`

#### Scenario: AUTO returns the language default

- **WHEN** `factory.create("en", GranularityPreference.AUTO)` is called
- **THEN** the returned instance MUST be an `EnglishAlignmentBackend`

- **WHEN** `factory.create("ja", GranularityPreference.AUTO)` is called
- **THEN** the returned instance MUST be a `JapaneseAlignmentBackend`

#### Scenario: Explicit WORD/CHARACTER preference looks up the registry directly

- **WHEN** `factory.create("en", GranularityPreference.WORD)` is called
- **THEN** the returned instance MUST be an `EnglishAlignmentBackend`

- **WHEN** `factory.create("ja", GranularityPreference.CHARACTER)` is called
- **THEN** the returned instance MUST be a `JapaneseAlignmentBackend`

### Requirement: AlignmentBackendFactory rejects missing language and missing granularity entries

`AlignmentBackendFactory.create()` SHALL raise `ValueError` with a clear message when:
- The `language` is not present in `_DEFAULTS` (AUTO mode) or in any registry entry (explicit mode). The message MUST contain the substring `No alignment backend for language`.
- The `(language, requested_granularity)` pair is absent from the registry under explicit `WORD` / `CHARACTER` preference. The message MUST contain the substring `No <granularity>-granularity alignment backend for language` where `<granularity>` is `WORD` or `CHARACTER`.

#### Scenario: Unknown language rejected

- **WHEN** `factory.create("fr", GranularityPreference.AUTO)` is called
- **THEN** the call MUST raise `ValueError` whose message contains `"No alignment backend for language"`

#### Scenario: Wrong granularity for known language rejected

- **WHEN** `factory.create("en", GranularityPreference.CHARACTER)` is called (English has only WORD-level)
- **THEN** the call MUST raise `ValueError` whose message contains `"No CHARACTER-granularity alignment backend for language"`

- **WHEN** `factory.create("ja", GranularityPreference.WORD)` is called (Japanese has only CHARACTER-level)
- **THEN** the call MUST raise `ValueError` whose message contains `"No WORD-granularity alignment backend for language"`

### Requirement: AlignmentBackendFactory caches backend instances

`AlignmentBackendFactory` SHALL cache instances by `(language, AlignmentGranularity)` so that repeated `create()` calls with arguments that resolve to the same key return the same `AlignmentBackend` object.

#### Scenario: Repeated AUTO calls return the same instance

- **WHEN** `factory.create("en")` is called twice (both AUTO)
- **THEN** both calls MUST return the same object (verified via `is` identity)

#### Scenario: AUTO and explicit WORD resolve to the same instance for English

- **WHEN** `factory.create("en", AUTO)` is followed by `factory.create("en", WORD)`
- **THEN** both calls MUST return the same object (verified via `is` identity)
