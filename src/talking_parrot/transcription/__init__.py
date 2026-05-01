"""Transcription subpackage — backends and factory for the transcription stage.

This package provides:
- ``TranscriptionBackend``: abstract base class defining the contract for all
  transcription backends.
- ``FasterWhisperBackend``: cross-platform backend wrapping ``faster_whisper``.
- ``MLXWhisperBackend``: Apple-Silicon-only backend wrapping ``mlx_whisper``.
- ``TranscriptionBackendFactory``: name- and platform-aware factory selecting
  between the available backends.
"""

from talking_parrot.transcription.backend import TranscriptionBackend
from talking_parrot.transcription.factory import TranscriptionBackendFactory
from talking_parrot.transcription.faster_whisper_backend import (
    FasterWhisperBackend,
)
from talking_parrot.transcription.mlx_whisper_backend import MLXWhisperBackend

__all__ = [
    "TranscriptionBackend",
    "TranscriptionBackendFactory",
    "FasterWhisperBackend",
    "MLXWhisperBackend",
]
