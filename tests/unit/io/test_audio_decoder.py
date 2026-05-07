"""Unit tests for ``FfmpegAudioReader`` (audio_decoder module)."""

from __future__ import annotations

from unittest.mock import patch

from talking_parrot.io.audio_decoder import FfmpegAudioReader


class TestDurationMsProperty:
    """``duration_ms`` exposes the value probed via ``ffmpeg.probe`` at construction."""

    def test_returns_milliseconds_from_probe(self):
        fake_probe = {"format": {"duration": "12.345"}}
        with patch(
            "talking_parrot.io.audio_decoder.ffmpeg.probe", return_value=fake_probe
        ):
            reader = FfmpegAudioReader("/tmp/anything.mp3")
        assert reader.duration_ms == 12345

    def test_truncates_sub_millisecond(self):
        fake_probe = {"format": {"duration": "0.5009"}}
        with patch(
            "talking_parrot.io.audio_decoder.ffmpeg.probe", return_value=fake_probe
        ):
            reader = FfmpegAudioReader("/tmp/anything.mp3")
        assert reader.duration_ms == 500
