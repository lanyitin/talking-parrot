import pytest
import pydantic

from talking_parrot.config.models import (
    PipelineConfig,
    VadConfig,
    ChunkingConfig,
    AlignConfig,
    PostProcessingConfig,
    TranscribingStep,
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
