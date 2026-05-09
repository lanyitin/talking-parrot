"""Stdlib-only HTTP server for the GUI backend.

Per the ``Server Library Selection`` Architectural Decision in the
gui-backend design, this module:

- Boots a ``http.server.ThreadingHTTPServer`` so concurrent fetches from the
  SPA do not block one another (no third-party dep).
- Wires the request handler to the pure-function dispatcher in
  ``talking_parrot.gui.api``.
- Owns the single source of truth for the in-process flagged-region list
  (the ``Flagged Regions Bridge`` decision), guarded by a module-level
  ``threading.Lock``. The future MCP bridge consumes
  :func:`get_flagged_regions` and MUST NOT touch the underlying list.
- Serves static assets from ``gui/static/`` via ``importlib.resources``,
  rewriting ``/`` to ``/index.html`` and rejecting traversal attempts.
- Logs only to stdout via ``logging.getLogger("talking_parrot.gui")`` —
  no file handlers (Factor XI).
"""

from __future__ import annotations

import importlib.resources
import logging
import mimetypes
import os
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlsplit

from talking_parrot.gui import api as _api
from talking_parrot.shared import (
    AudioInfo,  # re-exposed here for downstream import convenience
    FileSnapshotLoader,  # re-exposed here for downstream import convenience
    ProjectSnapshot,
    SnapshotLoader,  # re-exposed here for downstream import convenience
)

if TYPE_CHECKING:
    from talking_parrot.gui.cli import GuiConfig

# Re-export shared types so downstream code can write
# ``from talking_parrot.gui.http_server import ProjectSnapshot`` without
# violating the "Reuse of shared layer types" requirement (we never define
# them here, only re-bind the imported names).
__all__ = [
    "AudioInfo",
    "FileSnapshotLoader",
    "FlaggedRegion",
    "ProjectSnapshot",
    "SnapshotLoader",
    "configure_logging",
    "get_flagged_regions",
    "serve",
]


_logger = logging.getLogger("talking_parrot.gui")


# ---------------------------------------------------------------------------
# Logging — stdout-only per design Factor XI
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """Attach a single stdout ``StreamHandler`` to the gui logger.

    No file handler is ever attached; verified by
    ``test_http_server.py::test_no_file_handler_attached``.
    """
    if any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "stream", None) is sys.stdout
        for h in _logger.handlers
    ):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


# ---------------------------------------------------------------------------
# FlaggedRegion bridge
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FlaggedRegion:
    """Immutable flagged-region value object.

    Used by the GUI's POST endpoint and by the future MCP bridge.
    """

    start_ms: int
    end_ms: int
    label: str | None


_flagged_regions: list[FlaggedRegion] = []
_flagged_regions_lock = threading.Lock()


def get_flagged_regions() -> tuple[FlaggedRegion, ...]:
    """Return an immutable snapshot of the currently flagged regions.

    This function is the sole sanctioned interface for the future MCP bridge
    to read flagged regions. No other code outside ``talking_parrot.gui``
    may import the underlying mutable list — only this MCP bridge accessor
    is part of the stable API.
    """
    with _flagged_regions_lock:
        return tuple(_flagged_regions)


def _set_flagged_regions(regions: list[FlaggedRegion]) -> None:
    """Atomically replace the in-process flagged-region list under the lock."""
    with _flagged_regions_lock:
        _flagged_regions.clear()
        _flagged_regions.extend(regions)


# ---------------------------------------------------------------------------
# Static asset resolution
# ---------------------------------------------------------------------------


def _read_static(path: str) -> tuple[bytes, str] | None:
    """Resolve a request path to a static asset under ``gui/static/``.

    Returns ``(body, content_type)`` on success, or ``None`` if the asset is
    missing. Path traversal attempts (after normalisation) are rejected by
    the caller via the ``_is_safe_static_path`` guard.
    """
    rel = path.lstrip("/")
    if not rel:
        rel = "index.html"
    try:
        anchor = importlib.resources.files("talking_parrot.gui.static")
        target = anchor.joinpath(rel)
        if not target.is_file():
            return None
        body = target.read_bytes()
    except (FileNotFoundError, ModuleNotFoundError):
        return None
    mime, _enc = mimetypes.guess_type(rel)
    if mime is None:
        mime = "application/octet-stream"
    return body, mime


def _is_safe_static_path(raw: str) -> bool:
    """Return False if the path normalises outside the static root."""
    cleaned = PurePosixPath(raw.lstrip("/"))
    if cleaned.is_absolute():
        return False
    parts = cleaned.parts
    if any(part == ".." for part in parts):
        return False
    return True


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    """Minimal request handler that delegates to ``api.dispatch``."""

    server_version = "TalkingParrotGUI/0.1"

    # Silence the stdlib's stderr-by-default access logger; route through
    # our stdout-only logger instead.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        _logger.info("%s - %s", self.address_string(), format % args)

    def _split(self) -> tuple[str, dict[str, str]]:
        parsed = urlsplit(self.path)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        return parsed.path, query

    def _read_body(self) -> bytes | None:
        length_header = self.headers.get("Content-Length")
        if not length_header:
            return None
        try:
            length = int(length_header)
        except ValueError:
            return None
        if length <= 0:
            return b""
        # Hard cap at 4 MiB to reject oversized POST bodies.
        if length > 4 * 1024 * 1024:
            return None
        return self.rfile.read(length)

    def _serve_static_or_404(self, path: str) -> None:
        if not _is_safe_static_path(path):
            self._send_simple(403, b"forbidden", "text/plain; charset=utf-8")
            return
        result = _read_static(path)
        if result is None:
            self._send_simple(404, b"not found", "text/plain; charset=utf-8")
            return
        body, mime = result
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_simple(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_api(self, response: _api.ApiResponse) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response.body)

    # ---- Method dispatch ------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 — stdlib API name
        path, query = self._split()
        if path.startswith("/api/"):
            if path == "/api/video":
                self._handle_video(query)
                return
            snapshot = self._snapshot()
            response = _api.dispatch("GET", path, query, snapshot, None)
            self._send_api(response)
            return
        # Static
        if path == "/":
            path = "/index.html"
        self._serve_static_or_404(path)

    def do_POST(self) -> None:  # noqa: N802
        path, query = self._split()
        if not path.startswith("/api/"):
            self._send_simple(404, b"not found", "text/plain; charset=utf-8")
            return
        body = self._read_body()
        snapshot = self._snapshot()
        response = _api.dispatch("POST", path, query, snapshot, body)
        self._send_api(response)

    def do_DELETE(self) -> None:  # noqa: N802
        path, query = self._split()
        if not path.startswith("/api/"):
            self._send_simple(404, b"not found", "text/plain; charset=utf-8")
            return
        snapshot = self._snapshot()
        response = _api.dispatch("DELETE", path, query, snapshot, None)
        self._send_api(response)

    # ---- helpers --------------------------------------------------------

    def _snapshot(self) -> ProjectSnapshot:
        snap = getattr(self.server, "snapshot", None)
        assert isinstance(snap, ProjectSnapshot), (
            "server.snapshot is not bound; serve() must be called before requests"
        )
        return snap

    def _handle_video(self, query: dict[str, str]) -> None:
        """Range-aware byte serving from ``snapshot.source_path``."""
        snapshot = self._snapshot()
        source = snapshot.source_path
        if not source:
            self._send_simple(404, b"not found", "text/plain; charset=utf-8")
            return
        from pathlib import Path

        path = Path(source)
        if not path.exists() or not path.is_file():
            self._send_simple(404, b"not found", "text/plain; charset=utf-8")
            return
        mime_guess, _enc = mimetypes.guess_type(source)
        if mime_guess is None or not mime_guess.startswith("video/"):
            self._send_simple(404, b"not video", "text/plain; charset=utf-8")
            return
        total = path.stat().st_size
        range_header = self.headers.get("Range")
        if not range_header:
            with path.open("rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_guess)
            self.send_header("Content-Length", str(total))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(body)
            return

        start, end = _parse_range(range_header, total)
        if start is None or end is None:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{total}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        length = end - start + 1
        with path.open("rb") as fh:
            fh.seek(start)
            body = fh.read(length)
        self.send_response(206)
        self.send_header("Content-Type", mime_guess)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.end_headers()
        self.wfile.write(body)


def _parse_range(header: str, total: int) -> tuple[int | None, int | None]:
    """Parse a single ``bytes=<start>-<end>`` range header.

    Returns ``(start, end)`` inclusive, or ``(None, None)`` if unsatisfiable.
    """
    if not header.startswith("bytes="):
        return (None, None)
    spec = header[len("bytes=") :].strip()
    if "," in spec:
        # Multi-range not supported in this minimal impl.
        return (None, None)
    if "-" not in spec:
        return (None, None)
    start_s, end_s = spec.split("-", 1)
    try:
        if start_s == "" and end_s != "":
            # Suffix range: last N bytes.
            suffix = int(end_s)
            if suffix <= 0 or total == 0:
                return (None, None)
            start = max(0, total - suffix)
            end = total - 1
        elif start_s != "" and end_s == "":
            start = int(start_s)
            end = total - 1
        else:
            start = int(start_s)
            end = int(end_s)
    except ValueError:
        return (None, None)
    if start < 0 or start >= total or end < start:
        return (None, None)
    if end >= total:
        end = total - 1
    return (start, end)


# ---------------------------------------------------------------------------
# Server bootstrap
# ---------------------------------------------------------------------------


class _GuiServer(ThreadingHTTPServer):
    """``ThreadingHTTPServer`` subclass that holds the bound snapshot.

    The ``snapshot`` attribute is set exactly once (the
    ``Snapshot held read-only after bootstrap`` requirement); a second
    binding raises ``RuntimeError("snapshot already bound")``.
    """

    snapshot: ProjectSnapshot

    def bind_snapshot(self, snapshot: ProjectSnapshot) -> None:
        """Set the read-only snapshot or raise if already bound."""
        if getattr(self, "_snapshot_bound", False):
            raise RuntimeError("snapshot already bound")
        self.snapshot = snapshot
        self._snapshot_bound = True


def serve(snapshot: ProjectSnapshot, config: GuiConfig) -> _GuiServer:
    """Bind a ``ThreadingHTTPServer`` to ``config`` and bind the snapshot.

    Returns the constructed server instance (already snapshot-bound) without
    starting the request loop, so tests may drive it on an ephemeral port
    via ``server.serve_forever()`` in a thread.
    """
    configure_logging()
    server = _GuiServer((config.host, config.port), _Handler)
    server.bind_snapshot(snapshot)
    _logger.info(
        "gui server bound host=%s port=%d", config.host, server.server_address[1]
    )
    return server


# ``os`` is imported for downstream tests that may want
# ``os.environ`` overrides; keep the import explicit so the stdlib-only
# audit can see the dependency surface.
_ = os
