import pytest

from talking_parrot.io.audio_reader import AudioReader
from talking_parrot.io.audio_decoder import FfmpegAudioReader


class FakeAudioReader(AudioReader):
    """In-memory test double."""

    def __init__(self, duration_ms: int = 60_000, sample_rate: int = 16_000):
        self._duration_ms = duration_ms
        self._sample_rate = sample_rate

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def read(self, start_ms: int, end_ms: int) -> bytes:
        if start_ms < 0 or start_ms >= end_ms or end_ms > self._duration_ms:
            raise ValueError(f"Invalid interval [{start_ms}, {end_ms}]")
        samples = int((end_ms - start_ms) / 1000 * self._sample_rate)
        return b"\x00" * samples * 2  # 16-bit PCM

    @property
    def duration_ms(self) -> int:
        return self._duration_ms


class TestAudioReaderInterface:
    def test_sample_rate_readable(self):
        reader = FakeAudioReader(sample_rate=16_000)
        assert reader.sample_rate == 16_000

    def test_read_returns_bytes(self):
        reader = FakeAudioReader(duration_ms=60_000)
        data = reader.read(1000, 2000)
        assert isinstance(data, bytes)

    def test_out_of_range_raises_value_error(self):
        reader = FakeAudioReader(duration_ms=60_000)
        with pytest.raises(ValueError):
            reader.read(0, 70_000)  # end_ms > duration_ms

    def test_negative_start_raises(self):
        reader = FakeAudioReader(duration_ms=60_000)
        with pytest.raises(ValueError):
            reader.read(-1, 1000)

    def test_start_ge_end_raises(self):
        reader = FakeAudioReader(duration_ms=60_000)
        with pytest.raises(ValueError):
            reader.read(1000, 1000)


class TestFfmpegAudioReaderConfig:
    def test_default_cache_size_is_4(self, monkeypatch):
        monkeypatch.delenv("AUDIO_CACHE_SIZE", raising=False)
        # Importing the class should not fail; cache_size property accessible

        assert FfmpegAudioReader._default_cache_size() == 4

    def test_env_override_cache_size(self, monkeypatch):
        monkeypatch.setenv("AUDIO_CACHE_SIZE", "8")
        from talking_parrot.io import audio_decoder
        import importlib

        importlib.reload(audio_decoder)
        assert audio_decoder.FfmpegAudioReader._default_cache_size() == 8
