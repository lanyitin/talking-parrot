"""Unit tests for ``TranscriptionBackendFactory``."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from talking_parrot.transcription.factory import TranscriptionBackendFactory
from talking_parrot.transcription.faster_whisper_backend import (
    FasterWhisperBackend,
)
from talking_parrot.transcription.mlx_whisper_backend import MLXWhisperBackend


# ---------------------------------------------------------------------------
# default_for_platform
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("platform_name", "machine_name", "expected"),
    [
        ("darwin", "arm64", "mlx-whisper"),
        ("darwin", "x86_64", "faster-whisper"),
        ("linux", "x86_64", "faster-whisper"),
        ("win32", "AMD64", "faster-whisper"),
    ],
)
def test_default_for_platform(
    platform_name: str, machine_name: str, expected: str
) -> None:
    """``default_for_platform`` returns mlx-whisper only for darwin+arm64."""
    with (
        patch.object(sys, "platform", platform_name),
        patch("platform.machine", return_value=machine_name),
    ):
        assert TranscriptionBackendFactory.default_for_platform() == expected


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


def test_create_faster_whisper(monkeypatch: pytest.MonkeyPatch) -> None:
    """``create("faster-whisper")`` returns a ``FasterWhisperBackend``."""
    monkeypatch.delenv("TRANSCRIPTION_BACKEND", raising=False)
    factory = TranscriptionBackendFactory()
    backend = factory.create("faster-whisper")
    assert isinstance(backend, FasterWhisperBackend)


def test_create_mlx_whisper_under_arm64_darwin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``create("mlx-whisper")`` returns ``MLXWhisperBackend`` under patched arm64-darwin."""
    monkeypatch.delenv("TRANSCRIPTION_BACKEND", raising=False)
    with (
        patch.object(sys, "platform", "darwin"),
        patch("platform.machine", return_value="arm64"),
    ):
        factory = TranscriptionBackendFactory()
        backend = factory.create("mlx-whisper")
        assert isinstance(backend, MLXWhisperBackend)


def test_create_unknown_name_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown name raises ``ValueError`` containing ``"Unknown transcription backend"``."""
    monkeypatch.delenv("TRANSCRIPTION_BACKEND", raising=False)
    factory = TranscriptionBackendFactory()
    with pytest.raises(ValueError) as exc_info:
        factory.create("openai-whisper")
    assert "Unknown transcription backend" in str(exc_info.value)


def test_create_caches_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated ``create`` calls with the same name return the same instance."""
    monkeypatch.delenv("TRANSCRIPTION_BACKEND", raising=False)
    factory = TranscriptionBackendFactory()
    a = factory.create("faster-whisper")
    b = factory.create("faster-whisper")
    assert a is b


def test_env_var_overrides_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    """``TRANSCRIPTION_BACKEND="faster-whisper"`` overrides arg ``"mlx-whisper"``."""
    monkeypatch.setenv("TRANSCRIPTION_BACKEND", "faster-whisper")
    factory = TranscriptionBackendFactory()
    backend = factory.create("mlx-whisper")
    assert isinstance(backend, FasterWhisperBackend)


def test_empty_env_var_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """``TRANSCRIPTION_BACKEND=""`` does not override the argument."""
    monkeypatch.setenv("TRANSCRIPTION_BACKEND", "")
    factory = TranscriptionBackendFactory()
    backend = factory.create("faster-whisper")
    assert isinstance(backend, FasterWhisperBackend)
