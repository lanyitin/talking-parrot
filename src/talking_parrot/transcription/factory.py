"""``TranscriptionBackendFactory`` — name- and platform-aware backend selection.

The factory:
- Maps the literal strings ``"faster-whisper"`` and ``"mlx-whisper"`` to the
  concrete backend classes.
- Honours the ``TRANSCRIPTION_BACKEND`` environment variable as a runtime
  override (empty value is ignored).
- Caches one instance per resolved ``backend_name`` for the lifetime of the
  factory so cascade steps that share a backend reuse model state.
- Exposes ``default_for_platform()`` for callers that want to construct a
  default config template (e.g. CLI bootstrapping).
"""

from __future__ import annotations

import structlog
import os
import platform
import sys

from talking_parrot.transcription.backend import TranscriptionBackend
from talking_parrot.transcription.faster_whisper_backend import (
    FasterWhisperBackend,
)
from talking_parrot.transcription.mlx_whisper_backend import MLXWhisperBackend

logger = structlog.get_logger(__name__)


class TranscriptionBackendFactory:
    """Factory that resolves backend names to ``TranscriptionBackend`` instances.

    Usage:
        >>> factory = TranscriptionBackendFactory()
        >>> backend = factory.create("faster-whisper")
    """

    def __init__(self) -> None:
        """Initialise an empty per-instance backend cache."""
        self._cache: dict[str, TranscriptionBackend] = {}

    def create(self, backend_name: str) -> TranscriptionBackend:
        """Return the cached or freshly constructed backend for *backend_name*.

        The ``TRANSCRIPTION_BACKEND`` environment variable, when set to a
        non-empty value, overrides *backend_name*. Unknown names raise
        ``ValueError`` whose message contains ``"Unknown transcription
        backend"``.
        """
        env_override = os.environ.get("TRANSCRIPTION_BACKEND")
        effective_name = env_override or backend_name

        if effective_name in self._cache:
            return self._cache[effective_name]

        if effective_name == "faster-whisper":
            backend: TranscriptionBackend = FasterWhisperBackend()
        elif effective_name == "mlx-whisper":
            backend = MLXWhisperBackend()
        else:
            raise ValueError(f"Unknown transcription backend: {effective_name}")

        self._cache[effective_name] = backend
        return backend

    @staticmethod
    def default_for_platform() -> str:
        """Return the recommended default backend name for the current platform.

        Returns ``"mlx-whisper"`` only on Apple Silicon macOS, otherwise
        ``"faster-whisper"``.
        """
        if sys.platform == "darwin" and platform.machine() == "arm64":
            return "mlx-whisper"
        return "faster-whisper"
