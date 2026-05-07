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

# Full six-stage YAML exercising VAD + chunking + transcribing +
# hallucination_filter + align + post_processing. Hallucination thresholds
# are kept lenient so the filter does not strip every segment from the
# short test sample (which has only one short Japanese utterance).
FIXTURE_YAML_FULL_SIX_STAGES = textwrap.dedent("""\
    expected_language: ja
    vad:
      enabled: true
    chunking:
      enabled: true
    transcribing:
      - condition: "true"
        backend: faster-whisper
    hallucination_filter:
      enabled: true
      min_avg_logprob: -10.0
      max_no_speech_prob: 0.99
      max_compression_ratio: 100.0
      max_repetition_ratio: 1.0
      phrase_match_enabled: false
      bracket_match_enabled: false
      repeat_match_enabled: false
      # At least one rule must be enabled when `enabled: true`
      # (HallucinationFilterConfig validator). The thresholds above are
      # set permissively (-10.0 logprob) so this rule still effectively
      # filters nothing from the short test sample.
      low_logprob_match_enabled: true
      compression_match_enabled: false
      repetition_match_enabled: false
    align:
      # `enabled: false` keeps AlignmentStage wired into the orchestrator
      # (because `cfg.align is not None`) while letting the stage's
      # internal short-circuit skip the heavy backend. We still get a
      # six-stage pipeline; the alignment-specific contract is covered by
      # tests/unit/stages/test_alignment_stage.py.
      enabled: false
      granularity: AUTO
    post_processing:
      enabled: true
    """)


@pytest.fixture
def config_file(tmp_path):
    f = tmp_path / "pipeline.yaml"
    f.write_text(FIXTURE_YAML)
    return str(f)


@pytest.fixture
def output_file(tmp_path):
    return str(tmp_path / "output.json")


@pytest.fixture
def config_file_full_six_stages(tmp_path):
    """Config file enabling all six pipeline stages."""
    f = tmp_path / "pipeline_full.yaml"
    f.write_text(FIXTURE_YAML_FULL_SIX_STAGES)
    return str(f)


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


class TestPipelineSmokeFullSixStages:
    """Smoke test exercising all six pipeline stages end-to-end.

    Guards the ``pipeline-end-to-end-wiring`` contract: when a config
    populates all six optional sections, the orchestrator runs without
    error, the ``HallucinationFilterStage`` is actually invoked, and the
    resulting ``PipelineContext`` carries ``subtitles`` through to the
    project-JSON output.
    """

    def test_six_stage_pipeline_runs_and_invokes_hallucination_filter(
        self, config_file_full_six_stages, output_file
    ):
        """Run the CLI with all six stages; verify completion and filter activation."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "talking_parrot.cli",
                SAMPLE_AUDIO,
                "--config",
                config_file_full_six_stages,
                "--output",
                output_file,
                "--log-level",
                "INFO",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"CLI failed (stdout={result.stdout!r} stderr={result.stderr!r})"
        )

        # The orchestrator logs `stage=<name>` at INFO level for every stage
        # boundary; this is the simplest cross-process witness that the
        # HallucinationFilterStage was wired into the orchestrator's stage
        # list and actually executed.
        log_blob = result.stdout + result.stderr
        assert "hallucination_filter" in log_blob, (
            "HallucinationFilterStage was not invoked by the orchestrator. "
            f"Combined log output: {log_blob!r}"
        )

        with open(output_file) as fh:
            data = json.load(fh)
        # All six stages ran; the project file MUST round-trip and carry
        # the populated subtitles list (D7: subtitles flow from the
        # PostProcessingStage into the project file).
        assert "subtitles" in data
        assert isinstance(data["subtitles"], list)
        assert len(data["subtitles"]) > 0, (
            "subtitles should be populated after the six-stage run; "
            f"project payload: {data!r}"
        )
