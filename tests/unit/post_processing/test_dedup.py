"""Tests for ``DedupSubtitleProcessor``.

Spec: ``dedup-subtitle-processor`` (change
``segment-level-postprocessing-pipeline``).

These tests cover the four spec scenarios plus the similarity/gap decision
table, renumbering post-merge, non-transitive runs, empty/single inputs, and
the disabled-processor pass-through.
"""

from __future__ import annotations

import pytest

from talking_parrot.config.models import PostProcessingConfig
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.dedup import DedupSubtitleProcessor


@pytest.fixture
def cfg() -> PostProcessingConfig:
    """Default test config with explicit dedup defaults."""
    return PostProcessingConfig(
        dedup_enabled=True,
        dedup_similarity_threshold=0.9,
        dedup_max_gap_ms=600,
    )


class TestDedupSpecScenarios:
    """The four spec scenarios from ``dedup-subtitle-processor``."""

    def test_two_near_duplicate_cues_collapse_into_one(self, cfg):
        """Spec scenario: collapse to one cue with extended end_ms."""
        subs = [
            Subtitle(index=1, start_ms=1000, end_ms=1500, text="hello world"),
            Subtitle(index=2, start_ms=1700, end_ms=2200, text="hello worlds"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert out == [
            Subtitle(index=1, start_ms=1000, end_ms=2200, text="hello world"),
        ]

    def test_gap_above_threshold_prevents_merge(self, cfg):
        """Spec scenario: gap = 800ms > 600ms default → keep both, renumbered."""
        subs = [
            Subtitle(index=1, start_ms=1000, end_ms=1500, text="hello world"),
            Subtitle(index=2, start_ms=2300, end_ms=2800, text="hello worlds"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert len(out) == 2
        assert out[0] == Subtitle(
            index=1, start_ms=1000, end_ms=1500, text="hello world"
        )
        assert out[1] == Subtitle(
            index=2, start_ms=2300, end_ms=2800, text="hello worlds"
        )

    def test_three_cue_run_merges_into_single_cue(self, cfg):
        """Spec scenario: three cues all pairwise above thresholds → one cue."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="hello world"),
            Subtitle(index=2, start_ms=700, end_ms=1200, text="hello worlds"),
            Subtitle(index=3, start_ms=1400, end_ms=1900, text="hello world"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert out == [
            Subtitle(index=1, start_ms=0, end_ms=1900, text="hello world"),
        ]

    def test_disabled_processor_returns_input_unchanged(self):
        """Spec scenario: ``dedup_enabled=False`` → element-wise equal pass-through."""
        disabled = PostProcessingConfig(dedup_enabled=False)
        subs = [
            # Even though these would otherwise merge, disabled config skips it.
            Subtitle(index=7, start_ms=1000, end_ms=1500, text="hello world"),
            Subtitle(index=42, start_ms=1700, end_ms=2200, text="hello world"),
        ]
        out = DedupSubtitleProcessor().process(subs, disabled)
        assert out == subs
        # Indexes preserved (NOT renumbered) per spec wording.
        assert [s.index for s in out] == [7, 42]


class TestDedupDecisionTable:
    """Spec example: similarity/gap decision-table parametrisation."""

    @pytest.mark.parametrize(
        ("text_a", "text_b", "gap_ms", "should_merge"),
        [
            # similarity 0.95 ≥ 0.9 AND gap 200 ≤ 600 → merge
            ("hello world", "hello worlds", 200, True),
            # similarity 0.55 < 0.9 → no merge
            ("hello world", "goodbye world", 200, False),
            # gap 800 > 600 → no merge
            ("hello world", "hello world", 800, False),
            # identical short text, gap 100 ≤ 600 → merge
            ("あ", "あ", 100, True),
        ],
    )
    def test_decision_table(self, cfg, text_a, text_b, gap_ms, should_merge):
        """Each row of the spec's decision table maps to one parameterised case."""
        a_end = 1500
        b_start = a_end + gap_ms
        subs = [
            Subtitle(index=1, start_ms=1000, end_ms=a_end, text=text_a),
            Subtitle(index=2, start_ms=b_start, end_ms=b_start + 500, text=text_b),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        if should_merge:
            assert len(out) == 1
            assert out[0].text == text_a
            assert out[0].start_ms == 1000
            assert out[0].end_ms == b_start + 500
            assert out[0].index == 1
        else:
            assert len(out) == 2
            assert [s.index for s in out] == [1, 2]


class TestDedupBoundaryAndEdgeCases:
    """Boundary semantics, renumbering and edge inputs."""

    def test_similarity_equal_to_threshold_merges(self):
        """Spec uses ``>=`` for similarity — equality MUST merge."""
        # Construct two strings whose ratio is exactly 1.0 (>= any threshold).
        cfg = PostProcessingConfig(
            dedup_enabled=True,
            dedup_similarity_threshold=1.0,
            dedup_max_gap_ms=600,
        )
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="same"),
            Subtitle(index=2, start_ms=700, end_ms=1200, text="same"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert len(out) == 1
        assert out[0].text == "same"

    def test_gap_equal_to_threshold_merges(self):
        """Spec uses ``<=`` for gap — equality MUST merge."""
        cfg = PostProcessingConfig(
            dedup_enabled=True,
            dedup_similarity_threshold=0.9,
            dedup_max_gap_ms=600,
        )
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="hello world"),
            # gap = 1100 - 500 = 600 (equal to threshold)
            Subtitle(index=2, start_ms=1100, end_ms=1600, text="hello world"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert len(out) == 1

    def test_renumbering_after_merge_five_to_two(self, cfg):
        """A 5-cue input collapsing to 2 surviving cues yields indexes [1, 2]."""
        subs = [
            # Run 1: three near-duplicates (collapse to one)
            Subtitle(index=1, start_ms=0, end_ms=500, text="hello world"),
            Subtitle(index=2, start_ms=700, end_ms=1200, text="hello worlds"),
            Subtitle(index=3, start_ms=1400, end_ms=1900, text="hello world"),
            # Big gap → break
            Subtitle(index=4, start_ms=10000, end_ms=10500, text="foo"),
            # Different text → break (similarity to prev is low)
            Subtitle(index=5, start_ms=10700, end_ms=11200, text="bar"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert len(out) == 3
        assert [s.index for s in out] == [1, 2, 3]

    def test_renumbering_collapses_to_two(self, cfg):
        """Five inputs, one run of four collapsing → 2 surviving with indexes [1, 2]."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="hello world"),
            Subtitle(index=2, start_ms=700, end_ms=1200, text="hello worlds"),
            Subtitle(index=3, start_ms=1400, end_ms=1900, text="hello world"),
            Subtitle(index=4, start_ms=2100, end_ms=2600, text="hello worlds"),
            # Big gap breaks the run
            Subtitle(index=5, start_ms=20000, end_ms=20500, text="standalone"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert len(out) == 2
        assert [s.index for s in out] == [1, 2]
        assert out[0] == Subtitle(index=1, start_ms=0, end_ms=2600, text="hello world")

    def test_non_consecutive_no_transitive_merge(self, cfg):
        """S1↔S2 mergeable; S2↔S3 not. S3 stays separate; only S1+S2 merge."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="hello world"),
            Subtitle(index=2, start_ms=700, end_ms=1200, text="hello worlds"),
            # Different text — similarity to "hello worlds" is low.
            Subtitle(index=3, start_ms=1400, end_ms=1900, text="goodbye world"),
        ]
        out = DedupSubtitleProcessor().process(subs, cfg)
        assert len(out) == 2
        assert out[0] == Subtitle(index=1, start_ms=0, end_ms=1200, text="hello world")
        assert out[1] == Subtitle(
            index=2, start_ms=1400, end_ms=1900, text="goodbye world"
        )

    def test_empty_input(self, cfg):
        """Empty input returns empty list without raising."""
        assert DedupSubtitleProcessor().process([], cfg) == []

    def test_single_cue_input(self, cfg):
        """Single-cue input is returned with index=1."""
        sub = Subtitle(index=42, start_ms=0, end_ms=500, text="solo")
        out = DedupSubtitleProcessor().process([sub], cfg)
        assert out == [Subtitle(index=1, start_ms=0, end_ms=500, text="solo")]
