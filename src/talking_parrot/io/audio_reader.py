from __future__ import annotations

import abc


class AudioReader(abc.ABC):
    @property
    @abc.abstractmethod
    def sample_rate(self) -> int: ...

    @abc.abstractmethod
    def read(self, start_ms: int, end_ms: int) -> bytes:
        """Return PCM bytes for [start_ms, end_ms).

        Raises ValueError if start_ms < 0, start_ms >= end_ms,
        or end_ms > media duration.
        """
