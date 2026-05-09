"""Confirm gui module docstrings cite their Architectural Decision sections."""

from __future__ import annotations

import inspect

from talking_parrot.gui import api, cli, http_server


def test_http_server_docstring_cites_server_library_selection() -> None:
    doc = inspect.getdoc(http_server)
    assert doc is not None
    assert "Server Library Selection" in doc


def test_api_docstring_cites_endpoint_routing() -> None:
    doc = inspect.getdoc(api)
    assert doc is not None
    assert "Endpoint Routing" in doc


def test_cli_docstring_cites_configuration_resolution_order() -> None:
    doc = inspect.getdoc(cli)
    assert doc is not None
    assert "Configuration Resolution Order" in doc
