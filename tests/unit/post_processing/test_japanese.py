"""Tests for ``JapaneseFillerProcessor`` and ``JapaneseRepetitionProcessor``.

Spec: ``japanese-postprocessors`` (change
``segment-level-postprocessing-pipeline``).
"""

from __future__ import annotations

import pytest

from talking_parrot.config.models import PostProcessingConfig
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.japanese import (
    JapaneseFillerProcessor,
    JapaneseRepetitionProcessor,
)


# ---------------------------------------------------------------------------
# JapaneseFillerProcessor
# ---------------------------------------------------------------------------


@pytest.fixture
def filler_cfg() -> PostProcessingConfig:
    """Default config with filler enabled."""
    return PostProcessingConfig(japanese_filler_enabled=True)


class TestJapaneseFillerSpecScenarios:
    """Spec scenarios for ``JapaneseFillerProcessor``."""

    def test_leading_filler_removed_timing_preserved(self, filler_cfg):
        """Spec scenario: ``あのー、こんにちは`` → ``こんにちは`` (timing/index preserved)."""
        subs = [
            Subtitle(index=1, start_ms=1000, end_ms=2000, text="あのー、こんにちは"),
        ]
        out = JapaneseFillerProcessor().process(subs, filler_cfg)
        assert out == [
            Subtitle(index=1, start_ms=1000, end_ms=2000, text="こんにちは"),
        ]

    def test_cue_dropped_when_only_filler_remains(self, filler_cfg):
        """Spec scenario: filler-only cue dropped; survivor renumbered to 1."""
        subs = [
            Subtitle(index=1, start_ms=1000, end_ms=1500, text="えっと"),
            Subtitle(index=2, start_ms=2000, end_ms=2500, text="こんにちは"),
        ]
        out = JapaneseFillerProcessor().process(subs, filler_cfg)
        assert out == [
            Subtitle(index=1, start_ms=2000, end_ms=2500, text="こんにちは"),
        ]

    def test_disabled_processor_returns_input_unchanged(self):
        """Spec scenario: ``japanese_filler_enabled=False`` → element-wise equal."""
        cfg = PostProcessingConfig(japanese_filler_enabled=False)
        subs = [
            Subtitle(index=7, start_ms=1000, end_ms=2000, text="あのーこんにちは"),
            Subtitle(index=42, start_ms=3000, end_ms=4000, text="えっと"),
        ]
        out = JapaneseFillerProcessor().process(subs, cfg)
        assert out == subs
        assert [s.index for s in out] == [7, 42]


class TestJapaneseFillerDefaults:
    """Each default filler word must be stripped from the start."""

    @pytest.mark.parametrize(
        "filler",
        [
            "あの",
            "あのー",
            "えっと",
            "えーと",
            "えー",
            "まあ",
            "そのー",
            "その",
            "なんか",
            "ね",
        ],
    )
    def test_default_filler_stripped_from_start(self, filler_cfg, filler):
        """Each default filler word at the start is stripped."""
        text = f"{filler}こんにちは"
        subs = [Subtitle(index=1, start_ms=0, end_ms=1000, text=text)]
        out = JapaneseFillerProcessor().process(subs, filler_cfg)
        assert len(out) == 1
        assert out[0].text == "こんにちは"


class TestJapaneseFillerEdgeCases:
    """Boundary semantics and edge cases."""

    def test_filler_not_at_start_preserved(self, filler_cfg):
        """``あの`` mid-string is NOT stripped — leading-only rule."""
        subs = [Subtitle(index=1, start_ms=0, end_ms=1000, text="今日あのね")]
        out = JapaneseFillerProcessor().process(subs, filler_cfg)
        assert len(out) == 1
        assert out[0].text == "今日あのね"

    def test_custom_filler_list(self):
        """Custom filler list overrides defaults."""
        cfg = PostProcessingConfig(
            japanese_filler_enabled=True,
            japanese_filler_words=["ですね"],
        )
        # ですね prefix stripped
        subs1 = [Subtitle(index=1, start_ms=0, end_ms=1000, text="ですねこんにちは")]
        out1 = JapaneseFillerProcessor().process(subs1, cfg)
        assert out1[0].text == "こんにちは"

        # あの NOT in custom list, preserved
        subs2 = [Subtitle(index=1, start_ms=0, end_ms=1000, text="あのこんにちは")]
        out2 = JapaneseFillerProcessor().process(subs2, cfg)
        assert out2[0].text == "あのこんにちは"

    def test_renumbering_after_drops(self, filler_cfg):
        """4 cues, 2 of which become empty → survivors indexed [1, 2]."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="えっと"),
            Subtitle(index=2, start_ms=600, end_ms=1100, text="こんにちは"),
            Subtitle(index=3, start_ms=1200, end_ms=1700, text="あのー"),
            Subtitle(index=4, start_ms=1800, end_ms=2300, text="さようなら"),
        ]
        out = JapaneseFillerProcessor().process(subs, filler_cfg)
        assert len(out) == 2
        assert [s.index for s in out] == [1, 2]
        assert out[0].text == "こんにちは"
        assert out[1].text == "さようなら"

    def test_empty_input(self, filler_cfg):
        """Empty input returns empty list."""
        assert JapaneseFillerProcessor().process([], filler_cfg) == []

    def test_longest_filler_takes_priority(self, filler_cfg):
        """``あのー`` must match before ``あの`` to avoid leaving ``ー`` behind."""
        subs = [Subtitle(index=1, start_ms=0, end_ms=1000, text="あのーこんにちは")]
        out = JapaneseFillerProcessor().process(subs, filler_cfg)
        assert out[0].text == "こんにちは"


# ---------------------------------------------------------------------------
# JapaneseRepetitionProcessor
# ---------------------------------------------------------------------------


@pytest.fixture
def repeat_cfg() -> PostProcessingConfig:
    """Default config with repetition enabled."""
    return PostProcessingConfig(japanese_repetition_enabled=True)


class TestJapaneseRepetitionSpecScenarios:
    """Spec scenarios for ``JapaneseRepetitionProcessor``."""

    def test_three_or_more_repeats_collapsed_to_two(self, repeat_cfg):
        """Spec scenario: ``あああああ`` → ``ああ`` (timing/index preserved)."""
        subs = [Subtitle(index=1, start_ms=1000, end_ms=1500, text="あああああ")]
        out = JapaneseRepetitionProcessor().process(subs, repeat_cfg)
        assert out == [Subtitle(index=1, start_ms=1000, end_ms=1500, text="ああ")]

    def test_onomatopoeia_preserved(self, repeat_cfg):
        """Spec scenario: ``どきどきどき`` with ``どきどき`` in whitelist → unchanged."""
        subs = [Subtitle(index=1, start_ms=1000, end_ms=1500, text="どきどきどき")]
        out = JapaneseRepetitionProcessor().process(subs, repeat_cfg)
        assert out == [
            Subtitle(index=1, start_ms=1000, end_ms=1500, text="どきどきどき")
        ]

    def test_disabled_processor_returns_input_unchanged(self):
        """Spec scenario: ``japanese_repetition_enabled=False`` → element-wise equal."""
        cfg = PostProcessingConfig(japanese_repetition_enabled=False)
        subs = [
            Subtitle(index=7, start_ms=1000, end_ms=1500, text="あああああ"),
            Subtitle(index=42, start_ms=2000, end_ms=2500, text="わわわ"),
        ]
        out = JapaneseRepetitionProcessor().process(subs, cfg)
        assert out == subs
        assert [s.index for s in out] == [7, 42]


class TestJapaneseRepetitionDecisionTable:
    """Spec example: repetition collapse decision table."""

    @pytest.mark.parametrize(
        ("input_text", "whitelist", "expected_text"),
        [
            ("あああああ", None, "ああ"),
            ("わわわ", None, "わわ"),
            ("どきどきどき", ["どきどき"], "どきどきどき"),
            ("〜〜〜", None, "〜〜"),
        ],
    )
    def test_decision_table(self, input_text, whitelist, expected_text):
        """Each row of the decision table maps to one parameterised case."""
        if whitelist is None:
            cfg = PostProcessingConfig(japanese_repetition_enabled=True)
        else:
            cfg = PostProcessingConfig(
                japanese_repetition_enabled=True,
                japanese_onomatopoeia_whitelist=whitelist,
            )
        subs = [Subtitle(index=1, start_ms=0, end_ms=500, text=input_text)]
        out = JapaneseRepetitionProcessor().process(subs, cfg)
        assert len(out) == 1
        assert out[0].text == expected_text


class TestJapaneseRepetitionEdgeCases:
    """Boundary semantics and edge cases."""

    def test_cue_dropped_when_text_becomes_empty(self, repeat_cfg):
        """A whitespace-only input cue is dropped; survivors renumbered."""
        subs = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="   "),
            Subtitle(index=2, start_ms=600, end_ms=1100, text="あああああ"),
        ]
        out = JapaneseRepetitionProcessor().process(subs, repeat_cfg)
        assert len(out) == 1
        assert out[0] == Subtitle(index=1, start_ms=600, end_ms=1100, text="ああ")

    def test_mixed_text_only_run_collapses(self, repeat_cfg):
        """``ああああいうえお`` → ``ああいうえお`` (only the run collapses)."""
        subs = [Subtitle(index=1, start_ms=0, end_ms=500, text="ああああいうえお")]
        out = JapaneseRepetitionProcessor().process(subs, repeat_cfg)
        assert out[0].text == "ああいうえお"

    def test_multiple_runs_in_one_cue(self, repeat_cfg):
        """Each run collapses independently."""
        subs = [Subtitle(index=1, start_ms=0, end_ms=500, text="ああああ ええええ")]
        out = JapaneseRepetitionProcessor().process(subs, repeat_cfg)
        assert out[0].text == "ああ ええ"

    def test_empty_input(self, repeat_cfg):
        """Empty input returns empty list."""
        assert JapaneseRepetitionProcessor().process([], repeat_cfg) == []
