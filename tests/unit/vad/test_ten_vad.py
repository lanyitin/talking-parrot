"""Unit tests for TenVADBackend.

Tests mock ``ten_vad.TenVad`` to avoid a real dependency on the TEN VAD package
at test time. The implementation under test is at
``talking_parrot.vad.ten_vad``.
"""

from __future__ import annotations

import struct
from math import floor
from unittest.mock import MagicMock, patch

import pytest

from talking_parrot.vad.ten_vad import TenVADBackend


def _make_pcm_bytes(num_samples: int) -> bytes:
    """Create a PCM byte buffer of *num_samples* 16-bit signed samples (all zeros)."""
    return struct.pack(f"<{num_samples}h", *([0] * num_samples))


def _make_mock_ten_vad_cls(probability: float = 0.87) -> MagicMock:
    """Return a mock TenVad class whose ``process()`` returns (probability, 0)."""
    result_mock = MagicMock()
    result_mock.probability = probability

    instance_mock = MagicMock()
    instance_mock.process.return_value = result_mock

    cls_mock = MagicMock(return_value=instance_mock)
    return cls_mock


class TestTenVADBackendName:
    def test_name_returns_ten_vad(self):
        """TenVADBackend.name returns the string 'ten_vad'."""
        backend = TenVADBackend()
        assert backend.name == "ten_vad"


class TestTenVADBackendFrameCount:
    """Frame count equals floor(N / hop_size) for various audio lengths."""

    @pytest.mark.parametrize(
        "audio_samples, hop_size, expected_frames",
        [
            (256, 256, 1),
            (512, 256, 2),
            (1000, 256, 3),
            (8000, 256, 31),
        ],
    )
    def test_frame_count_matches_spec_examples(
        self, audio_samples: int, hop_size: int, expected_frames: int
    ) -> None:
        """frame count equals floor(N / hop_size) for common audio lengths."""
        mock_cls = _make_mock_ten_vad_cls(0.5)
        with patch("talking_parrot.vad.ten_vad.TenVad", mock_cls):
            backend = TenVADBackend(hop_size=hop_size)
            pcm = _make_pcm_bytes(audio_samples)
            frames = backend.analyze(pcm, sample_rate=16000)

        assert len(frames) == expected_frames, (
            f"Expected {expected_frames} frames for {audio_samples} samples "
            f"with hop_size={hop_size}, got {len(frames)}"
        )
        assert len(frames) == floor(audio_samples / hop_size)


class TestTenVADBackendTimestamps:
    """Frame time_ms values match chunk position."""

    @pytest.mark.parametrize(
        "frame_index, hop_size, sample_rate, expected_time_ms",
        [
            (0, 256, 16000, 0),
            (1, 256, 16000, 16),
            (2, 256, 16000, 32),
            (3, 256, 16000, 48),
        ],
    )
    def test_time_ms_for_first_four_frames(
        self,
        frame_index: int,
        hop_size: int,
        sample_rate: int,
        expected_time_ms: int,
    ) -> None:
        """Frame at index i has time_ms = i * hop_size / sample_rate * 1000."""
        num_samples = (frame_index + 1) * hop_size  # enough samples to reach this frame
        mock_cls = _make_mock_ten_vad_cls(0.5)
        with patch("talking_parrot.vad.ten_vad.TenVad", mock_cls):
            backend = TenVADBackend(hop_size=hop_size)
            pcm = _make_pcm_bytes(num_samples)
            frames = backend.analyze(pcm, sample_rate=sample_rate)

        assert frames[frame_index].time_ms == expected_time_ms


class TestTenVADBackendProbability:
    def test_prob_reflects_ten_vad_result_probability(self) -> None:
        """RawVadFrame.prob equals result.probability returned by TenVad.process()."""
        expected_prob = 0.87
        mock_cls = _make_mock_ten_vad_cls(expected_prob)
        with patch("talking_parrot.vad.ten_vad.TenVad", mock_cls):
            backend = TenVADBackend(hop_size=256)
            pcm = _make_pcm_bytes(256)  # exactly one frame
            frames = backend.analyze(pcm, sample_rate=16000)

        assert len(frames) == 1
        assert frames[0].prob == expected_prob


class TestTenVADBackendLazyInit:
    def test_ten_vad_not_instantiated_before_analyze(self) -> None:
        """TenVad instance is NOT created at construction time (lazy init)."""
        mock_cls = _make_mock_ten_vad_cls()
        with patch("talking_parrot.vad.ten_vad.TenVad", mock_cls):
            TenVADBackend()
            assert mock_cls.call_count == 0

    def test_ten_vad_instantiated_on_first_analyze(self) -> None:
        """TenVad instance IS created on the first analyze() call."""
        mock_cls = _make_mock_ten_vad_cls()
        with patch("talking_parrot.vad.ten_vad.TenVad", mock_cls):
            backend = TenVADBackend(hop_size=256, threshold=0.5)
            backend.analyze(_make_pcm_bytes(256), 16000)
            assert mock_cls.call_count == 1

    def test_ten_vad_not_reinstantiated_on_second_analyze(self) -> None:
        """TenVad instance is reused across multiple analyze() calls."""
        mock_cls = _make_mock_ten_vad_cls()
        with patch("talking_parrot.vad.ten_vad.TenVad", mock_cls):
            backend = TenVADBackend(hop_size=256)
            backend.analyze(_make_pcm_bytes(256), 16000)
            backend.analyze(_make_pcm_bytes(256), 16000)
            assert mock_cls.call_count == 1
