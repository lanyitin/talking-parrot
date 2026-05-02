"""Tests for word-boundary post-processors.

Spec: ``word-boundary-processors``. Design: D3 (token-map closure) and D6.
"""

from __future__ import annotations

import inspect

import pytest

from talking_parrot.config.models import PostProcessingConfig
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import AlignedToken
from talking_parrot.post_processing.word_boundary import (
    WordBoundaryMergeProcessor,
    WordBoundarySplitProcessor,
)


@pytest.fixture
def cfg() -> PostProcessingConfig:
    """Default test config."""
    return PostProcessingConfig(
        max_line_length=42,
        max_lines_per_subtitle=2,
        merge_gap_threshold_ms=200,
        merge_max_duration_ms=6000,
        split_max_duration_ms=6000,
    )


def _tok(word: str, start_ms: int, end_ms: int) -> AlignedToken:
    """Build an AlignedToken with score=1.0 for tests."""
    return AlignedToken(word=word, start_ms=start_ms, end_ms=end_ms, score=1.0)


class TestWordBoundaryMerge:
    """Spec: merge adjacent cues that satisfy all constraints."""

    def test_two_eligible_cues_merged_with_space(self, cfg):
        """Spec scenario: ``[(0,1000,"hello"),(1100,2000,"world")]`` merge."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=1000, text="hello"),
            Subtitle(index=2, start_ms=1100, end_ms=2000, text="world"),
        ]
        token_map = {
            1: [_tok("hello", 0, 1000)],
            2: [_tok("world", 1100, 2000)],
        }
        out = WordBoundaryMergeProcessor(token_map_by_index=token_map).process(
            subs, cfg
        )
        assert out == [
            Subtitle(index=1, start_ms=0, end_ms=2000, text="hello world"),
        ]

    def test_gap_too_large_no_merge(self, cfg):
        """Gap exceeds threshold → cues unchanged."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=1000, text="a"),
            Subtitle(index=2, start_ms=5000, end_ms=6000, text="b"),
        ]
        out = WordBoundaryMergeProcessor(token_map_by_index={}).process(subs, cfg)
        assert len(out) == 2

    def test_text_budget_blocks_merge(self):
        """Total text exceeds max_line_length * max_lines → no merge."""
        narrow = PostProcessingConfig(
            max_line_length=42,
            max_lines_per_subtitle=1,
            merge_gap_threshold_ms=200,
            merge_max_duration_ms=6000,
            split_max_duration_ms=6000,
        )
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=1000, text="x" * 30),
            Subtitle(index=2, start_ms=1100, end_ms=2000, text="y" * 30),
        ]
        out = WordBoundaryMergeProcessor(token_map_by_index={}).process(subs, narrow)
        assert len(out) == 2

    def test_empty_input(self, cfg):
        """Empty input returns empty list."""
        assert WordBoundaryMergeProcessor(token_map_by_index={}).process([], cfg) == []


class TestWordBoundarySplit:
    """Spec: split at token boundaries; snap to nearest token start."""

    def test_long_cue_split_at_token_boundary(self, cfg):
        """Spec example: 12s cue, 4 tokens, split_max=6000 → 2 cues 'a b' and 'c d'."""
        sub = Subtitle(index=1, start_ms=0, end_ms=12000, text="a b c d")
        tokens = [
            _tok("a", 0, 3000),
            _tok("b", 3100, 6000),
            _tok("c", 6100, 9000),
            _tok("d", 9100, 12000),
        ]
        token_map = {1: tokens}
        out = WordBoundarySplitProcessor(token_map_by_index=token_map).process(
            [sub], cfg
        )
        assert len(out) == 2
        assert out[0].text == "a b"
        assert out[1].text == "c d"
        # Times come from the underlying tokens.
        assert (out[0].start_ms, out[0].end_ms) == (0, 6000)
        assert (out[1].start_ms, out[1].end_ms) == (6100, 12000)
        assert [s.index for s in out] == [1, 2]

    def test_under_threshold_unchanged(self, cfg):
        """A cue under split_max_duration_ms passes through unchanged."""
        sub = Subtitle(index=7, start_ms=0, end_ms=5000, text="hello")
        out = WordBoundarySplitProcessor(token_map_by_index={7: []}).process([sub], cfg)
        assert out == [Subtitle(index=1, start_ms=0, end_ms=5000, text="hello")]

    def test_insufficient_tokens_logs_debug(self, cfg, caplog):
        """``len(tokens) < n`` leaves the cue intact and emits DEBUG."""
        import logging

        sub = Subtitle(index=42, start_ms=0, end_ms=12000, text="solo")
        token_map = {42: [_tok("solo", 0, 12000)]}
        with caplog.at_level(logging.DEBUG, logger="talking_parrot.post_processing"):
            out = WordBoundarySplitProcessor(token_map_by_index=token_map).process(
                [sub], cfg
            )
        assert out == [Subtitle(index=1, start_ms=0, end_ms=12000, text="solo")]
        assert any(
            r.levelno == logging.DEBUG and "42" in r.getMessage()
            for r in caplog.records
        )

    def test_empty_input(self, cfg):
        """Empty input returns empty list."""
        assert WordBoundarySplitProcessor(token_map_by_index={}).process([], cfg) == []


class TestWordBoundaryConstructor:
    """D3: WORD-group processors take a token-map keyword arg."""

    def test_merge_constructor_signature(self):
        """``WordBoundaryMergeProcessor.__init__`` accepts ``token_map_by_index``."""
        sig = inspect.signature(WordBoundaryMergeProcessor.__init__)
        assert "token_map_by_index" in sig.parameters

    def test_split_constructor_signature(self):
        """``WordBoundarySplitProcessor.__init__`` accepts ``token_map_by_index``."""
        sig = inspect.signature(WordBoundarySplitProcessor.__init__)
        assert "token_map_by_index" in sig.parameters
