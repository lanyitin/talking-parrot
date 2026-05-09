"""Port-collision tests for the HTTP runner (task 6.3).

Realises the **Port collision surfaces a clear failure** requirement: when
the bind raises :class:`OSError`, the runner SHALL exit non-zero and write
a stderr message naming both the host and the port.
"""

from __future__ import annotations

import errno
from pathlib import Path
from typing import Any

import pytest

from talking_parrot.mcp import cli as mcp_cli
from talking_parrot.shared import AudioInfo, ProjectSnapshot


class _StubLoader:
    def load(self, source: str | Path) -> ProjectSnapshot:
        return ProjectSnapshot(
            version="1.0",
            created_at="2026-05-09",
            source_path=str(source),
            config_snapshot={},
            audio_info=AudioInfo(
                sample_rate=16000, duration_ms=1000, rms_mean=0.0, rms_peak=0.0
            ),
        )


class _BindFailingFastMCP:
    """Stand-in FastMCP whose ``run`` raises ``OSError(EADDRINUSE)``."""

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def tool(self, *_a: Any, **_k: Any) -> Any:
        def _decorator(fn: Any) -> Any:
            return fn

        return _decorator

    def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
        raise OSError(errno.EADDRINUSE, "Address already in use")


def test_port_collision_writes_host_and_port_to_stderr_and_exits_non_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """OSError from the bind ⇒ non-zero exit + stderr names host and port."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    import mcp.server.fastmcp as _fastmcp_mod

    monkeypatch.setattr(_fastmcp_mod, "FastMCP", _BindFailingFastMCP)

    rc = mcp_cli.main(
        ["--project", str(project), "--port", "8765"],
        env={},
        loader=_StubLoader(),
    )
    assert rc != 0, f"expected non-zero exit on bind failure, got {rc}"
    captured = capsys.readouterr()
    assert "127.0.0.1" in captured.err, (
        f"stderr missing resolved host '127.0.0.1': {captured.err!r}"
    )
    assert "8765" in captured.err, (
        f"stderr missing resolved port '8765': {captured.err!r}"
    )
