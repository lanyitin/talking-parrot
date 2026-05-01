import dataclasses
import pytest

from talking_parrot.models.context import (
    PipelineContext,
    AlignmentStatus,
    AlignmentGranularity,
    GranularityPreference,
)


class TestAlignmentStatusEnum:
    def test_has_three_states(self):
        assert set(AlignmentStatus) == {
            AlignmentStatus.DISABLED,
            AlignmentStatus.SUCCESS,
            AlignmentStatus.FAILED,
        }


class TestAlignmentGranularityEnum:
    def test_has_word_and_character(self):
        assert set(AlignmentGranularity) == {
            AlignmentGranularity.WORD,
            AlignmentGranularity.CHARACTER,
        }

    def test_auto_not_present(self):
        names = {m.name for m in AlignmentGranularity}
        assert "AUTO" not in names


class TestGranularityPreferenceEnum:
    def test_has_word_character_auto(self):
        assert set(GranularityPreference) == {
            GranularityPreference.WORD,
            GranularityPreference.CHARACTER,
            GranularityPreference.AUTO,
        }


class TestPipelineContextDefaults:
    def _make_context(self):
        from talking_parrot.config.models import PipelineConfig
        from talking_parrot.models.media import MediaInfo

        cfg = PipelineConfig(
            transcribing=[{"condition": "true", "backend": "faster-whisper"}]
        )
        info = MediaInfo(path="/tmp/t.mp4", duration_ms=1000, sha256="abc")
        return PipelineContext(config=cfg, media_info=info)

    def test_list_fields_default_empty(self):
        ctx = self._make_context()
        assert ctx.vad_segments == []
        assert ctx.chunks == []
        assert ctx.transcription_results == []
        assert ctx.alignment_results == []
        assert ctx.subtitles == []

    def test_alignment_status_default_disabled(self):
        ctx = self._make_context()
        assert ctx.alignment_status == AlignmentStatus.DISABLED

    def test_alignment_granularity_default_none(self):
        ctx = self._make_context()
        assert ctx.alignment_granularity is None

    def test_context_is_frozen(self):
        ctx = self._make_context()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            ctx.vad_segments = []  # type: ignore
