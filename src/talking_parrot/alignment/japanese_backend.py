"""Japanese forced-alignment backend wrapping HuggingFace Wav2Vec2ForCTC.

The backend produces **character-level** :class:`AlignedToken` instances,
one per Unicode codepoint in the (whitespace-stripped) transcript. ``torch``
and ``transformers`` are lazy-imported on the first :meth:`align` call.
"""

from __future__ import annotations

import structlog
from typing import Any

from talking_parrot.alignment.backend import AlignmentBackend
from talking_parrot.alignment.ctc import ctc_align
from talking_parrot.models.context import AlignmentGranularity
from talking_parrot.models.transcription import AlignedToken

logger = structlog.get_logger(__name__)


# Module-level constant exposed for testability — tests can monkey-patch this
# to a sentinel value to assert the backend forwarded the right model id.
MODEL_ID: str = "jonatasgrosman/wav2vec2-large-xlsr-53-japanese"

# 50 Hz emission frame rate at 16 kHz input (XLSR convolutional stride).
_FRAME_RATE_HZ: float = 50.0
_MIN_SAMPLES: int = 400


class JapaneseAlignmentBackend(AlignmentBackend):
    """HuggingFace XLSR Japanese character-level aligner."""

    def __init__(self) -> None:
        """Defer all heavy work to the first ``align()`` call."""
        self._loaded: bool = False
        self._torch: Any = None
        self._device: Any = None
        self._processor: Any = None
        self._model: Any = None

    @property
    def language(self) -> str:
        """Return ``"ja"``."""
        return "ja"

    @property
    def granularity(self) -> AlignmentGranularity:
        """Return :pyattr:`AlignmentGranularity.CHARACTER`."""
        return AlignmentGranularity.CHARACTER

    def align(
        self, audio_data: bytes, sample_rate: int, transcript: str
    ) -> list[AlignedToken]:
        """Force-align ``transcript`` to ``audio_data`` and return character-level tokens.

        Args:
            audio_data: 16-bit signed little-endian PCM bytes (mono).
            sample_rate: Sample rate in Hz (typically 16000).
            transcript: Japanese text to align.

        Returns:
            One :class:`AlignedToken` per Unicode codepoint in the (whitespace
            stripped) transcript, with chunk-relative timestamps.

        Raises:
            ImportError: If ``torch`` or ``transformers`` is not installed.
        """
        self._ensure_loaded()
        assert self._processor is not None  # for type-checkers

        transcript_tokens = self._prepare_tokens(transcript)
        audio_array = self._decode(audio_data)

        logger.debug(
            "calling Wav2Vec2Processor for JapaneseAlignmentBackend",
            sample_rate=sample_rate,
        )
        proc_out = self._processor(
            audio_array, sampling_rate=sample_rate, return_tensors="pt"
        )
        input_values = proc_out.input_values.to(self._device)

        logger.info("calling Wav2Vec2ForCTC forward for JapaneseAlignmentBackend")
        model_out = self._model(input_values=input_values)
        logits = model_out.logits
        assert hasattr(logits, "shape"), (
            "Wav2Vec2ForCTC output has no .logits.shape — API may have changed"
        )
        emissions = self._torch.log_softmax(logits, dim=-1)
        logger.info(
            "Wav2Vec2ForCTC forward returned",
            logits_shape=tuple(logits.shape),
        )

        dictionary = self._processor.tokenizer.get_vocab()
        blank_id = self._processor.tokenizer.pad_token_id
        assert isinstance(dictionary, dict), (
            f"processor.tokenizer.get_vocab() returned {type(dictionary)!r}, "
            "expected dict — API may have changed"
        )
        assert isinstance(blank_id, int), (
            f"processor.tokenizer.pad_token_id is {type(blank_id)!r}, "
            "expected int — API may have changed"
        )

        return ctc_align(
            emissions[0],
            dictionary,
            transcript_tokens,
            blank_id,
            frame_rate_hz=_FRAME_RATE_HZ,
            segment_offset_ms=0,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Lazy-import torch + transformers and load the XLSR model once."""
        if self._loaded:
            return

        try:
            import torch  # noqa: WPS433 (lazy import is intentional)
            import transformers  # noqa: WPS433
        except ModuleNotFoundError as exc:
            raise ImportError(
                "JapaneseAlignmentBackend requires torch and transformers. "
                "Install with: uv add 'talking-parrot[align]'"
            ) from exc

        device_name = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(
            "calling transformers.Wav2Vec2Processor.from_pretrained",
            model_id=MODEL_ID,
        )
        processor = transformers.Wav2Vec2Processor.from_pretrained(MODEL_ID)
        logger.debug(
            "calling transformers.Wav2Vec2ForCTC.from_pretrained",
            model_id=MODEL_ID,
            device=device_name,
        )
        model = transformers.Wav2Vec2ForCTC.from_pretrained(MODEL_ID).to(device_name)

        self._torch = torch
        self._device = device_name
        self._processor = processor
        self._model = model
        self._loaded = True

    def _prepare_tokens(self, transcript: str) -> list[str]:
        """Strip ASCII whitespace and return one token per Unicode codepoint."""
        # Strip leading/trailing whitespace then drop every internal ASCII
        # whitespace character (space, tab, newline).
        stripped = transcript.strip()
        cleaned = "".join(ch for ch in stripped if ch not in (" ", "\t", "\n"))
        return list(cleaned)

    def _decode(self, audio_data: bytes) -> Any:
        """Decode int16 PCM bytes into a normalised numpy float32 1-D array."""
        import numpy as np

        logger.debug(
            "calling np.frombuffer for Japanese alignment audio decode",
            num_bytes=len(audio_data),
        )
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.shape[0] < _MIN_SAMPLES:
            pad = np.zeros(_MIN_SAMPLES - samples.shape[0], dtype=np.float32)
            samples = np.concatenate([samples, pad])
        return samples
