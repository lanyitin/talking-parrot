"""``MLXWhisperBackend`` — wraps ``mlx_whisper.transcribe``.

This backend is restricted to Apple Silicon macOS. The ``mlx_whisper`` and
``numpy`` modules are imported lazily at first ``transcribe()`` call so that
the package becomes a true optional dependency on platforms where it is not
applicable.

Audio decoding follows the project's ``audio-io`` capability: the source audio
file is opened via ``FfmpegAudioReader``, the chunk window
``[start_ms, end_ms)`` is read as little-endian int16 PCM bytes, then converted
to a float32 numpy array scaled to ``[-1.0, 1.0]`` for the model.
"""

from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path
from typing import Any

import structlog

from talking_parrot.io.audio_decoder import FfmpegAudioReader
from talking_parrot.models.chunk import Chunk
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.transcription.backend import TranscriptionBackend

logger = structlog.get_logger(__name__)


class MLXWhisperBackend(TranscriptionBackend):
    """Apple-Silicon-only transcription backend using ``mlx_whisper``.

    Construction enforces ``sys.platform == "darwin" and
    platform.machine() == "arm64"``; otherwise ``RuntimeError`` is raised.
    The ``mlx_whisper`` and ``numpy`` modules are imported lazily on first
    ``transcribe()`` call.
    """

    def __init__(self) -> None:
        """Validate the runtime platform; defer all imports to ``transcribe()``."""
        if sys.platform != "darwin" or platform.machine() != "arm64":
            raise RuntimeError("MLXWhisperBackend requires Apple Silicon macOS")

    @property
    def name(self) -> str:
        """Return the literal identifier ``"mlx-whisper"``."""
        return "mlx-whisper"

    def transcribe(
        self,
        audio_path: Path,
        chunk: Chunk,
        model: str,
        language: str | None,
    ) -> list[TranscriptionResult]:
        """Decode the chunk window and emit one ``TranscriptionResult`` per segment dict.

        The ``model`` string is passed verbatim to ``path_or_hf_repo`` — no
        magical translation is performed. Returns ``[]`` when the underlying
        dict has an empty ``segments`` list — callers MUST treat this as a
        valid no-op outcome (per the ``transcription-backend`` contract).
        """
        np = self._import_numpy()
        mlx_whisper = self._import_mlx_whisper()

        audio_array = self._decode_chunk_window(audio_path, chunk, np)

        logger.info(
            "calling mlx_whisper.transcribe",
            path_or_hf_repo=model,
            language=language,
            num_samples=len(audio_array),
        )
        result_dict = mlx_whisper.transcribe(
            audio_array,
            path_or_hf_repo=model,
            language=language,
        )
        logger.info(
            "mlx_whisper.transcribe returned",
            result_type=type(result_dict).__name__,
        )

        # Validate library return shape per third-party-call assertion rules.
        assert isinstance(result_dict, dict), (
            f"mlx_whisper.transcribe returned {type(result_dict)!r}, "
            "expected dict — API may have changed"
        )
        assert "segments" in result_dict, (
            "mlx_whisper.transcribe result missing 'segments' — API may have changed"
        )

        segments = list(result_dict["segments"])

        dict_language = result_dict.get("language")
        result_language = dict_language if dict_language is not None else language

        results: list[TranscriptionResult] = []
        for seg in segments:
            seg_text = (seg.get("text") or "").strip()
            start_ms = chunk.start_ms + int(round(seg["start"] * 1000))
            end_ms = chunk.start_ms + int(round(seg["end"] * 1000))
            metrics = TranscriptionMetrics(
                avg_logprob=seg["avg_logprob"],
                compression_ratio=seg["compression_ratio"],
                no_speech_prob=seg["no_speech_prob"],
                repetition_ratio=_segment_repetition_ratio(seg_text),
            )
            results.append(
                TranscriptionResult(
                    chunk_index=chunk.index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=seg_text,
                    language=result_language,  # type: ignore[arg-type]
                    model_used=model,
                    metrics=metrics,
                    aligned_tokens=None,
                )
            )
        return results

    @staticmethod
    def _decode_chunk_window(audio_path: Path, chunk: Chunk, np: Any) -> Any:
        """Read int16 PCM for ``[chunk.start_ms, chunk.end_ms)`` and convert to float32.

        Uses ``FfmpegAudioReader`` (the project's ``audio-io`` helper) to read
        the requested window, then frombuffers the raw bytes as int16 and
        scales to float32 in ``[-1.0, 1.0]``.
        """
        reader = FfmpegAudioReader(str(audio_path))
        logger.debug(
            "calling FfmpegAudioReader.read",
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
        )
        pcm_bytes = reader.read(chunk.start_ms, chunk.end_ms)
        logger.debug(
            "FfmpegAudioReader.read returned",
            num_bytes=len(pcm_bytes),
        )
        assert isinstance(pcm_bytes, bytes), (
            f"FfmpegAudioReader.read returned {type(pcm_bytes)!r}, expected bytes"
        )

        int16_array = np.frombuffer(pcm_bytes, dtype=np.int16)
        # Scale to float32 in [-1.0, 1.0]; numpy returns a new array.
        float32_array = int16_array.astype(np.float32) / 32768.0
        return float32_array

    @staticmethod
    def _import_mlx_whisper() -> Any:
        """Lazy-import ``mlx_whisper`` and raise an actionable ImportError on failure."""
        try:
            logger.debug("calling importlib.import_module('mlx_whisper')")
            mlx_whisper = importlib.import_module("mlx_whisper")
            logger.debug(
                "importlib.import_module('mlx_whisper') returned",
                result_type=type(mlx_whisper).__name__,
            )
        except ModuleNotFoundError as exc:
            raise ImportError("Install with: uv add 'talking-parrot[mlx]'") from exc

        assert hasattr(mlx_whisper, "transcribe"), (
            "mlx_whisper module is missing 'transcribe' — API may have changed"
        )
        return mlx_whisper

    @staticmethod
    def _import_numpy() -> Any:
        """Lazy-import ``numpy`` (transitively required by ``mlx_whisper``)."""
        try:
            logger.debug("calling importlib.import_module('numpy')")
            np = importlib.import_module("numpy")
            logger.debug(
                "importlib.import_module('numpy') returned",
                result_type=type(np).__name__,
            )
        except ModuleNotFoundError as exc:
            raise ImportError("Install with: uv add 'talking-parrot[mlx]'") from exc
        return np


def _segment_repetition_ratio(text: str) -> float:
    """Return ``1 - unique/total`` over whitespace-split tokens; ``0.0`` if empty."""
    tokens = text.split()
    if not tokens:
        return 0.0
    return 1.0 - (len(set(tokens)) / len(tokens))
