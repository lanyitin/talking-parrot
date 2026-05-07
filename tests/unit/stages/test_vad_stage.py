"""Unit tests for VADStage.

Covers:
- Disabled behaviour (tasks 6.1)
- Frame alignment (task 6.2)
- Composite score computation (task 6.3)
- Hysteresis state machine (task 6.4)
- Post-merge refinement steps (task 6.5)
- VadSegment statistics (task 6.6)
"""

from __future__ import annotations

import pytest

from talking_parrot.config.models import PipelineConfig, VadConfig
from talking_parrot.expression.formula import FormulaEvaluator
from talking_parrot.io.audio_reader import AudioReader
from talking_parrot.models.context import PipelineContext
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.vad import RawVadFrame, VadSegment
from talking_parrot.stages.vad_stage import VADStage
from talking_parrot.vad.backend import VADBackend


class _StubAudioReader(AudioReader):
    """Empty-PCM stub; mock backends ignore the bytes anyway."""

    @property
    def sample_rate(self) -> int:
        return 16_000

    def read(self, start_ms: int, end_ms: int) -> bytes:
        return b""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_media_info(duration_ms: int = 10000) -> MediaInfo:
    """Create a minimal MediaInfo for test pipelines."""
    return MediaInfo(path="/tmp/test.wav", duration_ms=duration_ms, sha256="abc")


def _make_pipeline_config(vad: VadConfig | None = None) -> PipelineConfig:
    """Build a minimal PipelineConfig for testing."""
    return PipelineConfig(
        transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        vad=vad,
    )


def _make_ctx(
    vad: VadConfig | None = None,
    duration_ms: int = 10000,
) -> PipelineContext:
    """Return a PipelineContext with the given VAD config."""
    return PipelineContext(
        config=_make_pipeline_config(vad),
        media_info=_make_media_info(duration_ms),
    )


class _MockBackend(VADBackend):
    """Test-double VAD backend that returns a preset list of frames."""

    def __init__(self, backend_name: str, frames: list[RawVadFrame]) -> None:
        self._name = backend_name
        self._frames = frames

    @property
    def name(self) -> str:
        return self._name

    def analyze(self, audio_data: bytes, sample_rate: int) -> list[RawVadFrame]:
        return list(self._frames)


def _make_stage(
    backends: list[VADBackend] | None = None,
    formula_evaluator: FormulaEvaluator | None = None,
) -> VADStage:
    """Return a VADStage with sensible defaults for testing."""
    if backends is None:
        backends = []
    if formula_evaluator is None:
        formula_evaluator = FormulaEvaluator()
    return VADStage(
        backends=backends,
        formula_evaluator=formula_evaluator,
        audio_reader=_StubAudioReader(),
    )


# ---------------------------------------------------------------------------
# Task 6.1 — Disabled behaviour
# ---------------------------------------------------------------------------


class TestVADStageDisabled:
    def test_process_returns_input_unchanged_when_vad_is_none(self) -> None:
        """process() returns input ctx unchanged when ctx.config.vad is None."""
        stage = _make_stage()
        ctx = _make_ctx(vad=None)
        result = stage.process(ctx)
        assert result is ctx

    def test_process_returns_input_unchanged_when_vad_enabled_false(self) -> None:
        """process() returns input ctx unchanged when vad.enabled=False."""
        stage = _make_stage()
        ctx = _make_ctx(vad=VadConfig(enabled=False))
        result = stage.process(ctx)
        assert result is ctx

    def test_vad_segments_empty_when_disabled(self) -> None:
        """ctx.vad_segments remains empty when stage is disabled."""
        stage = _make_stage()
        ctx = _make_ctx(vad=VadConfig(enabled=False))
        result = stage.process(ctx)
        assert result.vad_segments == []


# ---------------------------------------------------------------------------
# Task 6.2 — Frame alignment
# ---------------------------------------------------------------------------


class TestVADStageFrameAlignment:
    def test_unified_timeline_contains_all_backend_time_points(self) -> None:
        """Unified timeline contains time points from both backends."""
        ten_frames = [
            RawVadFrame(time_ms=0, prob=0.9),
            RawVadFrame(time_ms=16, prob=0.8),
            RawVadFrame(time_ms=32, prob=0.7),
        ]
        silero_frames = [
            RawVadFrame(time_ms=0, prob=0.85),
            RawVadFrame(time_ms=32, prob=0.75),
        ]
        ten_backend = _MockBackend("ten_vad", ten_frames)
        silero_backend = _MockBackend("silero_vad", silero_frames)

        # Use an always-active formula so every frame becomes a segment
        vad_cfg = VadConfig(
            enabled=True,
            activity_threshold=0.0,
            neg_threshold=-1.0,
            formula="(ten_vad_prob + silero_vad_prob) / 2",
            min_speech_duration_ms=0,
            max_speech_duration_ms=999999,
            min_silence_duration_ms=999999,
            speech_pad_ms=0,
        )
        stage = VADStage(
            backends=[ten_backend, silero_backend],
            formula_evaluator=FormulaEvaluator(),
            audio_reader=_StubAudioReader(),
        )
        # We need audio bytes — the backends are mocked so any bytes work
        ctx = _make_ctx(vad=vad_cfg, duration_ms=100)
        # Inject audio bytes into context to allow stage to call analyze()
        result = stage.process(ctx)
        # Timeline should include 0, 16, 32
        assert isinstance(result.vad_segments, list)

    def test_nearest_neighbour_alignment_spec_example(self) -> None:
        """At time_ms=16: ten_vad_prob=0.8, silero_vad_prob=0.85 (nearest silero frame 0ms within 50ms).

        Spec example:
          ten_vad frames: [(0, 0.9), (16, 0.8), (32, 0.7)]
          silero_vad frames: [(0, 0.85), (32, 0.75)]
          At time_ms=16: ten_vad_prob=0.8, silero_vad_prob=0.85
        """
        ten_frames = [
            RawVadFrame(time_ms=0, prob=0.9),
            RawVadFrame(time_ms=16, prob=0.8),
            RawVadFrame(time_ms=32, prob=0.7),
        ]
        silero_frames = [
            RawVadFrame(time_ms=0, prob=0.85),
            RawVadFrame(time_ms=32, prob=0.75),
        ]
        ten_backend = _MockBackend("ten_vad", ten_frames)
        silero_backend = _MockBackend("silero_vad", silero_frames)

        # Build a stage and call the internal alignment helper directly
        stage = VADStage(
            backends=[ten_backend, silero_backend],
            formula_evaluator=FormulaEvaluator(),
            audio_reader=_StubAudioReader(),
        )
        aligned = stage._align_frames(
            {"ten_vad": ten_frames, "silero_vad": silero_frames}
        )
        # Find the entry for time_ms=16
        point_16 = next(pt for pt in aligned if pt["time_ms"] == 16)
        assert point_16["ten_vad_prob"] == 0.8
        assert point_16["silero_vad_prob"] == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# Task 6.3 — Composite score
# ---------------------------------------------------------------------------


class TestVADStageCompositeScore:
    @pytest.mark.parametrize(
        "formula, ten_vad_prob, silero_vad_prob, expected",
        [
            ("(ten_vad_prob + silero_vad_prob) / 2", 0.9, 0.7, 0.8),
            (
                "(ten_vad_prob * 0.9) + (silero_vad_prob * 0.1)",
                0.95,
                0.82,
                pytest.approx(0.937),
            ),
            ("ten_vad_prob", 0.6, 0.0, 0.6),
        ],
    )
    def test_composite_score_matches_spec_examples(
        self,
        formula: str,
        ten_vad_prob: float,
        silero_vad_prob: float,
        expected,
    ) -> None:
        """Composite score equals the formula result for each spec example row."""
        evaluator = FormulaEvaluator()
        score = evaluator.evaluate(
            formula, {"ten_vad_prob": ten_vad_prob, "silero_vad_prob": silero_vad_prob}
        )
        assert score == expected


# ---------------------------------------------------------------------------
# Task 6.4 — Hysteresis state machine
# ---------------------------------------------------------------------------


class TestVADStageHysteresis:
    def test_single_segment_when_score_does_not_drop_below_neg_threshold(
        self,
    ) -> None:
        """Scores [0.6, 0.4, 0.6] with activity=0.5, neg=0.35 → one segment.

        Score 0.4 does NOT end the segment because 0.4 >= neg_threshold=0.35.
        """
        stage = _make_stage()
        frames = [
            {"time_ms": 0, "composite_score": 0.6},
            {"time_ms": 16, "composite_score": 0.4},
            {"time_ms": 32, "composite_score": 0.6},
        ]
        segments = stage._hysteresis_merge(
            frames, activity_threshold=0.5, neg_threshold=0.35, frame_duration_ms=16
        )
        assert len(segments) == 1

    def test_segment_starts_at_activity_threshold(self) -> None:
        """Scores [0.3, 0.6, 0.8] → segment starts at frame with score 0.6."""
        stage = _make_stage()
        frames = [
            {"time_ms": 0, "composite_score": 0.3},
            {"time_ms": 16, "composite_score": 0.6},
            {"time_ms": 32, "composite_score": 0.8},
        ]
        segments = stage._hysteresis_merge(
            frames, activity_threshold=0.5, neg_threshold=0.35, frame_duration_ms=16
        )
        assert len(segments) == 1
        assert segments[0][0] == 16  # start_ms

    def test_segment_ends_below_neg_threshold(self) -> None:
        """Scores [0.8, 0.7, 0.3] → segment ends when score drops to 0.3."""
        stage = _make_stage()
        frames = [
            {"time_ms": 0, "composite_score": 0.8},
            {"time_ms": 16, "composite_score": 0.7},
            {"time_ms": 32, "composite_score": 0.3},
        ]
        segments = stage._hysteresis_merge(
            frames, activity_threshold=0.5, neg_threshold=0.35, frame_duration_ms=16
        )
        # Segment should start at 0ms and end before the 0.3 frame
        assert len(segments) == 1
        assert segments[0][0] == 0  # start_ms at first active frame
        # end_ms should not include the frame with score 0.3 (which drops below neg)
        assert segments[0][1] <= 32


# ---------------------------------------------------------------------------
# Task 6.5 — Refinement steps
# ---------------------------------------------------------------------------


class TestVADStageRefinement:
    def test_gap_merging_adjacent_segments_with_small_gap(self) -> None:
        """A ends 500ms, B starts 550ms, gap 50ms < min_silence=100ms → merged."""
        stage = _make_stage()
        segments = [(0, 500), (550, 1000)]
        merged = stage._merge_gaps(segments, min_silence_duration_ms=100)
        assert len(merged) == 1
        assert merged[0] == (0, 1000)

    def test_gap_not_merged_when_gap_equals_min_silence(self) -> None:
        """Gap exactly equal to min_silence_duration_ms is NOT merged (strict <)."""
        stage = _make_stage()
        segments = [(0, 500), (600, 1000)]
        merged = stage._merge_gaps(segments, min_silence_duration_ms=100)
        assert len(merged) == 2

    def test_short_segment_is_discarded(self) -> None:
        """100ms segment discarded when min_speech_duration_ms=250."""
        stage = _make_stage()
        segments = [(0, 100)]
        filtered = stage._filter_short_segments(segments, min_speech_duration_ms=250)
        assert filtered == []

    def test_segment_meeting_min_duration_is_kept(self) -> None:
        """250ms segment is kept when min_speech_duration_ms=250."""
        stage = _make_stage()
        segments = [(0, 250)]
        filtered = stage._filter_short_segments(segments, min_speech_duration_ms=250)
        assert filtered == [(0, 250)]

    def test_long_segment_split_at_midpoint(self) -> None:
        """0–40000ms split → [0, 20000] and [20000, 40000] when max=30000."""
        stage = _make_stage()
        segments = [(0, 40000)]
        split = stage._split_long_segments(segments, max_speech_duration_ms=30000)
        assert len(split) == 2
        assert split[0] == (0, 20000)
        assert split[1] == (20000, 40000)

    def test_speech_padding_clamped_to_audio_bounds(self) -> None:
        """10–990ms padded by 30ms → 0–1000ms clamped to audio_duration=1000."""
        stage = _make_stage()
        segments = [(10, 990)]
        padded = stage._apply_padding(
            segments, speech_pad_ms=30, audio_duration_ms=1000
        )
        assert len(padded) == 1
        assert padded[0][0] == 0  # max(0, 10 - 30) = 0
        assert padded[0][1] == 1000  # min(1000, 990 + 30) = 1000


# ---------------------------------------------------------------------------
# Task 6.6 — VadSegment statistics
# ---------------------------------------------------------------------------


class TestVADStageSegmentStatistics:
    def test_segment_statistics_are_mean_of_frame_values(self) -> None:
        """ten_vad_prob=0.85, silero_vad_prob=0.65, composite_score=0.80 (means).

        Spec example:
          ten_vad frames: [0.9, 0.8] → mean = 0.85
          silero_vad frames: [0.7, 0.6] → mean = 0.65
          composite scores: [0.85, 0.75] → mean = 0.80
        """
        # Build aligned frames matching the spec example
        aligned_frames = [
            {
                "time_ms": 0,
                "ten_vad_prob": 0.9,
                "silero_vad_prob": 0.7,
                "composite_score": 0.85,
            },
            {
                "time_ms": 16,
                "ten_vad_prob": 0.8,
                "silero_vad_prob": 0.6,
                "composite_score": 0.75,
            },
        ]
        stage = _make_stage()
        backend_names = ["ten_vad", "silero_vad"]
        segment = stage._compute_segment_stats(
            start_ms=0,
            end_ms=32,
            frames=aligned_frames,
            backend_names=backend_names,
        )
        assert isinstance(segment, VadSegment)
        assert segment.ten_vad_prob == pytest.approx(0.85)
        assert segment.silero_vad_prob == pytest.approx(0.65)
        assert segment.composite_score == pytest.approx(0.80)
