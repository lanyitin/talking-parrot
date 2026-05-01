import dataclasses
import pytest

from talking_parrot.models.media import MediaInfo
from talking_parrot.models.vad import VadSegment
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
        seg = VadSegment(start_ms=0, end_ms=1000, confidence=0.9)
        chunk = Chunk(index=0, start_ms=0, end_ms=1000, source_segments=[seg])
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            chunk.index = 1  # type: ignore


class TestMediaInfo:
    def test_media_info_is_frozen(self):
        info = MediaInfo(path="/tmp/test.mp4", duration_ms=60000, sha256="abc")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            info.path = "/other"  # type: ignore


class TestVadSegment:
    def test_vad_segment_is_frozen(self):
        seg = VadSegment(start_ms=0, end_ms=500, confidence=0.95)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            seg.start_ms = 100  # type: ignore


class TestSubtitle:
    def test_subtitle_is_frozen(self):
        sub = Subtitle(index=0, start_ms=0, end_ms=1000, text="Hello")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            sub.text = "World"  # type: ignore
