"""Module-level snapshot binding tests for ``talking_parrot.mcp.server``.

Covers tasks 3.1 / 3.2 of ``mcp-core``:

- The pure accessor returns the installed snapshot.
- Double-install is rejected (audio2subtitle ``_project`` anti-pattern guard).
- Tools never reassign the binding — verified by inspecting the server's
  ``__all__`` for the absence of any reassignment helper outside the
  one-shot installer.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from talking_parrot.mcp import server as mcp_server
from talking_parrot.shared import ProjectSnapshot


def test_accessor_returns_installed_snapshot(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    """``get_snapshot`` returns the snapshot passed to ``install_snapshot``."""
    snap = make_snapshot()
    mcp_server.install_snapshot(snap)
    assert mcp_server.get_snapshot() is snap


def test_get_snapshot_before_install_raises() -> None:
    """Reading the binding before installation raises ``RuntimeError``."""
    with pytest.raises(RuntimeError):
        mcp_server.get_snapshot()


def test_install_rejects_non_snapshot() -> None:
    """A non-``ProjectSnapshot`` argument raises ``TypeError``."""
    with pytest.raises(TypeError):
        mcp_server.install_snapshot("not a snapshot")  # type: ignore[arg-type]


def test_no_reassign(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    """Double-install raises ``RuntimeError`` (anti-pattern guard).

    Codifies the guard against audio2subtitle's mutable global ``_project``
    pattern called out in the **Module-level snapshot is read-only after
    init** requirement.
    """
    snap1 = make_snapshot()
    snap2 = make_snapshot()
    mcp_server.install_snapshot(snap1)
    with pytest.raises(RuntimeError):
        mcp_server.install_snapshot(snap2)
    # The original binding survives the failed re-install attempt.
    assert mcp_server.get_snapshot() is snap1


def test_public_api_does_not_expose_setter() -> None:
    """``__all__`` exposes ``install_snapshot`` but no plain setter.

    This is a static guard: the only way to set the binding is the
    one-shot installer.
    """
    public = set(mcp_server.__all__)
    assert "install_snapshot" in public
    assert "get_snapshot" in public
    # No alternative setter slipped into the public surface.
    for name in public:
        assert "set_snapshot" not in name
        assert "replace_snapshot" not in name
