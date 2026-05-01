from __future__ import annotations

import os
import functools

import ffmpeg

from talking_parrot.io.audio_reader import AudioReader


class FfmpegAudioReader(AudioReader):
    _SAMPLE_RATE = 16_000

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path
        self._duration_ms = self._probe_duration_ms()
        cache_size = self._default_cache_size()
        self._cached_read = functools.lru_cache(maxsize=cache_size)(self._decode)

    @staticmethod
    def _default_cache_size() -> int:
        return int(os.environ.get("AUDIO_CACHE_SIZE", "4"))

    def _probe_duration_ms(self) -> int:
        probe = ffmpeg.probe(self._file_path)
        duration_s = float(probe["format"]["duration"])
        return int(duration_s * 1000)

    def _decode(self, start_ms: int, end_ms: int) -> bytes:
        out, _ = (
            ffmpeg.input(self._file_path, ss=start_ms / 1000.0, to=end_ms / 1000.0)
            .output(
                "pipe:", format="s16le", acodec="pcm_s16le", ac=1, ar=self._SAMPLE_RATE
            )
            .run(capture_stdout=True, capture_stderr=True)
        )
        return out

    @property
    def sample_rate(self) -> int:
        return self._SAMPLE_RATE

    def read(self, start_ms: int, end_ms: int) -> bytes:
        if start_ms < 0 or start_ms >= end_ms or end_ms > self._duration_ms:
            raise ValueError(
                f"Invalid interval [{start_ms}, {end_ms}] for file with "
                f"duration {self._duration_ms} ms"
            )
        return self._cached_read(start_ms, end_ms)
