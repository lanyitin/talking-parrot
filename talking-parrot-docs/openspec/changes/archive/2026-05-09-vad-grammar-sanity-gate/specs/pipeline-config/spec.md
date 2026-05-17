## ADDED Requirements

### Requirement: PostProcessingConfig exposes vad_grammar_search_radius

`PostProcessingConfig` (in `src/talking_parrot/config/models.py`) SHALL expose an integer field `vad_grammar_search_radius` with default value `2`. The field SHALL be validated at construction time to satisfy `vad_grammar_search_radius >= 0`; values less than zero SHALL cause pydantic validation to raise `ValidationError`.

The YAML key `post_processing.vad_grammar_search_radius` SHALL be optional. When omitted from a YAML file, `ConfigLoader.load` SHALL produce a `PostProcessingConfig` whose `vad_grammar_search_radius == 2` (no error, no warning).

This field is consumed by `CharacterBoundarySplitProcessor` to bound the search radius used when snapping a VAD-derived `char_idx` to the nearest grammar-valid boundary (sub-path 3b in `character-boundary-processors`).

#### Scenario: Default value is 2 when YAML omits the field

- **GIVEN** a YAML config file whose `post_processing` section does not contain a `vad_grammar_search_radius` key
- **WHEN** `ConfigLoader.load(path)` is called
- **THEN** the returned `PipelineConfig.post_processing.vad_grammar_search_radius` MUST equal `2`

#### Scenario: Explicit zero is accepted

- **GIVEN** a YAML config file with `post_processing.vad_grammar_search_radius: 0`
- **WHEN** `ConfigLoader.load(path)` is called
- **THEN** the returned `PipelineConfig.post_processing.vad_grammar_search_radius` MUST equal `0`

#### Scenario: Negative value is rejected

- **GIVEN** a YAML config file with `post_processing.vad_grammar_search_radius: -1`
- **WHEN** `ConfigLoader.load(path)` is called
- **THEN** a `pydantic.ValidationError` MUST be raised
