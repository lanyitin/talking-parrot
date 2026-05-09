"""Shared in-memory data layer consumed by regression, GUI, and MCP tooling.

This package provides:

- ``ProjectSnapshot``: a frozen aggregate of every pipeline intermediate.
- ``AudioInfo``: aggregate audio statistics carried inside the snapshot.
- ``SnapshotLoader`` / ``FileSnapshotLoader``: protocol and default file-backed
  loader that materialise a snapshot from a ``.tp`` project file.
- ``ScoreCard`` / ``MetricBundle`` / ``CueDiff``: empty-shape value objects that
  the future regression scorer will populate.

Downstream packages (``regression/``, ``gui/``, ``mcp/``) MUST depend only on
this module, never on each other.
"""

from talking_parrot.shared.metrics import CueDiff, MetricBundle, ScoreCard
from talking_parrot.shared.project_snapshot import AudioInfo, ProjectSnapshot
from talking_parrot.shared.snapshot_loader import FileSnapshotLoader, SnapshotLoader

__all__ = [
    "AudioInfo",
    "CueDiff",
    "FileSnapshotLoader",
    "MetricBundle",
    "ProjectSnapshot",
    "ScoreCard",
    "SnapshotLoader",
]
