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


class TestTimeBasedSplitWithPolicy:
    """Modified spec: `TimeBasedSplitProcessor` accepts a `SplitBoundaryPolicy`."""

    def test_default_constructor_uses_linear_policy(self, cfg):
        """No-arg constructor MUST be identical to `LinearSplitBoundaryPolicy`."""
        from talking_parrot.post_processing.split_policy import (
            LinearSplitBoundaryPolicy,
        )

        sub = Subtitle(index=1, start_ms=0, end_ms=12000, text="the quick brown fox")
        a = TimeBasedSplitProcessor().process([sub], cfg)
        b = TimeBasedSplitProcessor(policy=LinearSplitBoundaryPolicy()).process(
            [sub], cfg
        )
        assert a == b

    def test_policy_adjusts_text_split(self, cfg):
        """A stub policy adding +1 shifts text-split index but not timestamps."""

        class _PlusOne:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                return candidate_index + 1

        # 19 chars, 12s, cap 6s → n=2, candidate1 = round(1/2*19) = 10
        sub = Subtitle(index=1, start_ms=0, end_ms=12000, text="the quick brown fox")
        out = TimeBasedSplitProcessor(policy=_PlusOne()).process([sub], cfg)
        assert len(out) == 2
        assert (out[0].start_ms, out[0].end_ms) == (0, 6000)
        assert (out[1].start_ms, out[1].end_ms) == (6000, 12000)
        # First child text length = 11 (=10+1)
        assert out[0].text == "the quick b"
        assert out[1].text == "rown fox"
        assert out[0].text + out[1].text == "the quick brown fox"

    def test_policy_not_called_when_text_too_short(self, cfg):
        """Policy MUST NOT be invoked when ``len(text) <= 1``."""

        calls: list[tuple[str, int, int]] = []

        class _Spy:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                calls.append((text, candidate_index, search_radius))
                return candidate_index

        sub = Subtitle(index=5, start_ms=0, end_ms=12000, text="x")
        out = TimeBasedSplitProcessor(policy=_Spy()).process([sub], cfg)
        assert calls == []
        assert out == [Subtitle(index=1, start_ms=0, end_ms=12000, text="x")]

    def test_policy_receives_search_radius_from_config(self, cfg):
        """Processor MUST pass ``config.japanese_split_search_radius`` as radius."""

        captured: list[int] = []

        class _Capture:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                captured.append(search_radius)
                return candidate_index

        custom_cfg = PostProcessingConfig(
            max_line_length=40,
            max_lines_per_subtitle=2,
            merge_gap_threshold_ms=200,
            merge_max_duration_ms=6000,
            split_max_duration_ms=6000,
            japanese_split_search_radius=9,
        )
        sub = Subtitle(index=1, start_ms=0, end_ms=12000, text="the quick brown fox")
        TimeBasedSplitProcessor(policy=_Capture()).process([sub], custom_cfg)
        assert captured
        assert all(r == 9 for r in captured)


class TestTimeBasedSplitWithTimePolicy:
    """Modified spec: TimeBasedSplitProcessor accepts a SplitTimePolicy."""

    def test_default_constructor_uses_linear_time_policy(self, cfg):
        """No-arg constructor MUST be identical to passing both linear policies."""
        from talking_parrot.post_processing.split_policy import (
            LinearSplitBoundaryPolicy,
        )
        from talking_parrot.post_processing.split_time_policy import (
            LinearSplitTimePolicy,
        )

        sub = Subtitle(index=1, start_ms=0, end_ms=12000, text="the quick brown fox")
        a = TimeBasedSplitProcessor().process([sub], cfg)
        b = TimeBasedSplitProcessor(
            policy=LinearSplitBoundaryPolicy(),
            time_policy=LinearSplitTimePolicy(),
        ).process([sub], cfg)
        assert a == b

    def test_time_policy_snaps_boundary(self, cfg):
        """Stub time policy returning 6300 MUST shift slice boundary to 6300."""

        class _SnapTo6300:
            def adjust(
                self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int
            ) -> int:
                return 6300

        sub = Subtitle(index=1, start_ms=0, end_ms=12000, text="the quick brown fox")
        out = TimeBasedSplitProcessor(time_policy=_SnapTo6300()).process([sub], cfg)
        assert len(out) == 2
        assert (out[0].start_ms, out[0].end_ms) == (0, 6300)
        assert (out[1].start_ms, out[1].end_ms) == (6300, 12000)
        assert out[0].text + out[1].text == "the quick brown fox"

    def test_time_policy_not_called_when_text_too_short(self, cfg):
        """Time policy MUST NOT be called when text length <= 1."""

        calls: list[tuple[int, int, int]] = []

        class _SpyTime:
            def adjust(
                self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int
            ) -> int:
                calls.append((candidate_ms, cue_start_ms, cue_end_ms))
                return candidate_ms

        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="x")
        TimeBasedSplitProcessor(time_policy=_SpyTime()).process([sub], cfg)
        assert calls == []

    def test_sub_threshold_cue_skips_both_policies(self, cfg):
        """Cue under split_max_duration_ms MUST NOT call either policy."""
        boundary_calls: list[tuple[str, int, int]] = []
        time_calls: list[tuple[int, int, int]] = []

        class _SpyBoundary:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                boundary_calls.append((text, candidate_index, search_radius))
                return candidate_index

        class _SpyTime:
            def adjust(
                self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int
            ) -> int:
                time_calls.append((candidate_ms, cue_start_ms, cue_end_ms))
                return candidate_ms

        sub = Subtitle(index=1, start_ms=0, end_ms=3000, text="ok")
        TimeBasedSplitProcessor(policy=_SpyBoundary(), time_policy=_SpyTime()).process(
            [sub], cfg
        )
        assert boundary_calls == []
        assert time_calls == []

    def test_time_boundary_collision_emits_1ms_minimum_slice(self, caplog):
        """If time policy collides two adjacent boundaries, emit 1ms slice."""

        class _AlwaysCollide:
            def adjust(
                self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int
            ) -> int:
                return 8000

        custom_cfg = PostProcessingConfig(
            max_line_length=40,
            max_lines_per_subtitle=2,
            merge_gap_threshold_ms=200,
            merge_max_duration_ms=4000,
            split_max_duration_ms=4000,
        )
        sub = Subtitle(
            index=1, start_ms=0, end_ms=12000, text="a b c d e f g h i j k l"
        )
        with caplog.at_level(logging.DEBUG, logger="talking_parrot.post_processing"):
            out = TimeBasedSplitProcessor(time_policy=_AlwaysCollide()).process(
                [sub], custom_cfg
            )
        assert len(out) == 3
        assert (out[0].start_ms, out[0].end_ms) == (0, 8000)
        assert (out[1].start_ms, out[1].end_ms) == (8000, 8001)
        assert (out[2].start_ms, out[2].end_ms) == (8001, 12000)
        assert any(
            r.levelno == logging.DEBUG and "1" in r.getMessage() for r in caplog.records
        )
