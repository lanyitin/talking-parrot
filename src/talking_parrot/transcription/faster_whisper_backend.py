"""``FasterWhisperBackend`` — wraps ``faster_whisper.WhisperModel``.

The class lazy-imports ``faster_whisper`` on the first ``transcribe()`` call,
caches one ``WhisperModel`` instance per distinct ``model`` name, and emits one
``TranscriptionResult`` per yielded Whisper internal segment, with raw
per-segment ``TranscriptionMetrics`` as required by the
``transcription-backend`` and ``faster-whisper-backend`` specs.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import structlog

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
    ) -> list[TranscriptionResult]:
        """Transcribe ``[chunk.start_ms, chunk.end_ms)`` of ``audio_path``.

        Lazily imports ``faster_whisper``, instantiates the requested model on
        first use (cached for subsequent calls), invokes
        ``WhisperModel.transcribe`` with ``clip_timestamps`` set to the chunk
        window in seconds, and emits one ``TranscriptionResult`` per yielded
        Whisper internal segment in temporal order. Returns ``[]`` when the
        underlying iterator yields no segments — callers MUST treat this as a
        valid no-op outcome (per the ``transcription-backend`` contract).
        """
        whisper_model = self._get_model(model)

        clip_start_s = chunk.start_ms / 1000
        clip_end_s = chunk.end_ms / 1000

        logger.info(
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
        logger.info(
            "faster_whisper.WhisperModel.transcribe returned",
            num_segments=len(segments),
            info_language=getattr(info, "language", None),
        )

        # Validate library return shape per third-party-call assertion rules.
        assert hasattr(info, "language"), (
            "faster_whisper.WhisperModel.transcribe returned info without "
            "'language' attribute — API may have changed"
        )

        result_language = info.language

        results: list[TranscriptionResult] = []
        for seg in segments:
            seg_text = (seg.text or "").strip()
            start_ms = chunk.start_ms + int(round(seg.start * 1000))
            end_ms = chunk.start_ms + int(round(seg.end * 1000))
            metrics = TranscriptionMetrics(
                avg_logprob=seg.avg_logprob,
                compression_ratio=seg.compression_ratio,
                no_speech_prob=seg.no_speech_prob,
                repetition_ratio=_segment_repetition_ratio(seg_text),
            )
            results.append(
                TranscriptionResult(
                    chunk_index=chunk.index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=seg_text,
                    language=result_language,
                    model_used=model,
                    metrics=metrics,
                    aligned_tokens=None,
                )
            )
        return results

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


def _segment_repetition_ratio(text: str) -> float:
    """Return ``1 - unique/total`` over whitespace-split tokens; ``0.0`` if empty."""
    tokens = text.split()
    if not tokens:
        return 0.0
    return 1.0 - (len(set(tokens)) / len(tokens))
