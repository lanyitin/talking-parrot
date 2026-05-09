"""Unit tests for VADBackend abstract interface and RawVadFrame model."""

import dataclasses
import pytest

from talking_parrot.models.vad import RawVadFrame
from talking_parrot.vad.backend import VADBackend


class TestVADBackendAbstract:
    def test_vad_backend_cannot_be_instantiated_directly(self):
        """VADBackend is abstract and cannot be instantiated without implementing abstract members."""
        with pytest.raises(TypeError):
            VADBackend()  # type: ignore

    def test_concrete_subclass_satisfying_interface_can_be_instantiated(self):
        """A concrete subclass that implements name and analyze can be instantiated."""

        class ConcreteBackend(VADBackend):
            @property
            def name(self) -> str:
                return "test_backend"

            def analyze(self, audio_data: bytes, sample_rate: int) -> list[RawVadFrame]:
                return [RawVadFrame(time_ms=0, prob=0.5, backend="test_backend")]

        backend = ConcreteBackend()
        assert backend.name == "test_backend"
        frames = backend.analyze(b"\x00" * 512, 16000)
        assert isinstance(frames, list)
        assert len(frames) == 1

    def test_partial_subclass_without_analyze_cannot_be_instantiated(self):
        """A subclass that only implements name but not analyze cannot be instantiated."""

        class PartialBackend(VADBackend):
            @property
            def name(self) -> str:
                return "partial"

        with pytest.raises(TypeError):
            PartialBackend()  # type: ignore


class TestRawVadFrameImmutability:
    def test_raw_vad_frame_is_frozen(self):
        """RawVadFrame is frozen — field assignment raises FrozenInstanceError."""
        frame = RawVadFrame(time_ms=0, prob=0.5, backend="silero_vad")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            frame.time_ms = 10  # type: ignore

    def test_raw_vad_frame_prob_zero_is_valid(self):
        """prob=0.0 is within the valid range [0.0, 1.0]."""
        frame = RawVadFrame(time_ms=0, prob=0.0, backend="silero_vad")
        assert frame.prob == 0.0

    def test_raw_vad_frame_prob_one_is_valid(self):
        """prob=1.0 is within the valid range [0.0, 1.0]."""
        frame = RawVadFrame(time_ms=160, prob=1.0, backend="silero_vad")
        assert frame.prob == 1.0

    def test_raw_vad_frame_prob_mid_range_is_valid(self):
        """prob=0.95 is within the valid range [0.0, 1.0]."""
        frame = RawVadFrame(time_ms=320, prob=0.95, backend="silero_vad")
        assert frame.prob == 0.95
