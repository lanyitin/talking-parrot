"""Tests for the ``SubtitleProcessor`` ABC and shared helpers.

Covers spec ``subtitle-processor``:

- Direct instantiation of the ABC raises ``TypeError``.
- A subclass that does not implement ``process`` is not instantiable.
- ``process`` does not mutate the input list or input ``Subtitle`` instances.
- Output is ordered by non-decreasing ``start_ms`` and every cue has
  ``end_ms >= start_ms``.
- Empty input yields empty output without raising.
"""

from __future__ import annotations

import copy

import pytest

from talking_parrot.config.models import PostProcessingConfig
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.base import (
    SubtitleProcessor,
    _renumber,
    _with_token_map,
)
from talking_parrot.models.transcription import AlignedToken


class _IdentityProcessor(SubtitleProcessor):
    """Concrete trivial processor that returns a fresh list of the same cues."""

    def process(
        self, subtitles: list[Subtitle], config: PostProcessingConfig
    ) -> list[Subtitle]:
        """Return a renumbered copy of ``subtitles``."""
        return _renumber(list(subtitles))


class TestSubtitleProcessorABC:
    """Direct instantiation and subclass requirements."""

    def test_direct_instantiation_raises(self):
        """``SubtitleProcessor()`` raises ``TypeError``."""
        with pytest.raises(TypeError):
            SubtitleProcessor()  # type: ignore[abstract]

    def test_subclass_without_process_is_not_instantiable(self):
        """A subclass that doesn't implement ``process`` cannot be instantiated."""

        class Foo(SubtitleProcessor):
            pass

        with pytest.raises(TypeError):
            Foo()  # type: ignore[abstract]

    def test_concrete_subclass_is_instantiable(self):
        """Implementing ``process`` makes the subclass instantiable."""
        proc = _IdentityProcessor()
        assert isinstance(proc, SubtitleProcessor)


class TestSubtitleProcessorImmutability:
    """Spec: SubtitleProcessor input immutability."""

    def test_input_list_not_mutated(self):
        """The processor MUST NOT mutate the input list."""
        subs_in = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="a"),
            Subtitle(index=2, start_ms=600, end_ms=1100, text="b"),
        ]
        snapshot = copy.deepcopy(subs_in)
        out = _IdentityProcessor().process(subs_in, PostProcessingConfig())
        assert subs_in == snapshot
        assert out is not subs_in


class TestSubtitleProcessorOutputInvariants:
    """Spec: output ordering and timestamp invariants."""

    def test_output_sorted_by_start_ms(self):
        """For every adjacent pair, ``b.start_ms >= a.start_ms``."""
        subs_in = [
            Subtitle(index=1, start_ms=0, end_ms=500, text="a"),
            Subtitle(index=2, start_ms=600, end_ms=1100, text="b"),
            Subtitle(index=3, start_ms=1200, end_ms=1700, text="c"),
        ]
        out = _IdentityProcessor().process(subs_in, PostProcessingConfig())
        for i in range(len(out) - 1):
            assert out[i].start_ms <= out[i + 1].start_ms

    def test_each_cue_has_non_negative_duration(self):
        """``end_ms >= start_ms`` for every cue."""
        subs_in = [Subtitle(index=1, start_ms=10, end_ms=10, text="zero-len")]
        out = _IdentityProcessor().process(subs_in, PostProcessingConfig())
        for s in out:
            assert s.end_ms >= s.start_ms


class TestSubtitleProcessorEmptyInput:
    """Spec: SubtitleProcessor handles empty input."""

    def test_empty_input_returns_empty(self):
        """An empty input returns an empty list without raising."""
        out = _IdentityProcessor().process([], PostProcessingConfig())
        assert out == []


class TestRenumberHelper:
    """``_renumber`` MUST produce contiguous 1-based indices."""

    def test_renumber_resets_indices(self):
        """A list with arbitrary indices comes out indexed 1..N."""
        subs = [
            Subtitle(index=99, start_ms=0, end_ms=10, text="a"),
            Subtitle(index=42, start_ms=20, end_ms=30, text="b"),
        ]
        out = _renumber(subs)
        assert [s.index for s in out] == [1, 2]
        # other fields are preserved
        assert out[0].text == "a"
        assert out[1].start_ms == 20

    def test_renumber_empty(self):
        """Empty input yields empty output."""
        assert _renumber([]) == []


class TestWithTokenMapHelper:
    """``_with_token_map`` aggregates parent token lists onto new cue indices."""

    def test_aggregates_multiple_parents_into_one_child(self):
        """Merge case: child #1 derives from parents #1 and #2 → tokens concat."""
        t1 = AlignedToken(word="a", start_ms=0, end_ms=100, score=1.0)
        t2 = AlignedToken(word="b", start_ms=200, end_ms=300, score=1.0)
        parent_map = {1: [t1], 2: [t2]}
        # new_subs: one merged cue (parent indices 1 and 2 → child index 1)
        new_subs = [Subtitle(index=1, start_ms=0, end_ms=300, text="a b")]
        child_to_parents = {1: [1, 2]}
        out = _with_token_map(new_subs, parent_map, child_to_parents)
        assert out == {1: [t1, t2]}

    def test_split_one_parent_into_many_children(self):
        """Split case: parent #1's tokens are partitioned across two children."""
        t1 = AlignedToken(word="a", start_ms=0, end_ms=100, score=1.0)
        t2 = AlignedToken(word="b", start_ms=200, end_ms=300, score=1.0)
        parent_map = {1: [t1, t2]}
        new_subs = [
            Subtitle(index=1, start_ms=0, end_ms=100, text="a"),
            Subtitle(index=2, start_ms=200, end_ms=300, text="b"),
        ]
        # Use explicit per-child token slices rather than parent indices.
        per_child_tokens = {1: [t1], 2: [t2]}
        out = _with_token_map(
            new_subs,
            parent_map,
            child_to_parents=None,
            per_child_tokens=per_child_tokens,
        )
        assert out == {1: [t1], 2: [t2]}
