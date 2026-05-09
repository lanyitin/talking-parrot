"""Tests that ``python -m talking_parrot.regression --help`` works."""

from __future__ import annotations

import subprocess
import sys


def test_module_dunder_main_help_succeeds() -> None:
    """``python -m talking_parrot.regression --help`` exits zero."""
    result = subprocess.run(
        [sys.executable, "-m", "talking_parrot.regression", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "module --help should exit 0; got "
        f"{result.returncode}, stderr={result.stderr!r}"
    )
    out = result.stdout
    for flag in (
        "--samples-dir",
        "--results-dir",
        "--label",
        "--reset-baseline",
        "--cer-tolerance",
        "--confidence-tolerance",
        "--strict-missing",
    ):
        assert flag in out, f"expected {flag} in --help output, got: {out!r}"
