import textwrap
import pytest
import pydantic

from talking_parrot.config.loader import ConfigLoader
from talking_parrot.config.models import PipelineConfig
from talking_parrot.transcription.factory import TranscriptionBackendFactory


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


class TestTranscribingBackendPlatformDefault:
    """`TranscribingStep.backend` is optional with platform-aware default (loader-resolved).

    See spec: pipeline-config / "TranscribingStep.backend is optional with platform-aware default".
    """

    OMITTED_BACKEND_YAML = textwrap.dedent("""\
        transcribing:
          - condition: "true"
            model: large-v3
        """)

    NULL_BACKEND_YAML = textwrap.dedent("""\
        transcribing:
          - condition: "true"
            backend: null
            model: large-v3
        """)

    EXPLICIT_BACKEND_YAML = textwrap.dedent("""\
        transcribing:
          - condition: "true"
            backend: faster-whisper
            model: large-v3
        """)

    MIXED_CASCADE_YAML = textwrap.dedent("""\
        transcribing:
          - condition: "true"
            model: large-v3
          - condition: "avg_logprob < -1.0"
            backend: whisper
            model: large-v3
        """)

    def test_omitted_backend_resolves_to_platform_default(self, tmp_path, monkeypatch):
        """Scenario: Omitted backend resolves to platform default."""
        monkeypatch.setattr(
            TranscriptionBackendFactory,
            "default_for_platform",
            staticmethod(lambda: "mlx-whisper"),
        )
        f = tmp_path / "config.yaml"
        f.write_text(self.OMITTED_BACKEND_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.transcribing[0].backend == "mlx-whisper"

    def test_explicit_backend_value_preserved(self, tmp_path, monkeypatch):
        """Scenario: Explicit backend value preserved (platform default does NOT override)."""
        monkeypatch.setattr(
            TranscriptionBackendFactory,
            "default_for_platform",
            staticmethod(lambda: "mlx-whisper"),
        )
        f = tmp_path / "config.yaml"
        f.write_text(self.EXPLICIT_BACKEND_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.transcribing[0].backend == "faster-whisper"

    def test_null_backend_resolves_to_platform_default(self, tmp_path, monkeypatch):
        """Scenario: Null backend resolves to platform default."""
        monkeypatch.setattr(
            TranscriptionBackendFactory,
            "default_for_platform",
            staticmethod(lambda: "faster-whisper"),
        )
        f = tmp_path / "config.yaml"
        f.write_text(self.NULL_BACKEND_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.transcribing[0].backend == "faster-whisper"

    def test_mixed_cascade_resolves_only_omitted_step(self, tmp_path, monkeypatch):
        """Scenario: Mixed cascade — step 0 (omitted) resolved; step 1 (explicit) preserved."""
        monkeypatch.setattr(
            TranscriptionBackendFactory,
            "default_for_platform",
            staticmethod(lambda: "mlx-whisper"),
        )
        f = tmp_path / "config.yaml"
        f.write_text(self.MIXED_CASCADE_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.transcribing[0].backend == "mlx-whisper"
        assert cfg.transcribing[1].backend == "whisper"

    @pytest.mark.parametrize(
        "sys_platform,machine,expected",
        [
            ("darwin", "arm64", "mlx-whisper"),
            ("darwin", "x86_64", "faster-whisper"),
            ("linux", "x86_64", "faster-whisper"),
            ("win32", "AMD64", "faster-whisper"),
        ],
    )
    def test_platform_resolution_table(
        self, tmp_path, monkeypatch, sys_platform, machine, expected
    ):
        """Example: platform resolution table — drives `default_for_platform()` via stdlib."""
        monkeypatch.setattr("sys.platform", sys_platform)
        monkeypatch.setattr("platform.machine", lambda: machine)
        f = tmp_path / "config.yaml"
        f.write_text(self.OMITTED_BACKEND_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.transcribing[0].backend == expected
