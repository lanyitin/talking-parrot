import dataclasses
from pathlib import Path

import pytest

from talking_parrot.models.media import MediaInfo
from talking_parrot.models.vad import RawVadFrame, VadSegment
from talking_parrot.models.chunk import Chunk
from talking_parrot.models.subtitle import Subtitle


class TestChunkFields:
    def test_chunk_field_set_matches_spec(self):
        field_names = {f.name for f in dataclasses.fields(Chunk)}
        assert field_names == {"index", "start_ms", "end_ms", "source_segments"}

    def test_chunk_holds_no_audio_bytes(self):
        for f in dataclasses.fields(Chunk):
            assert f.type not in (bytes, bytearray), f"Field {f.name} must not be bytes"

    def test_chunk_is_frozen(self):
        seg = VadSegment(
            start_ms=0,
            end_ms=1000,
            ten_vad_prob=0.9,
            silero_vad_prob=0.8,
            composite_score=0.85,
        )
        chunk = Chunk(index=0, start_ms=0, end_ms=1000, source_segments=[seg])
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            chunk.index = 1  # type: ignore


class TestMediaInfo:
    def test_media_info_is_frozen(self):
        info = MediaInfo(path=Path("/tmp/test.mp4"), duration_ms=60000, sha256="abc")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            info.path = "/other"  # type: ignore


class TestVadSegment:
    def test_vad_segment_has_new_probability_fields(self):
        """VadSegment has ten_vad_prob, silero_vad_prob, composite_score instead of confidence."""
        seg = VadSegment(
            start_ms=0,
            end_ms=500,
            ten_vad_prob=0.9,
            silero_vad_prob=0.8,
            composite_score=0.85,
        )
        assert seg.ten_vad_prob == 0.9
        assert seg.silero_vad_prob == 0.8
        assert seg.composite_score == 0.85

    def test_vad_segment_is_frozen(self):
        """VadSegment is immutable after construction."""
        seg = VadSegment(
            start_ms=0,
            end_ms=500,
            ten_vad_prob=0.9,
            silero_vad_prob=0.8,
            composite_score=0.85,
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            seg.start_ms = 100  # type: ignore

    def test_vad_segment_has_no_confidence_field(self):
        """VadSegment no longer has a confidence field."""
        field_names = {f.name for f in dataclasses.fields(VadSegment)}
        assert "confidence" not in field_names
        assert "ten_vad_prob" in field_names
        assert "silero_vad_prob" in field_names
        assert "composite_score" in field_names


class TestRawVadFrame:
    def test_raw_vad_frame_construction(self):
        """RawVadFrame can be constructed with valid time_ms and prob."""
        frame = RawVadFrame(time_ms=0, prob=0.0)
        assert frame.time_ms == 0
        assert frame.prob == 0.0

        frame2 = RawVadFrame(time_ms=160, prob=0.95)
        assert frame2.time_ms == 160
        assert frame2.prob == 0.95

        frame3 = RawVadFrame(time_ms=320, prob=1.0)
        assert frame3.time_ms == 320
        assert frame3.prob == 1.0

    def test_raw_vad_frame_is_frozen(self):
        """RawVadFrame cannot be mutated after construction."""
        frame = RawVadFrame(time_ms=0, prob=0.5)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            frame.prob = 0.9  # type: ignore


class TestSubtitle:
    def test_subtitle_is_frozen(self):
        sub = Subtitle(index=0, start_ms=0, end_ms=1000, text="Hello")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            sub.text = "World"  # type: ignore
