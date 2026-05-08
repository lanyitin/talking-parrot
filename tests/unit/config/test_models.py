import pytest
import pydantic

from talking_parrot.config.models import (
    PipelineConfig,
    VadConfig,
    ChunkingConfig,
    AlignConfig,
    PostProcessingConfig,
    TranscribingStep,
    HallucinationFilterConfig,
)


class TestPipelineConfigOptionality:
    def test_optional_sections_default_none(self):
        cfg = PipelineConfig(
            transcribing=[{"condition": "true", "backend": "faster-whisper"}]
        )
        assert cfg.vad is None
        assert cfg.chunking is None
        assert cfg.align is None
        assert cfg.post_processing is None

    def test_transcribing_non_empty_required(self):
        with pytest.raises(pydantic.ValidationError):
            PipelineConfig(transcribing=[])

    def test_transcribing_missing_raises(self):
        with pytest.raises(pydantic.ValidationError):
            PipelineConfig()  # type: ignore

    def test_full_config_parses(self):
        cfg = PipelineConfig(
            expected_language="en",
            vad=VadConfig(),
            chunking=ChunkingConfig(),
            transcribing=[TranscribingStep(condition="true", backend="faster-whisper")],
            align=AlignConfig(),
            post_processing=PostProcessingConfig(),
        )
        assert cfg.vad is not None
        assert cfg.chunking is not None
        assert cfg.align is not None
        assert cfg.post_processing is not None


class TestVadConfigNewFields:
    def test_formula_has_default_value(self):
        """VadConfig.formula defaults to equal-weight average formula."""
        cfg = VadConfig()
        assert cfg.formula == "(ten_vad_prob + silero_vad_prob) / 2"

    def test_neg_threshold_has_default_value(self):
        """VadConfig.neg_threshold defaults to 0.35."""
        cfg = VadConfig()
        assert cfg.neg_threshold == 0.35

    def test_formula_can_be_overridden(self):
        """VadConfig.formula accepts a custom formula string."""
        cfg = VadConfig(formula="(ten_vad_prob * 0.9) + (silero_vad_prob * 0.1)")
        assert cfg.formula == "(ten_vad_prob * 0.9) + (silero_vad_prob * 0.1)"

    def test_neg_threshold_can_be_overridden(self):
        """VadConfig.neg_threshold accepts a custom float value."""
        cfg = VadConfig(neg_threshold=0.4)
        assert cfg.neg_threshold == 0.4


class TestChunkingConfigSilencePad:
    """Tests for the silence_pad_ms field on ChunkingConfig."""

    def test_silence_pad_ms_default_is_50(self):
        """ChunkingConfig.silence_pad_ms defaults to 50 when not specified."""
        cfg = ChunkingConfig()
        assert cfg.silence_pad_ms == 50

    def test_silence_pad_ms_explicit_value(self):
        """ChunkingConfig.silence_pad_ms accepts an explicit positive value."""
        cfg = ChunkingConfig(silence_pad_ms=100)
        assert cfg.silence_pad_ms == 100

    def test_silence_pad_ms_negative_raises(self):
        """ChunkingConfig.silence_pad_ms rejects negative values with a ValidationError."""
        with pytest.raises(pydantic.ValidationError):
            ChunkingConfig(silence_pad_ms=-1)


class TestTranscribingStepBackendOptional:
    """`TranscribingStep.backend` is optional with platform-aware default (loader-resolved)."""

    def test_backend_omitted_constructs_with_none(self):
        """Omitting `backend` MUST construct successfully with `backend is None`."""
        step = TranscribingStep(condition="true")
        assert step.backend is None

    def test_backend_explicit_value_preserved(self):
        """An explicit backend value MUST be preserved on the model."""
        step = TranscribingStep(condition="true", backend="faster-whisper")
        assert step.backend == "faster-whisper"

    def test_backend_explicit_null_constructs_with_none(self):
        """Explicit `backend=None` (mirrors YAML `backend: null`) MUST be accepted."""
        step = TranscribingStep(condition="true", backend=None)
        assert step.backend is None


class TestPipelineConfigUnknownFields:
    def test_unknown_top_level_field_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            PipelineConfig(
                transcribing=[{"condition": "true", "backend": "faster-whisper"}],
                unknown_field="boom",  # type: ignore
            )

    def test_vad_unknown_field_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            VadConfig(activty_threshold=0.5)  # type: ignore — typo


class TestPostProcessingConfigDefaults:
    """Defaults required by D8 of implement-post-processing-stage."""

    def test_merge_gap_threshold_ms_default(self):
        """merge_gap_threshold_ms defaults to 200."""
        assert PostProcessingConfig().merge_gap_threshold_ms == 200

    def test_merge_max_duration_ms_default(self):
        """merge_max_duration_ms defaults to 6000."""
        assert PostProcessingConfig().merge_max_duration_ms == 6000

    def test_split_max_duration_ms_default(self):
        """split_max_duration_ms defaults to 6000."""
        assert PostProcessingConfig().split_max_duration_ms == 6000

    def test_legacy_yaml_without_new_fields_loads(self):
        """A YAML-style dict missing the new fields still validates."""
        cfg = PostProcessingConfig(
            **{"enabled": True, "max_line_length": 42, "max_lines_per_subtitle": 2}
        )
        assert cfg.merge_gap_threshold_ms == 200
        assert cfg.merge_max_duration_ms == 6000
        assert cfg.split_max_duration_ms == 6000

    def test_unknown_field_rejected(self):
        """Extra keys are still forbidden after the additive change."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(unknown=1)  # type: ignore

    def test_default_japanese_filler_words_excludes_bare_sono(self):
        """Default `japanese_filler_words` MUST NOT contain bare `その`.

        Regression for change ``investigate-japanese-demonstrative-drop``:
        the bare demonstrative collides with content words.
        """
        defaults = PostProcessingConfig().japanese_filler_words
        assert "その" not in defaults
        assert "そのー" in defaults


class TestPostProcessingConfigMergeLeSplitValidator:
    """Validator from D7 / D8: merge_max_duration_ms <= split_max_duration_ms."""

    def test_equal_values_accepted(self):
        """Boundary case: merge == split is permitted."""
        cfg = PostProcessingConfig(
            merge_max_duration_ms=5000, split_max_duration_ms=5000
        )
        assert cfg.merge_max_duration_ms == 5000

    def test_merge_greater_than_split_rejected(self):
        """Validator raises when merge_max_duration_ms exceeds split_max_duration_ms."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(merge_max_duration_ms=8000, split_max_duration_ms=6000)


class TestHallucinationFilterConfigDefaults:
    """Defaults required by the HallucinationFilterConfig schema requirement."""

    def test_default_config_from_empty_dict(self):
        """`HallucinationFilterConfig()` MUST produce all spec-defined defaults."""
        cfg = HallucinationFilterConfig()
        assert cfg.enabled is True
        assert cfg.min_avg_logprob == -1.0
        assert cfg.max_no_speech_prob == 0.6
        assert cfg.max_compression_ratio == 2.4
        assert cfg.max_repetition_ratio == 0.5
        assert cfg.known_hallucination_phrases == [
            "ご視聴ありがとうございました",
            "ご視聴ありがとうございます",
            "おやすみなさい",
        ]
        assert cfg.phrase_match_enabled is True
        assert cfg.bracket_match_enabled is True
        assert cfg.repeat_match_enabled is True
        assert cfg.low_logprob_match_enabled is True
        assert cfg.compression_match_enabled is True
        assert cfg.repetition_match_enabled is True

    def test_known_hallucination_phrases_default_factory_isolated(self):
        """Two instances MUST NOT share the same list object (no mutable-default trap)."""
        cfg_a = HallucinationFilterConfig()
        cfg_b = HallucinationFilterConfig()
        assert (
            cfg_a.known_hallucination_phrases is not cfg_b.known_hallucination_phrases
        )

    def test_pipeline_config_with_empty_hallucination_filter_dict(self):
        """`PipelineConfig` parses `hallucination_filter: {}` to a default model instance."""
        cfg = PipelineConfig(
            transcribing=[{"condition": "true", "backend": "faster-whisper"}],
            hallucination_filter={},  # type: ignore[arg-type]
        )
        assert cfg.hallucination_filter is not None
        assert cfg.hallucination_filter.enabled is True
        assert cfg.hallucination_filter.min_avg_logprob == -1.0
        assert cfg.hallucination_filter.max_no_speech_prob == 0.6
        assert cfg.hallucination_filter.max_compression_ratio == 2.4
        assert cfg.hallucination_filter.max_repetition_ratio == 0.5

    def test_pipeline_config_missing_hallucination_filter_yields_none(self):
        """When `hallucination_filter` key is omitted, the field MUST be `None`."""
        cfg = PipelineConfig(
            transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        )
        assert cfg.hallucination_filter is None

    def test_hallucination_filter_unknown_field_rejected(self):
        """`extra='forbid'` is enforced on `HallucinationFilterConfig`."""
        with pytest.raises(pydantic.ValidationError):
            HallucinationFilterConfig(unknown=1)  # type: ignore[call-arg]


class TestPostProcessingConfigDedupAndJapaneseFields:
    """Defaults and validators for the dedup + Japanese fields requirement."""

    def test_default_fields_populated(self):
        """`PostProcessingConfig()` MUST expose all spec-defined defaults."""
        cfg = PostProcessingConfig()
        assert cfg.dedup_enabled is True
        assert cfg.dedup_similarity_threshold == 0.9
        assert cfg.dedup_max_gap_ms == 600
        assert cfg.japanese_filler_enabled is True
        assert cfg.japanese_repetition_enabled is True
        assert cfg.japanese_filler_words == [
            "あのー",
            "えーと",
            "えー",
            "そのー",
        ]
        assert cfg.japanese_onomatopoeia_whitelist == [
            "どきどき",
            "わくわく",
            "きらきら",
            "ぴかぴか",
        ]

    def test_japanese_filler_words_default_factory_isolated(self):
        """Two instances MUST NOT share the same filler-words list object."""
        cfg_a = PostProcessingConfig()
        cfg_b = PostProcessingConfig()
        assert cfg_a.japanese_filler_words is not cfg_b.japanese_filler_words

    def test_japanese_onomatopoeia_whitelist_default_factory_isolated(self):
        """Two instances MUST NOT share the same onomatopoeia list object."""
        cfg_a = PostProcessingConfig()
        cfg_b = PostProcessingConfig()
        assert (
            cfg_a.japanese_onomatopoeia_whitelist
            is not cfg_b.japanese_onomatopoeia_whitelist
        )

    def test_dedup_similarity_threshold_above_one_rejected(self):
        """`dedup_similarity_threshold=1.5` MUST raise `ValidationError`."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(dedup_similarity_threshold=1.5)

    def test_dedup_similarity_threshold_below_zero_rejected(self):
        """Negative similarity threshold MUST raise `ValidationError`."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(dedup_similarity_threshold=-0.1)

    def test_dedup_similarity_threshold_zero_accepted(self):
        """Boundary: `dedup_similarity_threshold=0.0` MUST be accepted."""
        cfg = PostProcessingConfig(dedup_similarity_threshold=0.0)
        assert cfg.dedup_similarity_threshold == 0.0

    def test_dedup_similarity_threshold_one_accepted(self):
        """Boundary: `dedup_similarity_threshold=1.0` MUST be accepted."""
        cfg = PostProcessingConfig(dedup_similarity_threshold=1.0)
        assert cfg.dedup_similarity_threshold == 1.0

    def test_dedup_max_gap_ms_negative_rejected(self):
        """`dedup_max_gap_ms=-1` MUST raise `ValidationError`."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(dedup_max_gap_ms=-1)

    def test_dedup_max_gap_ms_zero_accepted(self):
        """Boundary: `dedup_max_gap_ms=0` MUST be accepted."""
        cfg = PostProcessingConfig(dedup_max_gap_ms=0)
        assert cfg.dedup_max_gap_ms == 0

    def test_dedup_max_gap_ms_60000_accepted(self):
        """Boundary: `dedup_max_gap_ms=60_000` (1 minute) MUST be accepted."""
        cfg = PostProcessingConfig(dedup_max_gap_ms=60_000)
        assert cfg.dedup_max_gap_ms == 60_000

    def test_dedup_max_gap_ms_above_60000_rejected(self):
        """`dedup_max_gap_ms=60_001` MUST raise `ValidationError`."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(dedup_max_gap_ms=60_001)


class TestPostProcessingConfigJapaneseSplitBoundaryFields:
    """Defaults and validators for the Japanese split-boundary fields."""

    def test_default_japanese_split_search_radius(self):
        """`japanese_split_search_radius` defaults to 4."""
        assert PostProcessingConfig().japanese_split_search_radius == 4

    def test_default_no_split_units_contains_expected(self):
        """Defaults MUST contain the spec-required units."""
        units = PostProcessingConfig().japanese_split_no_split_units
        for u in ("まし", "です", "よう"):
            assert u in units

    def test_default_no_leading_particles_contains_expected(self):
        """Defaults MUST contain the spec-required particles."""
        particles = PostProcessingConfig().japanese_split_no_leading_particles
        for p in ("に", "を", "の"):
            assert p in particles

    def test_default_no_leading_finals_contains_expected(self):
        """Defaults MUST contain the spec-required finals."""
        finals = PostProcessingConfig().japanese_split_no_leading_finals
        for f in ("た", "い"):
            assert f in finals

    def test_japanese_split_search_radius_above_max_rejected(self):
        """`japanese_split_search_radius=21` MUST raise `ValidationError`."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(japanese_split_search_radius=25)

    def test_japanese_split_search_radius_negative_rejected(self):
        """Negative search radius MUST raise `ValidationError`."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(japanese_split_search_radius=-1)

    def test_japanese_split_search_radius_zero_accepted(self):
        """Boundary: `japanese_split_search_radius=0` MUST be accepted."""
        cfg = PostProcessingConfig(japanese_split_search_radius=0)
        assert cfg.japanese_split_search_radius == 0

    def test_japanese_split_search_radius_twenty_accepted(self):
        """Boundary: `japanese_split_search_radius=20` MUST be accepted."""
        cfg = PostProcessingConfig(japanese_split_search_radius=20)
        assert cfg.japanese_split_search_radius == 20

    def test_no_split_units_empty_string_rejected(self):
        """Empty entries in `japanese_split_no_split_units` MUST raise."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(japanese_split_no_split_units=["まし", ""])

    def test_no_leading_particles_empty_string_rejected(self):
        """Empty entries in `japanese_split_no_leading_particles` MUST raise."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(japanese_split_no_leading_particles=["", "に"])

    def test_no_leading_finals_empty_string_rejected(self):
        """Empty entries in `japanese_split_no_leading_finals` MUST raise."""
        with pytest.raises(pydantic.ValidationError):
            PostProcessingConfig(japanese_split_no_leading_finals=["た", ""])

    def test_japanese_split_lists_default_factory_isolated(self):
        """Two instances MUST NOT share the same Japanese-split list objects."""
        a = PostProcessingConfig()
        b = PostProcessingConfig()
        assert a.japanese_split_no_split_units is not b.japanese_split_no_split_units
        assert (
            a.japanese_split_no_leading_particles
            is not b.japanese_split_no_leading_particles
        )
        assert (
            a.japanese_split_no_leading_finals is not b.japanese_split_no_leading_finals
        )


class TestHallucinationFilterAllRulesDisabled:
    """Reject `enabled=True` while every per-rule toggle is False (silent no-op guard)."""

    def test_enabled_false_with_all_rules_false_accepted(self):
        """`enabled=False` plus all rules off is the disabled-stage path; MUST be accepted."""
        cfg = HallucinationFilterConfig(
            enabled=False,
            phrase_match_enabled=False,
            bracket_match_enabled=False,
            repeat_match_enabled=False,
            low_logprob_match_enabled=False,
            compression_match_enabled=False,
            repetition_match_enabled=False,
        )
        assert cfg.enabled is False

    def test_enabled_true_with_all_rules_false_rejected(self):
        """`enabled=True` with every per-rule toggle False MUST raise `ValidationError`."""
        with pytest.raises(pydantic.ValidationError):
            HallucinationFilterConfig(
                enabled=True,
                phrase_match_enabled=False,
                bracket_match_enabled=False,
                repeat_match_enabled=False,
                low_logprob_match_enabled=False,
                compression_match_enabled=False,
                repetition_match_enabled=False,
            )

    def test_enabled_true_with_one_rule_true_accepted(self):
        """`enabled=True` with at least one per-rule toggle True MUST be accepted."""
        cfg = HallucinationFilterConfig(
            enabled=True,
            phrase_match_enabled=True,
            bracket_match_enabled=False,
            repeat_match_enabled=False,
            low_logprob_match_enabled=False,
            compression_match_enabled=False,
            repetition_match_enabled=False,
        )
        assert cfg.enabled is True
        assert cfg.phrase_match_enabled is True


class TestHallucinationFilterPhrasesCleanup:
    """`known_hallucination_phrases` strips whitespace and drops empty entries."""

    def test_empty_and_whitespace_entries_filtered(self):
        """Empty and whitespace-only entries are dropped; valid entries are stripped."""
        cfg = HallucinationFilterConfig(
            known_hallucination_phrases=[
                "",
                "   ",
                "ご視聴ありがとうございました",
                "  hello  ",
            ]
        )
        assert cfg.known_hallucination_phrases == [
            "ご視聴ありがとうございました",
            "hello",
        ]

    def test_empty_list_accepted_as_is(self):
        """An explicit empty list overrides the default to disable phrase matching."""
        cfg = HallucinationFilterConfig(known_hallucination_phrases=[])
        assert cfg.known_hallucination_phrases == []

    def test_default_list_unchanged(self):
        """Default phrase list has no whitespace-only entries to strip."""
        cfg = HallucinationFilterConfig()
        assert cfg.known_hallucination_phrases == [
            "ご視聴ありがとうございました",
            "ご視聴ありがとうございます",
            "おやすみなさい",
        ]


class TestPipelineConfigExpectedLanguageNormalisation:
    """`PipelineConfig.expected_language` is normalised to canonical lowercase BCP-47 base tag."""

    def test_lowercase_base_tag_unchanged(self):
        """`expected_language='ja'` MUST be stored as `'ja'` (idempotent)."""
        cfg = PipelineConfig(
            expected_language="ja",
            transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        )
        assert cfg.expected_language == "ja"

    def test_uppercase_base_tag_lowercased(self):
        """`expected_language='JA'` MUST be normalised to `'ja'`."""
        cfg = PipelineConfig(
            expected_language="JA",
            transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        )
        assert cfg.expected_language == "ja"

    def test_region_subtag_stripped(self):
        """`expected_language='ja-JP'` MUST be normalised to `'ja'`."""
        cfg = PipelineConfig(
            expected_language="ja-JP",
            transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        )
        assert cfg.expected_language == "ja"

    def test_whitespace_and_case_and_region_normalised(self):
        """`expected_language='  En-US  '` MUST be normalised to `'en'`."""
        cfg = PipelineConfig(
            expected_language="  En-US  ",
            transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        )
        assert cfg.expected_language == "en"

    def test_none_passes_through(self):
        """`expected_language=None` MUST be stored as `None`."""
        cfg = PipelineConfig(
            expected_language=None,
            transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        )
        assert cfg.expected_language is None


class TestHallucinationFilterConfigRoundtrip:
    """Round-trip test for HallucinationFilterConfig (kept separate to preserve grouping)."""

    def test_hallucination_filter_roundtrip(self):
        """Model round-trip via `model_dump()`/re-instantiation preserves all fields."""
        cfg = HallucinationFilterConfig(
            enabled=False,
            min_avg_logprob=-0.5,
            max_no_speech_prob=0.7,
            max_compression_ratio=2.0,
            max_repetition_ratio=0.3,
            known_hallucination_phrases=["foo", "bar"],
            phrase_match_enabled=False,
            bracket_match_enabled=False,
            repeat_match_enabled=False,
            low_logprob_match_enabled=False,
            compression_match_enabled=False,
            repetition_match_enabled=False,
        )
        dumped = cfg.model_dump()
        restored = HallucinationFilterConfig(**dumped)
        assert restored == cfg
