from __future__ import annotations

import abc


class AudioReader(abc.ABC):
    @property
    @abc.abstractmethod
    def sample_rate(self) -> int: ...

    @property
    @abc.abstractmethod
    def duration_ms(self) -> int:
        """Total audio duration in milliseconds."""

    @abc.abstractmethod
    def read(self, start_ms: int, end_ms: int) -> bytes:
        """Return PCM bytes for [start_ms, end_ms).

        Raises ValueError if start_ms < 0, start_ms >= end_ms,
        or end_ms > media duration.
        """
