"""Static check that ``talking_parrot.gui`` does not import sibling subsystems."""

from __future__ import annotations

import ast
from pathlib import Path

_FORBIDDEN_PREFIXES = (
    "talking_parrot.regression",
    "talking_parrot.mcp",
)


def _gather_imports(root: Path) -> list[str]:
    imports: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
    return imports


def test_gui_does_not_import_regression_or_mcp() -> None:
    gui_root = Path(__file__).resolve().parents[3] / "src" / "talking_parrot" / "gui"
    imports = _gather_imports(gui_root)
    for imported in imports:
        for forbidden in _FORBIDDEN_PREFIXES:
            assert not imported.startswith(forbidden), (
                f"forbidden cross-package import: {imported!r}"
            )
