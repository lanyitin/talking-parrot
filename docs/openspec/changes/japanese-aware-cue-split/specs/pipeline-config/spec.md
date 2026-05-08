## ADDED Requirements

### Requirement: PostProcessingConfig Japanese split-boundary fields

`PostProcessingConfig` SHALL expose the following additional fields with defaults that drive `JapaneseSplitBoundaryPolicy`:

- `japanese_split_search_radius: int = 4`
- `japanese_split_no_split_units: list[str] = ["ます", "ません", "まし", "です", "でし", "だっ", "った", "ない", "なかっ", "たい", "よう", "そう", "という", "について"]`
- `japanese_split_no_leading_particles: list[str] = ["て", "で", "に", "を", "が", "は", "も", "と", "から", "まで", "より", "へ", "や", "か", "の", "ね", "よ"]`
- `japanese_split_no_leading_finals: list[str] = ["た", "だ", "る", "い"]`

`japanese_split_search_radius` MUST be in the closed interval `[0, 20]`. Validation SHALL be enforced via a pydantic field validator; out-of-range values MUST raise `pydantic.ValidationError`. Each list field MUST contain only non-empty strings; empty-string entries MUST raise `pydantic.ValidationError`.

#### Scenario: Default fields populated

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `PostProcessingConfig` MUST have `japanese_split_search_radius == 4`
- **AND** `japanese_split_no_split_units` MUST contain `"まし"`, `"です"`, and `"よう"`
- **AND** `japanese_split_no_leading_particles` MUST contain `"に"`, `"を"`, and `"の"`
- **AND** `japanese_split_no_leading_finals` MUST contain `"た"` and `"い"`

#### Scenario: Out-of-range radius rejected

- **GIVEN** YAML with `post_processing.japanese_split_search_radius: 25`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

#### Scenario: Empty string in list rejected

- **GIVEN** YAML with `post_processing.japanese_split_no_leading_particles: ["", "に"]`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

#### Scenario: Negative radius rejected

- **GIVEN** YAML with `post_processing.japanese_split_search_radius: -1`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised

