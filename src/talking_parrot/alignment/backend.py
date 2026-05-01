"""Abstract :class:`AlignmentBackend` interface.

Every concrete forced-alignment backend implements this ABC. The interface is
intentionally minimal: a backend is a language-bound, granularity-declaring
object that turns ``(audio_data, sample_rate, transcript)`` into a list of
chunk-relative :class:`AlignedToken` instances.

The backend is **not** aware of pipeline-level concepts such as chunk indices
or absolute timestamps. The :class:`AlignmentStage` is responsible for shifting
chunk-relative timestamps to absolute time and assembling
:class:`AlignmentResult` objects.
"""

from __future__ import annotations

import abc

from talking_parrot.models.context import AlignmentGranularity
from talking_parrot.models.transcription import AlignedToken


class AlignmentBackend(abc.ABC):
    """Abstract base class for forced-alignment backends.

    Concrete subclasses MUST implement:

    - :pyattr:`language` — read-only ISO language code (e.g. ``"en"``, ``"ja"``).
    - :pyattr:`granularity` — read-only :class:`AlignmentGranularity`.
    - :pymeth:`align` — chunk-relative forced alignment of a transcript.

    Direct instantiation raises :class:`TypeError` because the class is
    abstract.
    """

    @property
    @abc.abstractmethod
    def language(self) -> str:
        """Return the ISO language code this backend serves."""

    @property
    @abc.abstractmethod
    def granularity(self) -> AlignmentGranularity:
        """Return the alignment granularity this backend produces."""

    @abc.abstractmethod
    def align(
        self, audio_data: bytes, sample_rate: int, transcript: str
    ) -> list[AlignedToken]:
        """Force-align ``transcript`` to ``audio_data``.

        Args:
            audio_data: 16-bit signed little-endian PCM bytes for a single
                chunk of audio.
            sample_rate: Sample rate of ``audio_data`` in Hz (typically 16000).
            transcript: The text to force-align against the audio.

        Returns:
            A list of :class:`AlignedToken` whose ``start_ms`` / ``end_ms``
            are measured **from the first sample of ``audio_data``** (i.e.
            chunk-relative, not absolute).
        """
