"""Transport selection tests for ``talking_parrot.mcp.cli`` (task 2.3).

Covers the **Transport selection supports HTTP default and stdio opt-in**
requirement.
"""

from __future__ import annotations

import pytest

from talking_parrot.mcp import cli as mcp_cli


def test_default_transport_is_http() -> None:
    """No ``--transport`` flag selects HTTP."""
    config = mcp_cli.resolve_config([], env={})
    assert config.transport == "http"


def test_stdio_opt_in() -> None:
    """``--transport stdio`` selects stdio."""
    config = mcp_cli.resolve_config(["--transport", "stdio"], env={})
    assert config.transport == "stdio"


def test_http_explicit() -> None:
    """``--transport http`` is also accepted explicitly."""
    config = mcp_cli.resolve_config(["--transport", "http"], env={})
    assert config.transport == "http"


def test_invalid_transport_rejected() -> None:
    """Any other value raises ``SystemExit`` naming the bad value."""
    with pytest.raises(SystemExit) as exc_info:
        mcp_cli.resolve_config(["--transport", "websocket"], env={})
    assert "websocket" in str(exc_info.value)
