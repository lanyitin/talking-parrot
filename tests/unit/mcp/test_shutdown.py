"""Graceful-shutdown tests for the HTTP / stdio runners (task 6.5).

Realises the **Shutdown is graceful on SIGINT** requirement: SIGINT (and
SIGTERM where available) raised during the FastMCP serve loop unwinds to
exit code ``0`` without an unhandled exception escaping the CLI.
"""

from __future__ import annotations

import os
import signal
from pathlib import Path
from typing import Any

import pytest

from talking_parrot.mcp import cli as mcp_cli
from talking_parrot.shared import AudioInfo, ProjectSnapshot


@pytest.fixture(autouse=True)
def _restore_signal_handlers() -> None:
    """Restore default SIGINT / SIGTERM handlers after each test."""
    prev_int = signal.getsignal(signal.SIGINT)
    prev_term = signal.getsignal(getattr(signal, "SIGTERM", signal.SIGINT))
    yield
    signal.signal(signal.SIGINT, prev_int)
    sigterm = getattr(signal, "SIGTERM", None)
    if sigterm is not None:
        signal.signal(sigterm, prev_term)


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


class _SigintRaisingFastMCP:
    """Stand-in FastMCP whose ``run`` simulates SIGINT mid-serve."""

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def tool(self, *_a: Any, **_k: Any) -> Any:
        def _decorator(fn: Any) -> Any:
            return fn

        return _decorator

    def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
        # Simulate the OS delivering SIGINT to the dispatcher: invoke our
        # own handler the way the kernel would. Our handler raises
        # SystemExit(0) which the runner catches.
        os.kill(os.getpid(), signal.SIGINT)


def test_sigint_during_http_serve_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIGINT during HTTP serve ⇒ runner returns ``0`` cleanly."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    import mcp.server.fastmcp as _fastmcp_mod

    monkeypatch.setattr(_fastmcp_mod, "FastMCP", _SigintRaisingFastMCP)

    rc = mcp_cli.main(
        ["--project", str(project)],
        env={},
        loader=_StubLoader(),
    )
    assert rc == 0, f"SIGINT should yield graceful exit 0, got {rc}"


def test_sigint_during_stdio_serve_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIGINT during stdio serve ⇒ runner returns ``0`` cleanly."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    import mcp.server.fastmcp as _fastmcp_mod

    monkeypatch.setattr(_fastmcp_mod, "FastMCP", _SigintRaisingFastMCP)

    rc = mcp_cli.main(
        ["--project", str(project), "--transport", "stdio"],
        env={},
        loader=_StubLoader(),
    )
    assert rc == 0


def test_keyboardinterrupt_during_serve_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare KeyboardInterrupt from FastMCP.run is also a graceful exit."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    class _KIFastMCP:
        def __init__(self, name: str | None = None, **kwargs: Any) -> None:
            pass

        def tool(self, *_a: Any, **_k: Any) -> Any:
            def _decorator(fn: Any) -> Any:
                return fn

            return _decorator

        def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
            raise KeyboardInterrupt

    import mcp.server.fastmcp as _fastmcp_mod

    monkeypatch.setattr(_fastmcp_mod, "FastMCP", _KIFastMCP)

    rc = mcp_cli.main(
        ["--project", str(project)],
        env={},
        loader=_StubLoader(),
    )
    assert rc == 0
