"""English forced-alignment backend wrapping torchaudio's WAV2VEC2_ASR_BASE_960H.

The backend produces **word-level** :class:`AlignedToken` instances. Internally
it tokenises the transcript per character (lower-cased, with spaces replaced
by ``"|"``), runs the CTC kernel for character-level alignment, and groups
consecutive non-``"|"`` characters back into words.

``torch`` and ``torchaudio`` are lazy-imported on the first :meth:`align`
call. If either is missing, an :class:`ImportError` mentioning the
``talking-parrot[align]`` extra is raised.
"""

from __future__ import annotations

import structlog
from typing import Any

from talking_parrot.alignment.backend import AlignmentBackend
from talking_parrot.alignment.ctc import ctc_align
from talking_parrot.models.context import AlignmentGranularity
from talking_parrot.models.transcription import AlignedToken

logger = structlog.get_logger(__name__)


# Frame rate of WAV2VEC2_ASR_BASE_960H emissions at 16 kHz input
# (sample_rate / convolutional_stride = 16000 / 320 = 50 Hz).
_FRAME_RATE_HZ: float = 50.0
# WhisperX zero-pads segments shorter than 400 samples before the forward pass.
_MIN_SAMPLES: int = 400


class EnglishAlignmentBackend(AlignmentBackend):
    """torchaudio WAV2VEC2_ASR_BASE_960H word-level English aligner."""

    def __init__(self) -> None:
        """Defer all heavy work to the first ``align()`` call."""
        self._loaded: bool = False
        self._torch: Any = None
        self._device: Any = None
        self._model: Any = None
        self._labels: tuple[str, ...] | None = None
        self._dictionary: dict[str, int] | None = None
        self._blank_id: int = 0

    @property
    def language(self) -> str:
        """Return ``"en"`` — the ISO language code this backend serves."""
        return "en"

    @property
    def granularity(self) -> AlignmentGranularity:
        """Return :pyattr:`AlignmentGranularity.WORD`."""
        return AlignmentGranularity.WORD

    def align(
        self, audio_data: bytes, sample_rate: int, transcript: str
    ) -> list[AlignedToken]:
        """Force-align ``transcript`` to ``audio_data`` and return word-level tokens.

        Args:
            audio_data: 16-bit signed little-endian PCM bytes (mono).
            sample_rate: Sample rate in Hz (typically 16000).
            transcript: English text to align.

        Returns:
            One :class:`AlignedToken` per word in the transcript, with
            chunk-relative timestamps.

        Raises:
            ImportError: If ``torch`` or ``torchaudio`` is not installed.
        """
        self._ensure_loaded()
        assert self._dictionary is not None  # for type-checkers

        transcript_tokens = self._prepare_tokens(transcript)
        audio_tensor = self._decode(audio_data)

        logger.info(
            "calling torchaudio model forward",
            num_samples=int(audio_tensor.shape[-1]),
        )
        emissions, _ = self._model(audio_tensor)
        assert hasattr(emissions, "shape"), (
            "torchaudio model returned an object without .shape — API may have changed"
        )
        emissions = self._torch.log_softmax(emissions, dim=-1)
        logger.info(
            "torchaudio model forward returned",
            emissions_shape=tuple(emissions.shape),
        )

        char_tokens = ctc_align(
            emissions[0],
            self._dictionary,
            transcript_tokens,
            self._blank_id,
            frame_rate_hz=_FRAME_RATE_HZ,
            segment_offset_ms=0,
        )
        return self._group_words(char_tokens)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Lazy-import torch + torchaudio and load the WAV2VEC2 bundle once."""
        if self._loaded:
            return

        try:
            import torch  # noqa: WPS433 (lazy import is intentional)
            import torchaudio  # noqa: WPS433
        except ModuleNotFoundError as exc:
            raise ImportError(
                "EnglishAlignmentBackend requires torch and torchaudio. "
                "Install with: uv add 'talking-parrot[align]'"
            ) from exc

        device_name = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(
            "calling torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H.get_model",
            device=device_name,
        )
        bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
        model = bundle.get_model().to(device_name)
        labels = bundle.get_labels()
        assert isinstance(labels, (tuple, list)), (
            f"torchaudio bundle.get_labels() returned {type(labels)!r}, "
            "expected tuple or list — API may have changed"
        )
        logger.debug(
            "torchaudio bundle loaded",
            num_labels=len(labels),
        )

        self._torch = torch
        self._device = device_name
        self._model = model
        self._labels = tuple(labels)
        self._dictionary = {label.lower(): idx for idx, label in enumerate(labels)}
        self._blank_id = self._dictionary.get("[pad]", self._dictionary.get("<pad>", 0))
        self._loaded = True

    def _prepare_tokens(self, transcript: str) -> list[str]:
        """Lower-case ``transcript``, replace spaces with ``"|"``, return char list."""
        transformed = transcript.lower().replace(" ", "|")
        return list(transformed)

    def _decode(self, audio_data: bytes) -> Any:
        """Decode int16 PCM bytes into a normalised ``[1, N]`` float32 tensor."""
        # Lazy-imported numpy (part of the ``align`` extra).
        import numpy as np

        logger.debug(
            "calling np.frombuffer for English alignment audio decode",
            num_bytes=len(audio_data),
        )
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.shape[0] < _MIN_SAMPLES:
            pad = np.zeros(_MIN_SAMPLES - samples.shape[0], dtype=np.float32)
            samples = np.concatenate([samples, pad])
        tensor = self._torch.from_numpy(samples).reshape(1, -1).to(self._device)
        return tensor

    def _group_words(self, char_tokens: list[AlignedToken]) -> list[AlignedToken]:
        """Group consecutive non-``"|"`` characters into word-level AlignedTokens.

        - The word's ``word`` is the concatenation of the grouped characters.
        - The word's ``start_ms`` is the first character's ``start_ms``.
        - The word's ``end_ms`` is the last character's ``end_ms``.
        - The word's ``score`` is the arithmetic mean of the character scores.
        - ``"|"`` tokens are discarded; an empty pending buffer at flush
          MUST NOT emit.
        """
        out: list[AlignedToken] = []
        buf: list[AlignedToken] = []

        def _flush() -> None:
            """Emit the pending word if non-empty, then clear ``buf``."""
            if not buf:
                return
            scores = [t.score for t in buf]
            out.append(
                AlignedToken(
                    word="".join(t.word for t in buf),
                    start_ms=buf[0].start_ms,
                    end_ms=buf[-1].end_ms,
                    score=sum(scores) / len(scores),
                )
            )
            buf.clear()

        for tok in char_tokens:
            if tok.word == "|":
                _flush()
            else:
                buf.append(tok)
        _flush()
        return out
