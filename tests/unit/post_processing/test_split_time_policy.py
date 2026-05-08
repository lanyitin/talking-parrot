"""Tests for the SplitTimePolicy protocol and implementations.

Spec: ``split-time-policy`` (change ``snap-split-timestamps-to-vad-silence``).
"""

from __future__ import annotations

import pytest

from talking_parrot.post_processing.split_time_policy import (
    LinearSplitTimePolicy,
    SplitTimePolicy,
    VadAlignedSplitTimePolicy,
)


class TestSplitTimePolicyProtocol:
    """Structural-type checks for the SplitTimePolicy protocol."""

    def test_runtime_checkable(self):
        """`SplitTimePolicy` MUST be a runtime-checkable Protocol."""
        assert isinstance(LinearSplitTimePolicy(), SplitTimePolicy)
        assert isinstance(
            VadAlignedSplitTimePolicy(silences=[], search_radius_ms=0),
            SplitTimePolicy,
        )

    def test_returned_value_strictly_inside_cue(self):
        """Returned int from a valid candidate MUST satisfy `cue_start < value < cue_end`."""
        policy: SplitTimePolicy = LinearSplitTimePolicy()
        result = policy.adjust(candidate_ms=4500, cue_start_ms=1000, cue_end_ms=7000)
        assert 1000 < result < 7000


class TestLinearSplitTimePolicy:
    """No-op behaviour of the default policy."""

    def test_returns_candidate_unchanged(self):
        """`LinearSplitTimePolicy.adjust` MUST return the candidate verbatim."""
        policy = LinearSplitTimePolicy()
        assert policy.adjust(4500, 0, 9000) == 4500

    def test_ignores_cue_bounds(self):
        """The same candidate MUST yield the same return regardless of cue bounds."""
        policy = LinearSplitTimePolicy()
        assert policy.adjust(4500, 0, 9000) == 4500
        assert policy.adjust(4500, 4000, 5000) == 4500


class TestVadAlignedSplitTimePolicy:
    """Snapping behaviour of the VAD-aware policy."""

    def test_snaps_to_silence_midpoint_within_radius(self):
        """When a silence midpoint lies in `[candidate-r, candidate+r]`, snap to it."""
        policy = VadAlignedSplitTimePolicy(
            silences=[(4400, 4700)], search_radius_ms=300
        )
        assert policy.adjust(candidate_ms=4500, cue_start_ms=0, cue_end_ms=9000) == 4550

    def test_falls_back_when_no_silence_in_window(self):
        """No silence midpoint inside the window MUST yield candidate unchanged."""
        policy = VadAlignedSplitTimePolicy(
            silences=[(0, 100), (8800, 9000)], search_radius_ms=200
        )
        assert policy.adjust(candidate_ms=4500, cue_start_ms=0, cue_end_ms=9000) == 4500

    def test_snaps_to_nearer_of_two_in_window(self):
        """Two silences in window: nearer midpoint wins."""
        policy = VadAlignedSplitTimePolicy(
            silences=[(4200, 4400), (4700, 4900)], search_radius_ms=500
        )
        # Midpoints are 4300 (400 away from 4700) and 4800 (100 away from 4700).
        assert policy.adjust(candidate_ms=4700, cue_start_ms=0, cue_end_ms=9000) == 4800

    def test_tie_break_prefers_smaller_midpoint(self):
        """Equal distance MUST resolve to the smaller midpoint."""
        policy = VadAlignedSplitTimePolicy(
            silences=[(4500, 4700), (5300, 5500)], search_radius_ms=500
        )
        # mid1 = 4600 (400 away from 5000), mid2 = 5400 (400 away). Tie → 4600.
        assert policy.adjust(candidate_ms=5000, cue_start_ms=0, cue_end_ms=9000) == 4600

    def test_silence_midpoint_at_or_outside_cue_end_rejected(self):
        """A silence whose midpoint equals cue_end_ms MUST be ignored (open interval)."""
        policy = VadAlignedSplitTimePolicy(
            silences=[(8900, 9100)], search_radius_ms=500
        )
        # mid = 9000, cue_end = 9000 → rejected (mid < cue_end_ms required).
        assert policy.adjust(candidate_ms=8800, cue_start_ms=0, cue_end_ms=9000) == 8800

    def test_silence_midpoint_at_or_outside_cue_start_rejected(self):
        """A silence whose midpoint equals cue_start_ms MUST be ignored (open interval)."""
        policy = VadAlignedSplitTimePolicy(silences=[(-100, 100)], search_radius_ms=500)
        # mid = 0, cue_start = 0 → rejected (cue_start_ms < mid required).
        assert policy.adjust(candidate_ms=200, cue_start_ms=0, cue_end_ms=9000) == 200

    def test_negative_radius_rejected_at_construction(self):
        """`VadAlignedSplitTimePolicy(search_radius_ms=-1)` MUST raise `ValueError`."""
        with pytest.raises(ValueError):
            VadAlignedSplitTimePolicy(silences=[], search_radius_ms=-1)

    def test_constructor_copy_isolates_from_caller_mutation(self):
        """Mutating the caller's silence list MUST NOT affect the policy."""
        silences: list[tuple[int, int]] = [(4400, 4700)]
        policy = VadAlignedSplitTimePolicy(silences=silences, search_radius_ms=300)
        silences.append((0, 100))
        # The appended (0, 100) silence's midpoint 50 SHALL NOT be considered.
        assert policy.adjust(candidate_ms=50, cue_start_ms=0, cue_end_ms=9000) == 50
