"""Dispatch wiring tests for ``talking_parrot.mcp.cli`` (task 2.4).

Covers:

- **Logging targets stdout only** — no file handler is registered, no log
  file is written to disk during normal CLI startup.
- **Entry point loads snapshot then dispatches transport** — the snapshot
  is loaded once, installed on ``server``, and the chosen transport runner
  is invoked.
"""

from __future__ import annotations

import logging
from pathlib import Path

from talking_parrot.mcp import cli as mcp_cli
from talking_parrot.mcp import server as mcp_server
from talking_parrot.shared import AudioInfo, ProjectSnapshot


class _StubLoader:
    """In-memory loader that returns a tiny snapshot."""

    def __init__(self) -> None:
        self.calls = 0

    def load(self, source: str | Path) -> ProjectSnapshot:
        self.calls += 1
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


def test_dispatch_invokes_http_runner_with_resolved_config(tmp_path: Path) -> None:
    """The default transport (HTTP) invokes ``http_runner`` exactly once."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")
    loader = _StubLoader()
    captured: dict[str, object] = {}

    def _http(config: mcp_cli.McpConfig, snapshot: ProjectSnapshot) -> int:
        captured["config"] = config
        captured["snapshot_id"] = id(snapshot)
        return 0

    rc = mcp_cli.main(
        ["--project", str(project), "--port", "9100"],
        env={},
        loader=loader,
        http_runner=_http,
    )
    assert rc == 0
    assert loader.calls == 1
    config = captured["config"]
    assert isinstance(config, mcp_cli.McpConfig)
    assert config.port == 9100
    assert config.transport == "http"
    # Snapshot was installed on the server module.
    installed = mcp_server.get_snapshot()
    assert id(installed) == captured["snapshot_id"]


def test_dispatch_invokes_stdio_runner_when_selected(tmp_path: Path) -> None:
    """``--transport stdio`` routes to ``stdio_runner`` and skips ``http_runner``."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")
    loader = _StubLoader()
    http_called = {"n": 0}
    stdio_called = {"n": 0}

    def _http(config: mcp_cli.McpConfig, snapshot: ProjectSnapshot) -> int:
        http_called["n"] += 1
        return 1

    def _stdio(config: mcp_cli.McpConfig, snapshot: ProjectSnapshot) -> int:
        stdio_called["n"] += 1
        return 0

    rc = mcp_cli.main(
        ["--project", str(project), "--transport", "stdio"],
        env={},
        loader=loader,
        http_runner=_http,
        stdio_runner=_stdio,
    )
    assert rc == 0
    assert http_called["n"] == 0
    assert stdio_called["n"] == 1


def test_no_log_file_created_on_disk(tmp_path: Path) -> None:
    """Calling the CLI never registers a file handler on the MCP logger."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")
    loader = _StubLoader()

    def _http(config: mcp_cli.McpConfig, snapshot: ProjectSnapshot) -> int:
        return 0

    mcp_cli.main(
        ["--project", str(project)],
        env={},
        loader=loader,
        http_runner=_http,
    )
    mcp_logger = logging.getLogger("talking_parrot.mcp")
    for h in mcp_logger.handlers:
        assert not isinstance(h, logging.FileHandler), (
            "MCP logger must not register a FileHandler — Logging targets "
            "stdout only requirement"
        )
    # No new files should have been created in the working directory's tmp
    # path beyond the project file itself.
    leftover = [p for p in tmp_path.iterdir() if p != project]
    assert leftover == []
