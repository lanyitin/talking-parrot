"""Public API smoke tests for ``talking_parrot.shared``."""

from __future__ import annotations


def test_all_symbols_importable() -> None:
    """Every documented public symbol must import from ``talking_parrot.shared``."""
    from talking_parrot.shared import (
        AudioInfo,
        CueDiff,
        FileSnapshotLoader,
        MetricBundle,
        ProjectSnapshot,
        ScoreCard,
        SnapshotLoader,
    )

    for symbol in (
        AudioInfo,
        CueDiff,
        FileSnapshotLoader,
        MetricBundle,
        ProjectSnapshot,
        ScoreCard,
        SnapshotLoader,
    ):
        assert symbol is not None
