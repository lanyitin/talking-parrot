"""Tests for the SplitBoundaryPolicy protocol and LinearSplitBoundaryPolicy."""

from __future__ import annotations

import pytest

from talking_parrot.post_processing.split_policy import (
    LinearSplitBoundaryPolicy,
    SplitBoundaryPolicy,
)


class TestLinearSplitBoundaryPolicy:
    """Default policy is a no-op that returns the candidate unchanged."""

    def test_default_policy_is_noop(self):
        """`adjust("abcdefgh", 4, 3)` MUST return 4."""
        policy = LinearSplitBoundaryPolicy()
        assert policy.adjust("abcdefgh", 4, 3) == 4

    @pytest.mark.parametrize("radius", [0, 1, 3, 5, 100])
    def test_search_radius_is_ignored(self, radius: int):
        """Returned value MUST equal candidate_index regardless of radius."""
        policy = LinearSplitBoundaryPolicy()
        assert policy.adjust("abcdefgh", 4, radius) == 4

    def test_returned_index_in_valid_interval(self):
        """Returned index MUST lie in `[1, len(text) - 1]` for typical inputs."""
        policy = LinearSplitBoundaryPolicy()
        result = policy.adjust("abcdefgh", 4, 2)
        assert 1 <= result <= 7


class TestSplitBoundaryPolicyProtocol:
    """Structural typing contract for `SplitBoundaryPolicy`."""

    def test_linear_policy_is_a_split_boundary_policy(self):
        """`LinearSplitBoundaryPolicy` MUST satisfy the protocol structurally."""
        policy: SplitBoundaryPolicy = LinearSplitBoundaryPolicy()
        # protocol exposes `adjust`
        assert callable(policy.adjust)

    def test_arbitrary_object_with_adjust_satisfies_protocol(self):
        """Any object with the right `adjust` signature satisfies the protocol."""

        class _Stub:
            def adjust(
                self, text: str, candidate_index: int, search_radius: int
            ) -> int:
                return candidate_index

        policy: SplitBoundaryPolicy = _Stub()
        assert policy.adjust("abcd", 2, 1) == 2
