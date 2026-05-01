import textwrap
import logging

from talking_parrot.config.loader import ConfigLoader


INCONSISTENT_YAML = textwrap.dedent("""\
    transcribing:
      - condition: "true"
        backend: faster-whisper
    vad:
      enabled: true
      max_speech_duration_ms: 60000
    chunking:
      enabled: true
      max_chunk_seconds: 30
    """)

CONSISTENT_YAML = textwrap.dedent("""\
    transcribing:
      - condition: "true"
        backend: faster-whisper
    vad:
      enabled: true
      max_speech_duration_ms: 25000
    chunking:
      enabled: true
      max_chunk_seconds: 30
    """)


class TestInconsistentVadChunkingWarning:
    def test_warns_when_vad_ms_exceeds_chunk_ms(self, tmp_path, caplog):
        f = tmp_path / "config.yaml"
        f.write_text(INCONSISTENT_YAML)
        with caplog.at_level(logging.WARNING):
            cfg = ConfigLoader.load(str(f))
        assert cfg is not None
        # Should contain both values or at minimum the word "warning" was emitted
        assert any(
            "60000" in r.message or "30" in r.message
            for r in caplog.records
            if r.levelno >= logging.WARNING
        ), "Expected a WARNING log mentioning the inconsistent values"

    def test_does_not_raise_on_inconsistency(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(INCONSISTENT_YAML)
        cfg = ConfigLoader.load(str(f))
        assert cfg.vad is not None

    def test_no_warning_when_consistent(self, tmp_path, caplog):
        f = tmp_path / "config.yaml"
        f.write_text(CONSISTENT_YAML)
        with caplog.at_level(logging.WARNING):
            ConfigLoader.load(str(f))
        # No WARNING records about inconsistency
        inconsistency_warnings = [
            r
            for r in caplog.records
            if r.levelno >= logging.WARNING
            and ("25000" in r.message or "max_speech" in r.message)
        ]
        assert len(inconsistency_warnings) == 0
