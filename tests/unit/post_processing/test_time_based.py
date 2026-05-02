"""Tests for the time-based fallback post-processors.

Spec: ``time-based-processors``. Design: D5 (merge), D6 (split fallback).
"""

from __future__ import annotations

import logging

import pytest

from talking_parrot.config.models import PostProcessingConfig
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.time_based import (
    TimeBasedMergeProcessor,
    TimeBasedSplitProcessor,
)


@pytest.fixture
def cfg() -> PostProcessingConfig:
    """Default test config."""
    return PostProcessingConfig(
        max_line_length=40,
        max_lines_per_subtitle=2,
        merge_gap_threshold_ms=200,
        merge_max_duration_ms=6000,
        split_max_duration_ms=6000,
    )


class TestTimeBasedMerge:
    """Spec: TimeBasedMergeProcessor merges adjacent cues using only time/length."""

    def test_two_adjacent_cues_merged_with_single_space(self, cfg):
        """Spec scenario: ``[("hello",0,500),("world",600,1200)]`` → one cue."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="hello"),
            Subtitle(index=2, start_ms=600, end_ms=1200, text="world"),
        ]
        out = TimeBasedMergeProcessor().process(subs, cfg)
        assert out == [
            Subtitle(index=1, start_ms=0, end_ms=1200, text="hello world"),
        ]

    def test_gap_exceeding_threshold_prevents_merge(self, cfg):
        """A 500ms gap with threshold 200ms must not merge."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=1000, text="a"),
            Subtitle(index=2, start_ms=1500, end_ms=2000, text="b"),
        ]
        out = TimeBasedMergeProcessor().process(subs, cfg)
        assert len(out) == 2
        assert out[0].text == "a"
        assert out[1].text == "b"

    def test_merge_max_duration_cap_prevents_merge(self, cfg):
        """Total duration > merge_max_duration_ms must not merge."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=4000, text="a"),
            Subtitle(index=2, start_ms=4100, end_ms=8000, text="b"),
        ]
        out = TimeBasedMergeProcessor().process(subs, cfg)
        assert len(out) == 2

    def test_length_cap_prevents_merge(self, cfg):
        """Concatenated text exceeding max_line_length * max_lines must not merge."""
        narrow = PostProcessingConfig(
            max_line_length=10,
            max_lines_per_subtitle=1,
            merge_gap_threshold_ms=200,
            merge_max_duration_ms=6000,
            split_max_duration_ms=6000,
        )
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="aaaaa"),
            Subtitle(index=2, start_ms=600, end_ms=1100, text="bbbbb"),
        ]
        # 5 + 1 + 5 = 11 > 10 → no merge
        out = TimeBasedMergeProcessor().process(subs, narrow)
        assert len(out) == 2

    def test_cascade_merge_three_cues(self, cfg):
        """Three eligible cues collapse into one in a single left-to-right pass."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="a"),
            Subtitle(index=2, start_ms=600, end_ms=1100, text="b"),
            Subtitle(index=3, start_ms=1200, end_ms=1700, text="c"),
        ]
        out = TimeBasedMergeProcessor().process(subs, cfg)
        assert out == [Subtitle(index=1, start_ms=0, end_ms=1700, text="a b c")]

    def test_empty_input(self, cfg):
        """Empty input returns empty list."""
        assert TimeBasedMergeProcessor().process([], cfg) == []


class TestTimeBasedSplit:
    """Spec: TimeBasedSplitProcessor splits oversized cues proportionally."""

    def test_long_cue_split_into_two(self, cfg):
        """Spec scenario: 12s cue with 19 chars → two halves (0–6000) and (6000–12000)."""
        sub = Subtitle(index=1, start_ms=0, end_ms=12000, text="the quick brown fox")
        out = TimeBasedSplitProcessor().process([sub], cfg)
        assert len(out) == 2
        assert (out[0].start_ms, out[0].end_ms) == (0, 6000)
        assert (out[1].start_ms, out[1].end_ms) == (6000, 12000)
        assert out[0].text + out[1].text == "the quick brown fox"
        assert out[0].index == 1 and out[1].index == 2

    def test_cue_under_threshold_unchanged(self, cfg):
        """A cue shorter than the cap passes through with index renumbered."""
        sub = Subtitle(index=7, start_ms=0, end_ms=3000, text="ok")
        out = TimeBasedSplitProcessor().process([sub], cfg)
        assert len(out) == 1
        assert out[0].text == "ok"
        assert out[0].start_ms == 0
        assert out[0].end_ms == 3000
        assert out[0].index == 1

    def test_unsplittable_cue_logs_debug(self, cfg, caplog):
        """``len(text) <= 1`` leaves the cue intact and emits a DEBUG log."""
        sub = Subtitle(index=5, start_ms=0, end_ms=12000, text="x")
        with caplog.at_level(logging.DEBUG, logger="talking_parrot.post_processing"):
            out = TimeBasedSplitProcessor().process([sub], cfg)
        assert out == [Subtitle(index=1, start_ms=0, end_ms=12000, text="x")]
        debug_msgs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("5" in r.getMessage() for r in debug_msgs)

    def test_empty_input(self, cfg):
        """Empty input returns empty list."""
        assert TimeBasedSplitProcessor().process([], cfg) == []
