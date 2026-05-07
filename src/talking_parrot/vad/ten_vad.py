"""TenVADBackend — VAD backend wrapping the ``ten_vad`` library.

The ``ten_vad.TenVad`` instance is lazy-initialised on the first
``analyze()`` call and cached for all subsequent calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import structlog

from talking_parrot.vad.backend import VADBackend

if TYPE_CHECKING:
    from talking_parrot.models.vad import RawVadFrame

logger = structlog.get_logger(__name__)

try:
    from ten_vad import TenVad  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    TenVad = None  # type: ignore[assignment,misc]


class TenVADBackend(VADBackend):
    """VAD backend wrapping ``ten_vad.TenVad``.

    Splits PCM audio into fixed-size chunks of ``hop_size`` samples and
    calls ``TenVad.process()`` on each chunk to obtain per-frame speech
    probabilities.

    The ``TenVad`` instance is lazy-initialised on the first ``analyze()``
    call so that import-time cost is avoided.

    Args:
        hop_size: Number of 16-bit PCM samples per processing chunk.
            At 16 kHz, 256 samples correspond to 16 ms per frame.
        threshold: Detection threshold passed to ``TenVad`` at construction.
            The stage uses ``result.probability`` directly; the threshold
            only affects the ``flag`` field in the TEN library output and is
            not used by ``VADStage``.
    """

    def __init__(self, hop_size: int = 256, threshold: float = 0.5) -> None:
        """Initialise TenVADBackend with processing parameters.

        Args:
            hop_size: Samples per chunk (frame). Default 256 = 16 ms at 16 kHz.
            threshold: Detection threshold forwarded to the underlying TenVad instance.
        """
        self._hop_size = hop_size
        self._threshold = threshold
        self._ten_vad_instance = None

    @property
    def name(self) -> str:
        """Return the unique backend identifier ``"ten_vad"``."""
        return "ten_vad"

    def _get_instance(self):
        """Return the cached TenVad instance, creating it on first call."""
        if self._ten_vad_instance is None:
            if TenVad is None:
                raise ImportError(  # pragma: no cover
                    "ten_vad package is not installed. Install it to use TenVADBackend."
                )

            logger.debug(
                "calling ten_vad.TenVad (constructor)",
                hop_size=self._hop_size,
                threshold=self._threshold,
            )
            instance = TenVad(self._hop_size, self._threshold)
            logger.debug(
                "ten_vad.TenVad constructor returned",
                result_type=type(instance).__name__,
                result_summary=repr(instance)[:200],
            )
            assert instance is not None, (
                "ten_vad.TenVad() returned None — check whether the library API changed."
            )
            self._ten_vad_instance = instance
        return self._ten_vad_instance

    def analyze(self, audio_data: bytes, sample_rate: int) -> list["RawVadFrame"]:
        """Analyse audio and return one ``RawVadFrame`` per ``hop_size``-sample chunk.

        PCM bytes are interpreted as a sequence of 16-bit signed little-endian
        samples. Trailing samples that do not form a complete chunk are ignored.

        Args:
            audio_data: Raw 16-bit PCM audio bytes (mono).
            sample_rate: Sample rate in Hz; used only for ``time_ms`` calculation.

        Returns:
            List of ``RawVadFrame`` sorted by ascending ``time_ms``.
        """
        from talking_parrot.models.vad import RawVadFrame

        hop_size = self._hop_size
        num_samples = len(audio_data) // 2  # 16-bit = 2 bytes per sample
        num_frames = num_samples // hop_size

        if num_frames == 0:
            return []

        instance = self._get_instance()
        frames: list[RawVadFrame] = []

        # ten_vad.TenVad.process expects np.ndarray[int16] of shape (hop_size,);
        # decode the whole buffer once and slice per frame.
        all_samples = np.frombuffer(
            audio_data[: num_frames * hop_size * 2], dtype=np.int16
        )

        for i in range(num_frames):
            chunk = all_samples[i * hop_size : (i + 1) * hop_size]

            logger.debug(
                "calling ten_vad.TenVad.process",
                frame_index=i,
                hop_size=hop_size,
            )
            result = instance.process(chunk)
            logger.debug(
                "ten_vad.TenVad.process returned",
                result_type=type(result).__name__,
                result_summary=repr(result)[:200],
            )

            assert isinstance(result, tuple) and len(result) == 2, (
                f"ten_vad.TenVad.process() returned {type(result)!r}, "
                "expected a (probability, flags) tuple. "
                "Check whether the library API changed."
            )
            probability = float(result[0])

            time_ms = round(i * hop_size / sample_rate * 1000)
            frames.append(RawVadFrame(time_ms=time_ms, prob=probability))

        return frames
