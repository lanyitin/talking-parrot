"""Streamable-HTTP dispatch tests for ``talking_parrot.mcp.cli`` (task 6.2).

Covers:

- **Streamable HTTP is the default transport** — invoking the production
  HTTP runner constructs a FastMCP app at the resolved host / port / path.
- **Default bind is loopback host and port 8765** — the FastMCP instance
  receives ``host=127.0.0.1`` and ``port=8765`` when the CLI is invoked
  with no overrides.
- **MCP endpoint path is ``/mcp``** — ``streamable_http_path`` is ``/mcp``.

The test patches :class:`mcp.server.fastmcp.FastMCP` with a recording stub
so we can assert how the production HTTP runner instantiates and runs it,
without binding a real socket.
"""

from __future__ import annotations

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
                sample_rate=16000,
                duration_ms=1000,
                rms_mean=0.0,
                rms_peak=0.0,
            ),
        )


class _RecordingFastMCP:
    """Stand-in for :class:`FastMCP` that records its construction args."""

    instances: list[_RecordingFastMCP] = []

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self.name = name
        self.kwargs = kwargs
        self.run_calls: list[dict[str, Any]] = []
        type(self).instances.append(self)

    def tool(self, *_args: Any, **_kwargs: Any) -> Any:
        def _decorator(fn: Any) -> Any:
            return fn

        return _decorator

    def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
        self.run_calls.append({"transport": transport, "mount_path": mount_path})


@pytest.fixture
def recording_fastmcp(monkeypatch: pytest.MonkeyPatch) -> type[_RecordingFastMCP]:
    """Patch ``mcp.server.fastmcp.FastMCP`` with the recording stub."""
    _RecordingFastMCP.instances = []
    import mcp.server.fastmcp as _fastmcp_mod

    monkeypatch.setattr(_fastmcp_mod, "FastMCP", _RecordingFastMCP)
    return _RecordingFastMCP


def test_default_http_runner_invokes_streamable_http_with_defaults(
    tmp_path: Path, recording_fastmcp: type[_RecordingFastMCP]
) -> None:
    """No CLI overrides ⇒ FastMCP gets ``127.0.0.1:8765`` and path ``/mcp``."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    rc = mcp_cli.main(
        ["--project", str(project)],
        env={},
        loader=_StubLoader(),
    )
    assert rc == 0, f"expected graceful exit, got {rc}"
    assert len(recording_fastmcp.instances) == 1, (
        f"expected exactly one FastMCP instance, got {len(recording_fastmcp.instances)}"
    )
    inst = recording_fastmcp.instances[0]
    assert inst.kwargs.get("host") == "127.0.0.1", inst.kwargs
    assert inst.kwargs.get("port") == 8765, inst.kwargs
    assert inst.kwargs.get("streamable_http_path") == "/mcp", inst.kwargs
    assert len(inst.run_calls) == 1, inst.run_calls
    assert inst.run_calls[0]["transport"] == "streamable-http"


def test_default_http_runner_honours_resolved_host_port(
    tmp_path: Path, recording_fastmcp: type[_RecordingFastMCP]
) -> None:
    """CLI overrides flow into the FastMCP instance."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    rc = mcp_cli.main(
        ["--project", str(project), "--host", "0.0.0.0", "--port", "9100"],
        env={},
        loader=_StubLoader(),
    )
    assert rc == 0
    inst = recording_fastmcp.instances[-1]
    assert inst.kwargs.get("host") == "0.0.0.0"
    assert inst.kwargs.get("port") == 9100
    assert inst.run_calls[0]["transport"] == "streamable-http"
