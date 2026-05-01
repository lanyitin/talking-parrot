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
