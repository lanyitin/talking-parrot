## ADDED Requirements

### Requirement: HallucinationFilterConfig schema

`PipelineConfig` SHALL expose an optional `hallucination_filter: HallucinationFilterConfig | None` field. `HallucinationFilterConfig` SHALL be a pydantic model with the following fields and defaults:

- `enabled: bool = True`
- `min_avg_logprob: float = -1.0`
- `max_no_speech_prob: float = 0.6`
- `max_compression_ratio: float = 2.4`
- `max_repetition_ratio: float = 0.5`
- `known_hallucination_phrases: list[str] = ["ご視聴ありがとうございました", "ご視聴ありがとうございます", "おやすみなさい"]` (default list copied from the audio2subtitle reference; project SHALL allow this list to be overridden via YAML)
- `phrase_match_enabled: bool = True`
- `bracket_match_enabled: bool = True`
- `repeat_match_enabled: bool = True`
- `low_logprob_match_enabled: bool = True`
- `compression_match_enabled: bool = True`
- `repetition_match_enabled: bool = True`

When `hallucination_filter is None` or `enabled is False`, `HallucinationFilterStage.process()` MUST return its input context unchanged. The CLI wiring (see `pipeline-end-to-end-wiring`) SHALL include the stage only when `hallucination_filter is not None`.

#### Scenario: Default HallucinationFilterConfig

- **GIVEN** YAML containing `hallucination_filter: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `HallucinationFilterConfig` MUST have `enabled=True`, `min_avg_logprob=-1.0`, `max_no_speech_prob=0.6`, `max_compression_ratio=2.4`, `max_repetition_ratio=0.5`

#### Scenario: Missing section yields None

- **GIVEN** YAML omits the `hallucination_filter` key entirely
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `PipelineConfig.hallucination_filter` MUST be `None`

### Requirement: PostProcessingConfig dedup and Japanese fields

`PostProcessingConfig` SHALL expose the following additional fields with defaults:

- `dedup_enabled: bool = True`
- `dedup_similarity_threshold: float = 0.9`
- `dedup_max_gap_ms: int = 600`
- `japanese_filler_enabled: bool = True`
- `japanese_repetition_enabled: bool = True`
- `japanese_filler_words: list[str] = ["あの", "あのー", "えっと", "えーと", "えー", "まあ", "そのー", "その", "なんか", "ね"]`
- `japanese_onomatopoeia_whitelist: list[str] = ["どきどき", "わくわく", "きらきら", "ぴかぴか"]`

`dedup_similarity_threshold` MUST be in the closed interval `[0.0, 1.0]`. `dedup_max_gap_ms` MUST be `>= 0`. Validation SHALL be enforced via pydantic field validators; out-of-range values MUST raise `pydantic.ValidationError`.

#### Scenario: Default fields populated

- **GIVEN** YAML containing `post_processing: {}`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** the resulting `PostProcessingConfig` MUST have `dedup_enabled=True`, `dedup_similarity_threshold=0.9`, `dedup_max_gap_ms=600`, `japanese_filler_enabled=True`, `japanese_repetition_enabled=True`

#### Scenario: Out-of-range threshold rejected

- **GIVEN** YAML with `post_processing.dedup_similarity_threshold: 1.5`
- **WHEN** `ConfigLoader.load()` parses it
- **THEN** `pydantic.ValidationError` MUST be raised
