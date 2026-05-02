"""Tests for character-boundary post-processors (CJK, etc.).

Spec: ``character-boundary-processors``. Design: D4 (no token map) and D6.
"""

from __future__ import annotations

import inspect
import logging

import pytest

from talking_parrot.config.models import PostProcessingConfig
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.character_boundary import (
    CharacterBoundaryMergeProcessor,
    CharacterBoundarySplitProcessor,
)


@pytest.fixture
def cfg() -> PostProcessingConfig:
    """Default test config."""
    return PostProcessingConfig(
        max_line_length=20,
        max_lines_per_subtitle=2,
        merge_gap_threshold_ms=200,
        merge_max_duration_ms=6000,
        split_max_duration_ms=6000,
    )


class TestCharacterBoundaryMerge:
    """Spec: empty separator, time/length predicates apply."""

    def test_two_short_cjk_cues_merged_with_empty_separator(self, cfg):
        """``[("こんにちは",0,800),("世界",850,1500)]`` → one cue, no whitespace."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=800, text="こんにちは"),
            Subtitle(index=2, start_ms=850, end_ms=1500, text="世界"),
        ]
        out = CharacterBoundaryMergeProcessor().process(subs, cfg)
        assert out == [
            Subtitle(index=1, start_ms=0, end_ms=1500, text="こんにちは世界"),
        ]

    def test_gap_exceeding_threshold_prevents_merge(self, cfg):
        """500ms gap with threshold 200ms must not merge."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="あ"),
            Subtitle(index=2, start_ms=1000, end_ms=1500, text="い"),
        ]
        out = CharacterBoundaryMergeProcessor().process(subs, cfg)
        assert len(out) == 2
        assert [s.index for s in out] == [1, 2]

    def test_empty_input(self, cfg):
        """Empty input returns empty list."""
        assert CharacterBoundaryMergeProcessor().process([], cfg) == []


class TestCharacterBoundarySplit:
    """Spec: linear-interpolation split at character indices."""

    def test_nine_second_cjk_cue_split_into_two(self, cfg):
        """Spec scenario: 10-char 9s cue → ``あいうえお``/``かきくけこ`` halves."""
        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="あいうえおかきくけこ")
        out = CharacterBoundarySplitProcessor().process([sub], cfg)
        assert len(out) == 2
        assert out[0] == Subtitle(index=1, start_ms=0, end_ms=4500, text="あいうえお")
        assert out[1] == Subtitle(
            index=2, start_ms=4500, end_ms=9000, text="かきくけこ"
        )

    def test_single_character_cue_unchanged_logs_debug(self, cfg, caplog):
        """``len(text) <= 1`` leaves the cue intact and emits DEBUG log."""
        sub = Subtitle(index=3, start_ms=0, end_ms=9000, text="。")
        with caplog.at_level(logging.DEBUG, logger="talking_parrot.post_processing"):
            out = CharacterBoundarySplitProcessor().process([sub], cfg)
        assert out == [Subtitle(index=1, start_ms=0, end_ms=9000, text="。")]
        assert any(
            r.levelno == logging.DEBUG and "3" in r.getMessage() for r in caplog.records
        )

    def test_under_threshold_unchanged(self, cfg):
        """A cue under split_max_duration_ms passes through (renumbered)."""
        sub = Subtitle(index=42, start_ms=0, end_ms=3000, text="ab")
        out = CharacterBoundarySplitProcessor().process([sub], cfg)
        assert out == [Subtitle(index=1, start_ms=0, end_ms=3000, text="ab")]

    def test_empty_input(self, cfg):
        """Empty input returns empty list."""
        assert CharacterBoundarySplitProcessor().process([], cfg) == []


class TestCharacterBoundaryConstructorSurface:
    """D4: character-boundary processors don't accept a token map."""

    def test_merge_constructor_takes_no_token_map(self):
        """``CharacterBoundaryMergeProcessor.__init__`` accepts only ``self``."""
        sig = inspect.signature(CharacterBoundaryMergeProcessor.__init__)
        params = [p for p in sig.parameters if p != "self"]
        assert "token_map_by_index" not in params

    def test_split_constructor_takes_no_token_map(self):
        """``CharacterBoundarySplitProcessor.__init__`` accepts only ``self``."""
        sig = inspect.signature(CharacterBoundarySplitProcessor.__init__)
        params = [p for p in sig.parameters if p != "self"]
        assert "token_map_by_index" not in params
