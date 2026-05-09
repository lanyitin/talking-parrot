"""Unit tests for ``talking_parrot.gui.cli``."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from talking_parrot.gui import cli as gui_cli


def test_gui_config_defaults() -> None:
    """``GuiConfig()`` yields the documented defaults."""
    config = gui_cli.GuiConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 8765
    assert config.project is None


def test_resolve_config_env_overrides_default() -> None:
    """Env vars override the documented defaults when no CLI flag is given."""
    env = {
        "TALKING_PARROT_GUI_HOST": "10.0.0.5",
        "TALKING_PARROT_GUI_PORT": "9000",
    }
    config = gui_cli.resolve_config([], env=env)
    assert config.host == "10.0.0.5"
    assert config.port == 9000


def test_resolve_config_cli_overrides_env() -> None:
    """CLI flags override env vars."""
    env = {
        "TALKING_PARROT_GUI_HOST": "10.0.0.5",
        "TALKING_PARROT_GUI_PORT": "9000",
    }
    config = gui_cli.resolve_config(["--port", "9100"], env=env)
    assert config.port == 9100


def test_loader_called_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The CLI calls ``FileSnapshotLoader.load`` exactly once."""
    project = tmp_path / "p.tp"
    project.write_text("{}", encoding="utf-8")
    counter = {"n": 0}

    class _FakeServer:
        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            pass

    def _fake_load(self, source):  # type: ignore[no-untyped-def]
        counter["n"] += 1
        from talking_parrot.shared import AudioInfo, ProjectSnapshot

        return ProjectSnapshot(
            version="1.0",
            created_at="2026-05-09",
            source_path="",
            config_snapshot={},
            audio_info=AudioInfo(
                sample_rate=16000, duration_ms=0, rms_mean=0.0, rms_peak=0.0
            ),
        )

    with patch("talking_parrot.gui.cli.FileSnapshotLoader.load", _fake_load):
        with patch(
            "talking_parrot.gui.cli.http_server.serve",
            return_value=_FakeServer(),
        ):
            rc = gui_cli.main(["--project", str(project)])
    assert rc == 0
    assert counter["n"] == 1


def test_missing_project_exits(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing ``--project`` and env var triggers a non-zero exit."""
    monkeypatch.delenv("TALKING_PARROT_GUI_PROJECT", raising=False)
    rc = gui_cli.main([])
    assert rc != 0
    captured = capsys.readouterr()
    assert "--project" in captured.err
    assert "TALKING_PARROT_GUI_PROJECT" in captured.err
