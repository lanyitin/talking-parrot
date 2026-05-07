"""``FasterWhisperBackend`` — wraps ``faster_whisper.WhisperModel``.

The class lazy-imports ``faster_whisper`` on the first ``transcribe()`` call,
caches one ``WhisperModel`` instance per distinct ``model`` name, and converts
provider-specific output into a ``TranscriptionResult`` with the four portable
``TranscriptionMetrics`` fields described by the ``transcription-backend``
spec.
"""

from __future__ import annotations

import importlib
import structlog
from pathlib import Path
from typing import Any

from talking_parrot.models.chunk import Chunk
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.transcription.backend import TranscriptionBackend

logger = structlog.get_logger(__name__)


class FasterWhisperBackend(TranscriptionBackend):
    """Cross-platform transcription backend using ``faster_whisper``.

    Models are lazy-loaded on first use and cached per ``model`` name on the
    instance. The actual ``faster_whisper`` import is deferred until the first
    ``transcribe()`` call so that the package becomes a true optional
    dependency.
    """

    def __init__(self) -> None:
        """Initialise an empty model cache. No imports occur here."""
        self._models: dict[str, Any] = {}

    @property
    def name(self) -> str:
        """Return the literal identifier ``"faster-whisper"``."""
        return "faster-whisper"

    def transcribe(
        self,
        audio_path: Path,
        chunk: Chunk,
        model: str,
        language: str | None,
    ) -> TranscriptionResult:
        """Transcribe ``[chunk.start_ms, chunk.end_ms)`` of ``audio_path``.

        Lazily imports ``faster_whisper``, instantiates the requested model on
        first use (cached for subsequent calls), invokes
        ``WhisperModel.transcribe`` with ``clip_timestamps`` set to the chunk
        window in seconds, and assembles the cross-backend
        ``TranscriptionResult`` per the ``transcription-backend`` contract.
        """
        whisper_model = self._get_model(model)

        clip_start_s = chunk.start_ms / 1000
        clip_end_s = chunk.end_ms / 1000
        logger.debug(
            "calling faster_whisper.WhisperModel.transcribe",
            audio_path=str(audio_path),
            language=language,
            clip_timestamps=[clip_start_s, clip_end_s],
            model=model,
        )
        segments_iter, info = whisper_model.transcribe(
            str(audio_path),
            language=language,
            clip_timestamps=[clip_start_s, clip_end_s],
        )
        segments = list(segments_iter)
        logger.debug(
            "faster_whisper.WhisperModel.transcribe returned",
            num_segments=len(segments),
            info_language=getattr(info, "language", None),
        )

        # Validate library return shape per third-party-call assertion rules.
        assert hasattr(info, "language"), (
            "faster_whisper.WhisperModel.transcribe returned info without "
            "'language' attribute — API may have changed"
        )

        text = " ".join(seg.text for seg in segments).strip()
        metrics = _compute_metrics(segments, text)
        result_language = info.language

        return TranscriptionResult(
            chunk_index=chunk.index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text=text,
            language=result_language,
            model_used=model,
            metrics=metrics,
            aligned_tokens=None,
        )

    def _get_model(self, model: str) -> Any:
        """Return the cached ``WhisperModel`` for *model*, constructing on first use.

        Raises ``ImportError`` with an actionable install hint when
        ``faster_whisper`` is not importable.
        """
        if model in self._models:
            return self._models[model]

        try:
            logger.debug(
                "calling importlib.import_module('faster_whisper')",
            )
            faster_whisper = importlib.import_module("faster_whisper")
            logger.debug(
                "importlib.import_module('faster_whisper') returned",
                result_type=type(faster_whisper).__name__,
            )
        except ModuleNotFoundError as exc:
            raise ImportError(
                "Install with: uv add 'talking-parrot[faster-whisper]'"
            ) from exc

        assert hasattr(faster_whisper, "WhisperModel"), (
            "faster_whisper module is missing 'WhisperModel' — API may have changed"
        )

        logger.debug(
            "calling faster_whisper.WhisperModel",
            model_size_or_path=model,
        )
        instance = faster_whisper.WhisperModel(model_size_or_path=model)
        logger.debug(
            "faster_whisper.WhisperModel returned",
            result_type=type(instance).__name__,
        )
        self._models[model] = instance
        return instance


def _compute_metrics(segments: list[Any], text: str) -> TranscriptionMetrics:
    """Derive the four cross-backend ``TranscriptionMetrics`` from raw segments.

    Rules (per ``transcription-backend`` spec):
    - ``avg_logprob``: weighted mean of segment ``avg_logprob`` weighted by
      segment duration in milliseconds.
    - ``compression_ratio``: weighted mean of segment ``compression_ratio``
      weighted by segment duration in milliseconds.
    - ``no_speech_prob``: maximum of segment ``no_speech_prob``.
    - ``repetition_ratio``: ``1 - unique_tokens / total_tokens`` over
      whitespace-split *text*; ``0.0`` when ``total_tokens == 0``.

    When *segments* is empty all weighted metrics fall back to ``0.0`` so the
    result is well-defined; this matches the empty-text case used by callers.
    """
    if not segments:
        avg_logprob = 0.0
        compression_ratio = 0.0
        no_speech_prob = 0.0
    else:
        total_duration_ms = 0.0
        weighted_logprob_sum = 0.0
        weighted_compression_sum = 0.0
        max_no_speech = float("-inf")
        for seg in segments:
            duration_ms = (seg.end - seg.start) * 1000.0
            total_duration_ms += duration_ms
            weighted_logprob_sum += seg.avg_logprob * duration_ms
            weighted_compression_sum += seg.compression_ratio * duration_ms
            if seg.no_speech_prob > max_no_speech:
                max_no_speech = seg.no_speech_prob

        if total_duration_ms > 0:
            avg_logprob = weighted_logprob_sum / total_duration_ms
            compression_ratio = weighted_compression_sum / total_duration_ms
        else:
            avg_logprob = 0.0
            compression_ratio = 0.0
        no_speech_prob = max_no_speech if max_no_speech != float("-inf") else 0.0

    tokens = text.split()
    if not tokens:
        repetition_ratio = 0.0
    else:
        repetition_ratio = 1.0 - (len(set(tokens)) / len(tokens))

    return TranscriptionMetrics(
        avg_logprob=avg_logprob,
        compression_ratio=compression_ratio,
        no_speech_prob=no_speech_prob,
        repetition_ratio=repetition_ratio,
    )
