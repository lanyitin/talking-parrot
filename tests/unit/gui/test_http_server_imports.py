"""Verify ``gui.http_server`` only depends on stdlib and project-internal modules."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_FORBIDDEN_THIRD_PARTY_PREFIXES = (
    "aiohttp",
    "fastapi",
    "flask",
    "starlette",
    "tornado",
    "bottle",
    "werkzeug",
    "httpx",
    "requests",
    "pydantic",
    "structlog",
    "yaml",
    "ffmpeg",
)


def _module_root(name: str) -> str:
    """Return the top-level package name of an import target."""
    return name.split(".", 1)[0]


def test_no_third_party_imports() -> None:
    """``gui.http_server`` must import only stdlib or ``talking_parrot.*`` modules."""
    source_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "talking_parrot"
        / "gui"
        / "http_server.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    stdlib_names = set(sys.stdlib_module_names)
    seen: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                seen.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            seen.append(node.module)

    for imported in seen:
        root = _module_root(imported)
        assert root not in _FORBIDDEN_THIRD_PARTY_PREFIXES, (
            f"forbidden third-party import: {imported!r}"
        )
        assert root in stdlib_names or root == "talking_parrot", (
            f"unexpected non-stdlib, non-project import: {imported!r}"
        )
