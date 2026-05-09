"""Tests for the ``backend`` tag on :class:`RawVadFrame`.

These tests pin down the requirement
``RawVadFrame is an immutable value object`` from the
``vad-backend`` capability spec: every frame carries a non-empty
``backend: str`` identifier.
"""

from __future__ import annotations

import pytest

from talking_parrot.models.vad import RawVadFrame


def test_raw_vad_frame_requires_backend() -> None:
    """Constructing without ``backend`` raises ``TypeError`` (dataclass default)."""
    with pytest.raises(TypeError):
        RawVadFrame(time_ms=0, prob=0.5)  # type: ignore[call-arg]


def test_raw_vad_frame_rejects_empty_backend() -> None:
    """Constructing with ``backend=""`` raises ``ValueError`` from ``__post_init__``."""
    with pytest.raises(ValueError):
        RawVadFrame(time_ms=0, prob=0.5, backend="")


def test_raw_vad_frame_accepts_concrete_backend_tags() -> None:
    """The four reserved backend tags MUST all construct successfully."""
    for backend in ("silero_vad", "ten_vad", "composite", "unknown"):
        frame = RawVadFrame(time_ms=0, prob=0.5, backend=backend)
        assert frame.backend == backend
