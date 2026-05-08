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


class TestCharacterBoundarySplitWithPolicy:
    """Modified spec: split processor accepts a ``SplitBoundaryPolicy``."""

    def test_default_constructor_uses_linear_policy(self, cfg):
        """No-arg constructor MUST be identical to ``LinearSplitBoundaryPolicy``."""
        from talking_parrot.post_processing.split_policy import (
            LinearSplitBoundaryPolicy,
        )

        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="あいうえおかきくけこ")
        a = CharacterBoundarySplitProcessor().process([sub], cfg)
        b = CharacterBoundarySplitProcessor(policy=LinearSplitBoundaryPolicy()).process(
            [sub], cfg
        )
        assert a == b

    def test_policy_adjusts_text_but_not_time(self, cfg):
        """A stub policy adding +1 shifts text-split index but not timestamps."""

        class _PlusOne:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                return candidate_index + 1

        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="あいうえおかきくけこ")
        out = CharacterBoundarySplitProcessor(policy=_PlusOne()).process([sub], cfg)
        # split_max_duration_ms=6000, duration=9000 → n=2 slices
        assert len(out) == 2
        # Time positions unchanged: 0, 4500, 9000
        assert out[0].start_ms == 0
        assert out[0].end_ms == 4500
        assert out[1].start_ms == 4500
        assert out[1].end_ms == 9000
        # Text-split point shifted from 5 → 6 (round(4500/9000*10) + 1 = 6)
        assert out[0].text == "あいうえおか"
        assert out[1].text == "きくけこ"

    def test_policy_not_called_when_text_too_short(self, cfg):
        """Policy MUST NOT be invoked when ``len(text) <= 1``."""

        calls: list[tuple[str, int, int]] = []

        class _Spy:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                calls.append((text, candidate_index, search_radius))
                return candidate_index

        sub = Subtitle(index=3, start_ms=0, end_ms=9000, text="。")
        out = CharacterBoundarySplitProcessor(policy=_Spy()).process([sub], cfg)
        assert calls == []
        assert out == [Subtitle(index=1, start_ms=0, end_ms=9000, text="。")]

    def test_equal_consecutive_indices_emit_empty_child_and_log(self, cfg, caplog):
        """If policy snaps two slices to the same index, second slice gets empty text."""

        class _AlwaysOne:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                return 1

        # Duration 18000 with cap 6000 → n=3 slices; policy collapses both
        # intermediate split points to index 1 → middle slice is empty.
        sub = Subtitle(index=1, start_ms=0, end_ms=18000, text="あいうえおかきくけこ")
        with caplog.at_level(logging.DEBUG, logger="talking_parrot.post_processing"):
            out = CharacterBoundarySplitProcessor(policy=_AlwaysOne()).process(
                [sub], cfg
            )
        assert len(out) == 3
        assert out[0].text == "あ"
        assert out[1].text == ""
        assert out[2].text == "いうえおかきくけこ"
        assert out[0].start_ms == 0
        assert out[2].end_ms == 18000
        # DEBUG log emitted naming the cue index.
        assert any(
            r.levelno == logging.DEBUG and "1" in r.getMessage() for r in caplog.records
        )

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
            max_line_length=20,
            max_lines_per_subtitle=2,
            merge_gap_threshold_ms=200,
            merge_max_duration_ms=6000,
            split_max_duration_ms=6000,
            japanese_split_search_radius=7,
        )
        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="あいうえおかきくけこ")
        CharacterBoundarySplitProcessor(policy=_Capture()).process([sub], custom_cfg)
        assert captured  # at least one call
        assert all(r == 7 for r in captured)


class TestCharacterBoundarySplitWithTimePolicy:
    """Modified spec: split processor accepts a ``SplitTimePolicy``."""

    def test_default_constructor_uses_linear_time_policy(self, cfg):
        """No-arg constructor MUST be identical to passing both linear policies."""
        from talking_parrot.post_processing.split_policy import (
            LinearSplitBoundaryPolicy,
        )
        from talking_parrot.post_processing.split_time_policy import (
            LinearSplitTimePolicy,
        )

        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="あいうえおかきくけこ")
        a = CharacterBoundarySplitProcessor().process([sub], cfg)
        b = CharacterBoundarySplitProcessor(
            policy=LinearSplitBoundaryPolicy(),
            time_policy=LinearSplitTimePolicy(),
        ).process([sub], cfg)
        assert a == b

    def test_time_policy_snaps_boundary(self, cfg):
        """Stub time policy returning 4700 MUST shift slice boundary to 4700."""

        class _SnapTo4700:
            def adjust(
                self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int
            ) -> int:
                return 4700

        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="あいうえおかきくけこ")
        out = CharacterBoundarySplitProcessor(time_policy=_SnapTo4700()).process(
            [sub], cfg
        )
        assert len(out) == 2
        assert (out[0].start_ms, out[0].end_ms) == (0, 4700)
        assert (out[1].start_ms, out[1].end_ms) == (4700, 9000)
        assert out[0].text + out[1].text == "あいうえおかきくけこ"

    def test_time_policy_not_called_when_text_too_short(self, cfg):
        """Time policy MUST NOT be invoked when ``len(text) <= 1``."""

        calls: list[tuple[int, int, int]] = []

        class _SpyTime:
            def adjust(
                self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int
            ) -> int:
                calls.append((candidate_ms, cue_start_ms, cue_end_ms))
                return candidate_ms

        sub = Subtitle(index=3, start_ms=0, end_ms=9000, text="。")
        CharacterBoundarySplitProcessor(time_policy=_SpyTime()).process([sub], cfg)
        assert calls == []

    def test_time_boundary_collision_emits_1ms_minimum_slice(self, cfg, caplog):
        """If time policy snaps two adjacent boundaries to same value, emit 1ms slice."""

        class _AlwaysCollide:
            def adjust(
                self, candidate_ms: int, cue_start_ms: int, cue_end_ms: int
            ) -> int:
                return 8000

        custom_cfg = PostProcessingConfig(
            max_line_length=20,
            max_lines_per_subtitle=2,
            merge_gap_threshold_ms=200,
            merge_max_duration_ms=4000,
            split_max_duration_ms=4000,
        )
        # n = ceil(12000 / 4000) = 3 slices, two inner boundaries.
        sub = Subtitle(
            index=1, start_ms=0, end_ms=12000, text="あいうえおかきくけこさし"
        )
        with caplog.at_level(logging.DEBUG, logger="talking_parrot.post_processing"):
            out = CharacterBoundarySplitProcessor(time_policy=_AlwaysCollide()).process(
                [sub], custom_cfg
            )
        assert len(out) == 3
        assert (out[0].start_ms, out[0].end_ms) == (0, 8000)
        assert (out[1].start_ms, out[1].end_ms) == (8000, 8001)
        assert (out[2].start_ms, out[2].end_ms) == (8001, 12000)
        assert any(
            r.levelno == logging.DEBUG and "1" in r.getMessage() for r in caplog.records
        )
