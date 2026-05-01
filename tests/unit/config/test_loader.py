import textwrap
import pytest
import pydantic

from talking_parrot.config.loader import ConfigLoader
from talking_parrot.config.models import PipelineConfig


VALID_YAML = textwrap.dedent("""\
    expected_language: en
    transcribing:
      - condition: "true"
        backend: faster-whisper
    """)

UNKNOWN_FIELD_YAML = textwrap.dedent("""\
    transcribing:
      - condition: "true"
        backend: faster-whisper
    unknown_key: bad
    """)

NON_TRUE_CONDITION_YAML = textwrap.dedent("""\
    transcribing:
      - condition: "avg_logprob < -1.0"
        backend: faster-whisper
    """)

EMPTY_TRANSCRIBING_YAML = textwrap.dedent("""\
    transcribing: []
    """)

FULL_YAML = textwrap.dedent("""\
    expected_language: ja
    vad:
      enabled: true
      max_speech_duration_ms: 60000
    chunking:
      enabled: true
      max_chunk_seconds: 30
    transcribing:
      - condition: "true"
        backend: faster-whisper
        model: large-v3
    align:
      enabled: true
      granularity: AUTO
    post_processing:
      enabled: true
    """)


class TestConfigLoaderParsesYAML:
    def test_valid_yaml_returns_pipeline_config(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(VALID_YAML)
        cfg = ConfigLoader.load(str(f))
        assert isinstance(cfg, PipelineConfig)
        assert cfg.expected_language == "en"
        assert len(cfg.transcribing) == 1

    def test_full_yaml_populates_sub_sections(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(FULL_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.vad is not None
        assert cfg.chunking is not None
        assert cfg.align is not None
        assert cfg.post_processing is not None


class TestConfigLoaderRejectsUnknownFields:
    def test_unknown_top_level_field_raises(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(UNKNOWN_FIELD_YAML)
        with pytest.raises(pydantic.ValidationError):
            ConfigLoader.load(str(f))

    def test_vad_unknown_field_raises(self, tmp_path):
        yaml = textwrap.dedent("""\
            transcribing:
              - condition: "true"
                backend: faster-whisper
            vad:
              activty_threshold: 0.5
            """)
        f = tmp_path / "config.yaml"
        f.write_text(yaml)
        with pytest.raises(pydantic.ValidationError):
            ConfigLoader.load(str(f))


class TestFirstTranscribingCondition:
    def test_non_true_first_condition_raises(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(NON_TRUE_CONDITION_YAML)
        with pytest.raises(pydantic.ValidationError):
            ConfigLoader.load(str(f))

    def test_true_first_condition_accepted(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(VALID_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.transcribing[0].condition == "true"


class TestEmptyTranscribing:
    def test_empty_transcribing_list_raises(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(EMPTY_TRANSCRIBING_YAML)
        with pytest.raises(pydantic.ValidationError):
            ConfigLoader.load(str(f))
