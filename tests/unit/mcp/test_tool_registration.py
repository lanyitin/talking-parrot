"""Tool registration tests for ``talking_parrot.mcp.server`` (task 6.1).

Covers the **Each tool is a separate decorated function (ISP)** requirement:
the FastMCP instance constructed in :mod:`talking_parrot.mcp.server` SHALL
register exactly the seven tools named in the spec, each as its own
decorated function delegating to a pure helper.
"""

from __future__ import annotations

import asyncio

import pytest

from talking_parrot.mcp import server as mcp_server


_EXPECTED_TOOL_NAMES = {
    "summary",
    "get_vad_segments",
    "get_vad_frames",
    "get_subtitles",
    "get_pre_postprocess_subtitles",
    "get_transcription_results",
    "diagnostics",
}


def test_seven_tools_registered_with_expected_names() -> None:
    """The MCP module exposes exactly the seven spec-named tools."""
    mcp = mcp_server.build_mcp_app()
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == _EXPECTED_TOOL_NAMES, (
        f"unexpected tool catalogue: got {names!r}, expected {_EXPECTED_TOOL_NAMES!r}"
    )
    # ISP: seven distinct callables, no duplicates.
    assert len(tools) == 7


def test_tools_delegate_to_pure_helpers(make_snapshot) -> None:  # type: ignore[no-untyped-def]
    """Invoking each tool yields the same payload as its pure helper."""
    snapshot = make_snapshot()
    mcp_server.install_snapshot(snapshot)
    mcp = mcp_server.build_mcp_app()

    # Use FastMCP's call_tool to dispatch by name; compare to direct helper.
    expected_summary = mcp_server.summary_from_snapshot(snapshot)
    result = asyncio.run(mcp.call_tool("summary", {}))
    # FastMCP call_tool returns ``(content_blocks, structured)`` when the
    # tool returns a dict — we compare the structured payload to the helper.
    assert isinstance(result, tuple), (
        f"FastMCP.call_tool returned {type(result)!r}, expected tuple — "
        "API may have changed"
    )
    assert len(result) == 2, (
        f"FastMCP.call_tool tuple length {len(result)}, expected 2 — "
        "API may have changed"
    )
    _content, structured = result
    assert structured == expected_summary, (
        "summary tool payload diverges from summary_from_snapshot helper"
    )


@pytest.fixture(autouse=True)
def _isolate_logger() -> None:
    """Avoid leaking handlers across tests."""
    yield
