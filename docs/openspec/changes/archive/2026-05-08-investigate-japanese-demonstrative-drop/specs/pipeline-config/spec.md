## MODIFIED Requirements

### Requirement: PostProcessingConfig dedup and Japanese fields

`PostProcessingConfig` SHALL expose the following additional fields with defaults:

- `dedup_enabled: bool = True`
- `dedup_similarity_threshold: float = 0.9`
- `dedup_max_gap_ms: int = 600`
- `japanese_filler_enabled: bool = True`
- `japanese_repetition_enabled: bool = True`
- `japanese_filler_words: list[str] = ["あのー", "えーと", "えー", "そのー"]`
- `japanese_onomatopoeia_whitelist: list[str] = ["どきどき", "わくわく", "きらきら", "ぴかぴか"]`

The default `japanese_filler_words` list MUST include only prolonged-vowel filler forms (those ending in the chōonpu `ー`). Bare-form fillers such as `その`, `あの`, `えっと`, `まあ`, `なんか`, `ね` MUST NOT appear in the default list because they collide with content words (most prominently the demonstrative pronoun `その`, observed in `test-samples/sample1`). Operators who need bare-form filler stripping for a specific corpus MAY add entries via the YAML `post_processing.japanese_filler_words` override.

`dedup_similarity_threshold` MUST be in the closed interval `[0.0, 1.0]`. `dedup_max_gap_ms` MUST be `>= 0`. Validation SHALL be enforced via pydantic field validators; out-of-range values MUST raise `pydantic.ValidationError`.

#### Scenario: Default fields populated

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `PostProcessingConfig` MUST have `dedup_enabled=True`, `dedup_similarity_threshold=0.9`, `dedup_max_gap_ms=600`, `japanese_filler_enabled=True`, `japanese_repetition_enabled=True`

#### Scenario: Default japanese_filler_words excludes bare demonstrative

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `PostProcessingConfig.japanese_filler_words` MUST NOT contain the bare string `"その"`
- **AND** it MUST contain the prolonged form `"そのー"`

#### Scenario: Out-of-range threshold rejected

- **GIVEN** YAML with `post_processing.dedup_similarity_threshold: 1.5`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised
