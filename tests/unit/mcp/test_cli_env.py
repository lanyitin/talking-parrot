"""Env-var resolution tests for ``talking_parrot.mcp.cli`` (task 2.2).

Covers the **Configuration is injected via env vars and CLI flags**
requirement: CLI flags override env vars override built-in defaults.
"""

from __future__ import annotations

import pytest

from talking_parrot.mcp import cli as mcp_cli


def test_env_var_overrides_default() -> None:
    """``TALKING_PARROT_MCP_HOST`` set, no flag → env wins."""
    env = {"TALKING_PARROT_MCP_HOST": "0.0.0.0"}
    config = mcp_cli.resolve_config([], env=env)
    assert config.host == "0.0.0.0"


def test_env_port_overrides_default() -> None:
    """``TALKING_PARROT_MCP_PORT`` set, no flag → env wins."""
    env = {"TALKING_PARROT_MCP_PORT": "9000"}
    config = mcp_cli.resolve_config([], env=env)
    assert config.port == 9000


def test_cli_flag_overrides_env_port() -> None:
    """CLI ``--port`` value beats ``TALKING_PARROT_MCP_PORT``."""
    env = {"TALKING_PARROT_MCP_PORT": "9000"}
    config = mcp_cli.resolve_config(["--port", "9100"], env=env)
    assert config.port == 9100


def test_cli_flag_overrides_env_host() -> None:
    """CLI ``--host`` value beats ``TALKING_PARROT_MCP_HOST``."""
    env = {"TALKING_PARROT_MCP_HOST": "0.0.0.0"}
    config = mcp_cli.resolve_config(["--host", "127.0.0.1"], env=env)
    assert config.host == "127.0.0.1"


def test_invalid_env_port_raises() -> None:
    """A non-integer ``TALKING_PARROT_MCP_PORT`` triggers ``SystemExit``."""
    with pytest.raises(SystemExit):
        mcp_cli.resolve_config([], env={"TALKING_PARROT_MCP_PORT": "not-a-number"})
