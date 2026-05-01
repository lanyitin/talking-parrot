"""Abstract VAD backend interface.

All concrete VAD backends must inherit from ``VADBackend`` and implement
the ``name`` property and the ``analyze`` method.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from talking_parrot.models.vad import RawVadFrame


class VADBackend(abc.ABC):
    """Abstract base class defining the contract for all VAD backends.

    Concrete implementations must provide:

    - ``name``: a unique string identifier for the backend (used as the formula
      variable prefix, e.g. ``"ten_vad"`` → variable ``ten_vad_prob``).
    - ``analyze(audio_data, sample_rate)``: analyse a complete PCM audio buffer
      and return one ``RawVadFrame`` per processing chunk, in chronological order.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier for this backend, used as the formula variable prefix."""

    @abc.abstractmethod
    def analyze(self, audio_data: bytes, sample_rate: int) -> list["RawVadFrame"]:
        """Analyse audio and return per-frame speech probabilities.

        Args:
            audio_data: Raw 16-bit PCM audio bytes (mono, 16 kHz).
            sample_rate: Sample rate in Hz. The pipeline always uses 16000.

        Returns:
            A list of ``RawVadFrame`` instances sorted by ascending ``time_ms``.
            Returns an empty list when no frames can be produced (e.g., audio
            shorter than one processing chunk).
        """
