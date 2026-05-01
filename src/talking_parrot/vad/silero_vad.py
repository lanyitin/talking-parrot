"""SileroVADBackend — VAD backend wrapping the ``silero_vad`` library.

The Silero model is lazy-loaded via ``silero_vad.load_silero_vad()`` on the
first ``analyze()`` call and cached for all subsequent calls.
"""

from __future__ import annotations

import logging
import struct
from typing import TYPE_CHECKING

from talking_parrot.vad.backend import VADBackend

if TYPE_CHECKING:
    from talking_parrot.models.vad import RawVadFrame

logger = logging.getLogger(__name__)

try:
    from silero_vad import load_silero_vad  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    load_silero_vad = None  # type: ignore[assignment,misc]

try:
    import torch  # type: ignore[import-not-found]

    _TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover
    torch = None  # type: ignore[assignment]
    _TORCH_AVAILABLE = False


class SileroVADBackend(VADBackend):
    """VAD backend wrapping the ``silero_vad`` ONNX model.

    Splits PCM audio into fixed-size chunks of ``chunk_size`` samples and
    calls the loaded Silero model on each chunk to obtain per-frame speech
    probabilities.

    The model is lazy-loaded via ``silero_vad.load_silero_vad()`` on the
    first ``analyze()`` call so that import-time cost is avoided.

    Args:
        chunk_size: Number of 16-bit PCM samples per processing chunk.
            At 16 kHz, 512 samples correspond to 32 ms per frame.
    """

    def __init__(self, chunk_size: int = 512) -> None:
        """Initialise SileroVADBackend with the processing chunk size.

        Args:
            chunk_size: Samples per chunk (frame). Default 512 = 32 ms at 16 kHz.
        """
        self._chunk_size = chunk_size
        self._model = None

    @property
    def name(self) -> str:
        """Return the unique backend identifier ``"silero_vad"``."""
        return "silero_vad"

    def _get_model(self):
        """Return the cached Silero model, loading it on first call."""
        if self._model is None:
            if load_silero_vad is None:
                raise ImportError(  # pragma: no cover
                    "silero_vad package is not installed. "
                    "Install it to use SileroVADBackend."
                )

            logger.debug("calling silero_vad.load_silero_vad")
            model = load_silero_vad()
            logger.debug(
                "silero_vad.load_silero_vad returned",
                result_type=type(model).__name__,
                result_summary=repr(model)[:200],
            )
            assert model is not None, (
                "silero_vad.load_silero_vad() returned None — "
                "check whether the library API changed."
            )
            self._model = model
        return self._model

    def analyze(self, audio_data: bytes, sample_rate: int) -> list["RawVadFrame"]:
        """Analyse audio and return one ``RawVadFrame`` per ``chunk_size``-sample chunk.

        PCM bytes are interpreted as a sequence of 16-bit signed little-endian
        samples. Trailing samples that do not form a complete chunk are ignored.

        The Silero model is called with a tuple of integers representing the
        audio chunk and the sample rate. The model returns a tensor whose
        ``.item()`` method yields the speech probability as a float.

        Args:
            audio_data: Raw 16-bit PCM audio bytes (mono).
            sample_rate: Sample rate in Hz; used for both the model call and
                ``time_ms`` calculation.

        Returns:
            List of ``RawVadFrame`` sorted by ascending ``time_ms``.
        """
        from talking_parrot.models.vad import RawVadFrame

        chunk_size = self._chunk_size
        num_samples = len(audio_data) // 2  # 16-bit = 2 bytes per sample
        num_frames = num_samples // chunk_size

        if num_frames == 0:
            return []

        model = self._get_model()
        frames: list[RawVadFrame] = []

        for i in range(num_frames):
            byte_offset = i * chunk_size * 2
            chunk_bytes = audio_data[byte_offset : byte_offset + chunk_size * 2]
            chunk_ints = struct.unpack(f"<{chunk_size}h", chunk_bytes)
            # Silero model expects a float32 tensor in [-1.0, 1.0].
            # When torch is not available (e.g., during tests with mocked model),
            # fall back to a plain list of floats.
            float_samples = [s / 32768.0 for s in chunk_ints]
            if _TORCH_AVAILABLE and torch is not None:
                chunk_tensor = torch.tensor(float_samples, dtype=torch.float32)
            else:
                chunk_tensor = float_samples  # type: ignore[assignment]

            logger.debug(
                "calling silero_vad model",
                frame_index=i,
                chunk_size=chunk_size,
                sample_rate=sample_rate,
            )
            result_tensor = model(chunk_tensor, sample_rate)
            logger.debug(
                "silero_vad model returned",
                result_type=type(result_tensor).__name__,
                result_summary=repr(result_tensor)[:200],
            )

            assert result_tensor is not None, (
                "silero_vad model returned None — check whether the library API changed."
            )
            assert hasattr(result_tensor, "item"), (
                f"silero_vad model output missing 'item' method — "
                f"got type {type(result_tensor)!r}. Check whether the library API changed."
            )

            probability = result_tensor.item()

            assert isinstance(probability, float), (
                f"silero_vad model output .item() returned {type(probability)!r}, "
                "expected float. Check whether the library API changed."
            )

            time_ms = round(i * chunk_size / sample_rate * 1000)
            frames.append(RawVadFrame(time_ms=time_ms, prob=probability))

        return frames
