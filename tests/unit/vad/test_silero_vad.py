"""Unit tests for SileroVADBackend.

Tests mock ``silero_vad.load_silero_vad`` to avoid a real dependency on
the Silero VAD package at test time. The implementation under test is at
``talking_parrot.vad.silero_vad``.
"""

from __future__ import annotations

import struct
from math import floor
from unittest.mock import MagicMock, patch

import pytest

from talking_parrot.vad.silero_vad import SileroVADBackend


def _make_pcm_bytes(num_samples: int) -> bytes:
    """Create a PCM byte buffer of *num_samples* 16-bit signed samples (all zeros)."""
    return struct.pack(f"<{num_samples}h", *([0] * num_samples))


def _make_mock_load_silero_vad(probability: float = 0.72) -> MagicMock:
    """Return a mock ``load_silero_vad`` that yields a model returning *probability*."""
    prob_tensor = MagicMock()
    prob_tensor.item.return_value = probability

    model_mock = MagicMock(return_value=prob_tensor)
    load_fn_mock = MagicMock(return_value=model_mock)
    return load_fn_mock


class TestSileroVADBackendName:
    def test_name_returns_silero_vad(self):
        """SileroVADBackend.name returns the string 'silero_vad'."""
        backend = SileroVADBackend()
        assert backend.name == "silero_vad"


class TestSileroVADBackendFrameCount:
    """Frame count equals floor(N / chunk_size) for various audio lengths."""

    @pytest.mark.parametrize(
        "audio_samples, chunk_size, expected_frames",
        [
            (512, 512, 1),
            (1024, 512, 2),
            (1500, 512, 2),
            (16000, 512, 31),
        ],
    )
    def test_frame_count_matches_spec_examples(
        self, audio_samples: int, chunk_size: int, expected_frames: int
    ) -> None:
        """frame count equals floor(N / chunk_size) for common audio lengths."""
        load_fn = _make_mock_load_silero_vad(0.5)
        with patch("talking_parrot.vad.silero_vad.load_silero_vad", load_fn):
            backend = SileroVADBackend(chunk_size=chunk_size)
            pcm = _make_pcm_bytes(audio_samples)
            frames = backend.analyze(pcm, sample_rate=16000)

        assert len(frames) == expected_frames, (
            f"Expected {expected_frames} frames for {audio_samples} samples "
            f"with chunk_size={chunk_size}, got {len(frames)}"
        )
        assert len(frames) == floor(audio_samples / chunk_size)


class TestSileroVADBackendTimestamps:
    """Frame time_ms values match chunk position."""

    @pytest.mark.parametrize(
        "frame_index, chunk_size, sample_rate, expected_time_ms",
        [
            (0, 512, 16000, 0),
            (1, 512, 16000, 32),
            (2, 512, 16000, 64),
            (3, 512, 16000, 96),
        ],
    )
    def test_time_ms_for_first_four_frames(
        self,
        frame_index: int,
        chunk_size: int,
        sample_rate: int,
        expected_time_ms: int,
    ) -> None:
        """Frame at index i has time_ms = i * chunk_size / sample_rate * 1000."""
        num_samples = (frame_index + 1) * chunk_size
        load_fn = _make_mock_load_silero_vad(0.5)
        with patch("talking_parrot.vad.silero_vad.load_silero_vad", load_fn):
            backend = SileroVADBackend(chunk_size=chunk_size)
            pcm = _make_pcm_bytes(num_samples)
            frames = backend.analyze(pcm, sample_rate=sample_rate)

        assert frames[frame_index].time_ms == expected_time_ms


class TestSileroVADBackendProbability:
    def test_prob_reflects_silero_model_output(self) -> None:
        """RawVadFrame.prob equals model(chunk, sr).item() from mock."""
        expected_prob = 0.72
        load_fn = _make_mock_load_silero_vad(expected_prob)
        with patch("talking_parrot.vad.silero_vad.load_silero_vad", load_fn):
            backend = SileroVADBackend(chunk_size=512)
            pcm = _make_pcm_bytes(512)  # exactly one frame
            frames = backend.analyze(pcm, sample_rate=16000)

        assert len(frames) == 1
        assert frames[0].prob == expected_prob


class TestSileroVADBackendLazyInit:
    def test_load_silero_vad_not_called_before_analyze(self) -> None:
        """load_silero_vad is NOT called at construction time (lazy init)."""
        load_fn = _make_mock_load_silero_vad()
        with patch("talking_parrot.vad.silero_vad.load_silero_vad", load_fn):
            SileroVADBackend()
            assert load_fn.call_count == 0

    def test_load_silero_vad_called_on_first_analyze(self) -> None:
        """load_silero_vad is called on the first analyze() call."""
        load_fn = _make_mock_load_silero_vad()
        with patch("talking_parrot.vad.silero_vad.load_silero_vad", load_fn):
            backend = SileroVADBackend(chunk_size=512)
            backend.analyze(_make_pcm_bytes(512), 16000)
            assert load_fn.call_count == 1

    def test_load_silero_vad_not_called_again_on_second_analyze(self) -> None:
        """load_silero_vad is NOT called again on the second analyze() call (cached)."""
        load_fn = _make_mock_load_silero_vad()
        with patch("talking_parrot.vad.silero_vad.load_silero_vad", load_fn):
            backend = SileroVADBackend(chunk_size=512)
            backend.analyze(_make_pcm_bytes(512), 16000)
            backend.analyze(_make_pcm_bytes(512), 16000)
            assert load_fn.call_count == 1
