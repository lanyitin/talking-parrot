"""End-to-end smoke test: CLI load config → hash → empty stage run → JSON output."""

import json
import textwrap
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent
SAMPLE_AUDIO = str(PROJECT_ROOT / "test-samples/sample1/base.mp3")

FIXTURE_YAML = textwrap.dedent("""\
    expected_language: en
    transcribing:
      - condition: "true"
        backend: faster-whisper
    """)


@pytest.fixture
def config_file(tmp_path):
    f = tmp_path / "pipeline.yaml"
    f.write_text(FIXTURE_YAML)
    return str(f)


@pytest.fixture
def output_file(tmp_path):
    return str(tmp_path / "output.json")


class TestPipelineSmokeFlow:
    def test_cli_produces_valid_json(self, config_file, output_file):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "talking_parrot.cli",
                SAMPLE_AUDIO,
                "--config",
                config_file,
                "--output",
                output_file,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
        with open(output_file) as fh:
            data = json.loads(fh.read())
        assert data is not None

    def test_output_contains_media_hash(self, config_file, output_file):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "talking_parrot.cli",
                SAMPLE_AUDIO,
                "--config",
                config_file,
                "--output",
                output_file,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        with open(output_file) as fh:
            data = json.load(fh)
        assert "media" in data
        assert "sha256" in data["media"]
        sha256 = data["media"]["sha256"]
        assert len(sha256) == 64
        assert sha256 == sha256.lower()

    def test_output_contains_config_snapshot(self, config_file, output_file):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "talking_parrot.cli",
                SAMPLE_AUDIO,
                "--config",
                config_file,
                "--output",
                output_file,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        with open(output_file) as fh:
            data = json.load(fh)
        assert "config" in data
        cfg = data["config"]
        assert "transcribing" in cfg
        assert cfg["transcribing"][0]["condition"] == "true"
