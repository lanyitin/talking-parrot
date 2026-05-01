"""Alignment subsystem for the talking_parrot pipeline.

This package implements forced-alignment of transcripts to audio using the
WhisperX-derived CTC kernel. It is split into:

- :mod:`backend` — the abstract :class:`AlignmentBackend` interface.
- :mod:`ctc` — the shared CTC forced-alignment kernel.
- :mod:`english_backend` — torchaudio WAV2VEC2 bundle backend (word-level).
- :mod:`japanese_backend` — HuggingFace Wav2Vec2ForCTC backend (character-level).
- :mod:`factory` — :class:`AlignmentBackendFactory` routing by language and
  granularity, with instance caching.

Heavy ML dependencies (`torch`, `torchaudio`, `transformers`, `numpy`) are
lazy-imported by individual backends so that constructing the package or the
pipeline does not require them. Install with ``uv add 'talking-parrot[align]'``.
"""

from talking_parrot.alignment.backend import AlignmentBackend

__all__ = ["AlignmentBackend"]
