"""Integration tests for ``talking_parrot.gui.http_server``."""

from __future__ import annotations

import dataclasses
import http.client
import importlib
import inspect
import json
import logging
import re
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from talking_parrot.gui import http_server
from talking_parrot.gui.cli import GuiConfig
from talking_parrot.shared import ProjectSnapshot


# ---------------------------------------------------------------------------
# Server lifecycle helper
# ---------------------------------------------------------------------------


@pytest.fixture
def running_server(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> Iterator[tuple[http_server._GuiServer, int]]:
    snap = make_snapshot()
    config = GuiConfig(host="127.0.0.1", port=0)
    server = http_server.serve(snap, config)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


# ---------------------------------------------------------------------------
# Snapshot binding
# ---------------------------------------------------------------------------


def test_serve_rejects_rebind(make_snapshot: Callable[..., ProjectSnapshot]) -> None:
    snap = make_snapshot()
    other = make_snapshot()
    config = GuiConfig(host="127.0.0.1", port=0)
    server = http_server.serve(snap, config)
    try:
        with pytest.raises(RuntimeError, match="snapshot already bound"):
            server.bind_snapshot(other)
    finally:
        server.server_close()


def test_snapshot_remains_frozen(
    running_server: tuple[http_server._GuiServer, int],
) -> None:
    server, port = running_server
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/api/summary")
    response = conn.getresponse()
    response.read()
    conn.close()
    with pytest.raises(dataclasses.FrozenInstanceError):
        server.snapshot.version = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Reuse of shared layer types
# ---------------------------------------------------------------------------


def test_no_shared_layer_redefinition() -> None:
    """The gui package must not redefine the shared layer types."""
    import talking_parrot.gui as gui_pkg
    from talking_parrot import shared

    forbidden = {"ProjectSnapshot", "AudioInfo", "SnapshotLoader"}
    for module_name in ("__init__", "api", "cli", "http_server"):
        full = (
            f"talking_parrot.gui.{module_name}"
            if module_name != "__init__"
            else "talking_parrot.gui"
        )
        mod = importlib.import_module(full)
        for name, obj in vars(mod).items():
            if name in forbidden and inspect.isclass(obj):
                # Allowed only if the class IS the shared-layer object.
                shared_obj = getattr(shared, name, None)
                assert obj is shared_obj, f"{full} redefines shared-layer type {name}"
    _ = gui_pkg


# ---------------------------------------------------------------------------
# No hardcoded host/port literals in api.py / http_server.py outside the
# GuiConfig default helper.
# ---------------------------------------------------------------------------


def test_no_hardcoded_host_port() -> None:
    api_src = Path(http_server.__file__).with_name("api.py").read_text("utf-8")
    forbidden_re = re.compile(r"127\.0\.0\.1|0\.0\.0\.0|localhost|\b8765\b")
    assert not forbidden_re.search(api_src), (
        "api.py contains forbidden host/port literal"
    )

    server_src = Path(http_server.__file__).read_text("utf-8")
    # The literal should appear at most via cli.py imports / docstring strings,
    # not in http_server.py itself outside the GuiConfig helper. http_server.py
    # does not declare GuiConfig, so it must contain no such literals at all.
    assert not forbidden_re.search(server_src), (
        "http_server.py contains forbidden host/port literal"
    )


# ---------------------------------------------------------------------------
# Static asset serving
# ---------------------------------------------------------------------------


def test_root_returns_index_html(
    running_server: tuple[http_server._GuiServer, int],
) -> None:
    _, port = running_server
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/")
    response = conn.getresponse()
    body = response.read()
    conn.close()
    assert response.status == 200
    assert response.getheader("Content-Type", "").startswith("text/html")
    assert b'<div id="app"></div>' in body


def test_path_traversal_rejected(
    running_server: tuple[http_server._GuiServer, int],
) -> None:
    _, port = running_server
    conn = http.client.HTTPConnection("127.0.0.1", port)
    # http.client normalises ``/../`` for us. Send the encoded path-info raw.
    conn.request("GET", "/%2e%2e/%2e%2e/etc/passwd")
    response = conn.getresponse()
    response.read()
    conn.close()
    # urlsplit decodes %2e -> ".", so our handler should see "../../etc/passwd"
    # and reject. If the runtime treats the encoded form as a literal filename,
    # the underlying file does not exist so 403 OR 404 are acceptable rejections;
    # we explicitly assert the request is NOT served as 200.
    assert response.status in (403, 404)


def test_static_only_contains_index_html() -> None:
    static_dir = Path(http_server.__file__).with_name("static")
    entries = sorted(
        p.name for p in static_dir.iterdir() if not p.name.startswith("__")
    )
    assert entries == ["index.html"]


# ---------------------------------------------------------------------------
# Range support on /api/video
# ---------------------------------------------------------------------------


@pytest.fixture
def video_server(
    make_snapshot: Callable[..., ProjectSnapshot], tmp_path: Path
) -> Iterator[tuple[http_server._GuiServer, int, int]]:
    """Start a server backed by a snapshot whose source file is a real video."""
    video = tmp_path / "movie.mp4"
    payload = bytes((i % 256) for i in range(8192))
    video.write_bytes(payload)
    snap = make_snapshot()
    snap = dataclasses.replace(snap, source_path=str(video))
    config = GuiConfig(host="127.0.0.1", port=0)
    server = http_server.serve(snap, config)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, port, len(payload)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_video_full_when_no_range(
    video_server: tuple[http_server._GuiServer, int, int],
) -> None:
    _, port, total = video_server
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/api/video")
    response = conn.getresponse()
    body = response.read()
    conn.close()
    assert response.status == 200
    assert int(response.getheader("Content-Length", "0")) == total
    assert len(body) == total


def test_video_range_partial_content(
    video_server: tuple[http_server._GuiServer, int, int],
) -> None:
    _, port, total = video_server
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/api/video", headers={"Range": "bytes=0-1023"})
    response = conn.getresponse()
    body = response.read()
    conn.close()
    assert response.status == 206
    assert int(response.getheader("Content-Length", "0")) == 1024
    assert response.getheader("Content-Range") == f"bytes 0-1023/{total}"
    assert len(body) == 1024


def test_video_range_unsatisfiable_416(
    video_server: tuple[http_server._GuiServer, int, int],
) -> None:
    _, port, _total = video_server
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/api/video", headers={"Range": "bytes=999999999999-"})
    response = conn.getresponse()
    response.read()
    conn.close()
    assert response.status == 416


# ---------------------------------------------------------------------------
# Threaded handling
# ---------------------------------------------------------------------------


def test_two_simultaneous_requests_complete(
    running_server: tuple[http_server._GuiServer, int],
) -> None:
    _, port = running_server
    results: list[int] = []

    def _hit() -> None:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/api/audio?start_ms=0&end_ms=1000")
        response = conn.getresponse()
        response.read()
        results.append(response.status)
        conn.close()

    threads = [threading.Thread(target=_hit) for _ in range(2)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    elapsed = time.monotonic() - start
    assert results == [200, 200]
    assert elapsed < 5


# ---------------------------------------------------------------------------
# FlaggedRegion bridge
# ---------------------------------------------------------------------------


def test_flagged_region_frozen() -> None:
    region = http_server.FlaggedRegion(start_ms=0, end_ms=100, label="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        region.label = "y"  # type: ignore[misc]


def test_get_flagged_regions_returns_tuple() -> None:
    http_server._set_flagged_regions(
        [
            http_server.FlaggedRegion(start_ms=0, end_ms=100, label="a"),
            http_server.FlaggedRegion(start_ms=100, end_ms=200, label="b"),
        ]
    )
    out = http_server.get_flagged_regions()
    assert isinstance(out, tuple)
    assert len(out) == 2


def test_get_flagged_regions_docstring_mentions_mcp_bridge() -> None:
    doc = inspect.getdoc(http_server.get_flagged_regions)
    assert doc is not None
    assert "MCP bridge" in doc


def test_post_flagged_regions_concurrent_replacement_is_coherent(
    running_server: tuple[http_server._GuiServer, int],
) -> None:
    _, port = running_server

    payload_a = json.dumps(
        {
            "regions": [
                {"start_ms": 0, "end_ms": 100, "label": "a1"},
                {"start_ms": 100, "end_ms": 200, "label": "a2"},
            ]
        }
    ).encode("utf-8")
    payload_b = json.dumps(
        {
            "regions": [
                {"start_ms": 0, "end_ms": 100, "label": "b1"},
                {"start_ms": 100, "end_ms": 200, "label": "b2"},
                {"start_ms": 200, "end_ms": 300, "label": "b3"},
            ]
        }
    ).encode("utf-8")

    def _post(body: bytes) -> None:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request(
            "POST",
            "/api/flagged_regions",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        conn.getresponse().read()
        conn.close()

    for _ in range(20):
        threads = [
            threading.Thread(target=_post, args=(payload_a,)),
            threading.Thread(target=_post, args=(payload_b,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        regions = http_server.get_flagged_regions()
        # Coherent end state: full A or full B, never a mix.
        labels = [r.label for r in regions]
        assert labels == ["a1", "a2"] or labels == ["b1", "b2", "b3"], labels


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_no_file_handler_attached(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    config = GuiConfig(host="127.0.0.1", port=0)
    server = http_server.serve(snap, config)
    try:
        logger = logging.getLogger("talking_parrot.gui")
        # Walk up to root
        seen: list[logging.Handler] = []
        cursor: logging.Logger | None = logger
        while cursor is not None:
            seen.extend(cursor.handlers)
            cursor = cursor.parent if cursor.propagate else None
        for handler in seen:
            assert not isinstance(handler, logging.FileHandler), (
                f"unexpected FileHandler attached: {handler!r}"
            )
    finally:
        server.server_close()


# ---------------------------------------------------------------------------
# Ephemeral port boot
# ---------------------------------------------------------------------------


def test_server_binds_ephemeral_port(
    make_snapshot: Callable[..., ProjectSnapshot],
) -> None:
    snap = make_snapshot()
    config = GuiConfig(host="127.0.0.1", port=0)
    server = http_server.serve(snap, config)
    try:
        host, port = server.server_address[:2]
        assert host == "127.0.0.1"
        assert port > 0
    finally:
        server.server_close()
