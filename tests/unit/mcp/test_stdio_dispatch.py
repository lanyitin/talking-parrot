"""stdio-dispatch tests for the stdio runner (task 6.4).

Realises the **Transport selection supports HTTP default and stdio opt-in**
requirement (stdio half): FastMCP's stdio runner is invoked only when
``--transport stdio`` is explicitly selected, never when the default HTTP
transport is in effect.
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
                sample_rate=16000, duration_ms=1000, rms_mean=0.0, rms_peak=0.0
            ),
        )


class _RecordingFastMCP:
    instances: list[_RecordingFastMCP] = []

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.run_calls: list[dict[str, Any]] = []
        type(self).instances.append(self)

    def tool(self, *_a: Any, **_k: Any) -> Any:
        def _decorator(fn: Any) -> Any:
            return fn

        return _decorator

    def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
        self.run_calls.append({"transport": transport, "mount_path": mount_path})


@pytest.fixture
def recording_fastmcp(monkeypatch: pytest.MonkeyPatch) -> type[_RecordingFastMCP]:
    _RecordingFastMCP.instances = []
    import mcp.server.fastmcp as _fastmcp_mod

    monkeypatch.setattr(_fastmcp_mod, "FastMCP", _RecordingFastMCP)
    return _RecordingFastMCP


def test_stdio_runner_invoked_only_when_stdio_explicitly_selected(
    tmp_path: Path, recording_fastmcp: type[_RecordingFastMCP]
) -> None:
    """``--transport stdio`` ⇒ FastMCP.run(transport='stdio')."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    rc = mcp_cli.main(
        ["--project", str(project), "--transport", "stdio"],
        env={},
        loader=_StubLoader(),
    )
    assert rc == 0
    assert len(recording_fastmcp.instances) == 1
    inst = recording_fastmcp.instances[0]
    assert len(inst.run_calls) == 1
    assert inst.run_calls[0]["transport"] == "stdio", (
        f"expected stdio dispatch, got {inst.run_calls[0]!r}"
    )


def test_default_transport_does_not_invoke_stdio(
    tmp_path: Path, recording_fastmcp: type[_RecordingFastMCP]
) -> None:
    """Without ``--transport stdio`` the stdio path SHALL not run."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")

    rc = mcp_cli.main(
        ["--project", str(project)],
        env={},
        loader=_StubLoader(),
    )
    assert rc == 0
    inst = recording_fastmcp.instances[-1]
    transports = [c["transport"] for c in inst.run_calls]
    assert "stdio" not in transports, (
        f"stdio runner invoked when default HTTP was selected: {transports!r}"
    )
    assert transports == ["streamable-http"]
