"""Argument-parsing tests for ``talking_parrot.mcp.cli`` (task 2.1).

Covers the **Decision: CLI / env-var injection layer** and the
**Entry point loads snapshot then dispatches transport** missing-flag
scenario.
"""

from __future__ import annotations

import pytest

from talking_parrot.mcp import cli as mcp_cli


def test_resolve_config_defaults_with_no_argv() -> None:
    """No argv yields the documented defaults (project unset)."""
    config = mcp_cli.resolve_config([], env={})
    assert config.host == "127.0.0.1"
    assert config.port == 8765
    assert config.transport == "http"
    assert config.project is None


def test_main_missing_project_exits_non_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invoking ``main`` without ``--project`` exits non-zero with stderr."""
    rc = mcp_cli.main([], env={})
    assert rc != 0
    captured = capsys.readouterr()
    assert "--project" in captured.err


def test_invalid_transport_value_exits(capsys: pytest.CaptureFixture[str]) -> None:
    """``--transport grpc`` triggers SystemExit naming ``grpc``."""
    with pytest.raises(SystemExit) as exc_info:
        mcp_cli.resolve_config(["--transport", "grpc"], env={})
    message = str(exc_info.value)
    assert "grpc" in message


def test_project_flag_parsed() -> None:
    """The ``--project`` value is captured into the config."""
    config = mcp_cli.resolve_config(["--project", "/tmp/x.tp"], env={})
    assert config.project == "/tmp/x.tp"
