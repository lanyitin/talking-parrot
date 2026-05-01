import pytest

from talking_parrot.stages.base import PipelineStage
from talking_parrot.models.context import PipelineContext
from talking_parrot.models.media import MediaInfo
from talking_parrot.config.models import PipelineConfig


def _make_ctx():
    cfg = PipelineConfig(
        transcribing=[{"condition": "true", "backend": "faster-whisper"}]
    )
    info = MediaInfo(path="/tmp/t.mp4", duration_ms=1000, sha256="abc")
    return PipelineContext(config=cfg, media_info=info)


class _NoopStage(PipelineStage):
    @property
    def name(self) -> str:
        return "noop"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        return ctx


class TestPipelineStageInterface:
    def test_name_property_accessible(self):
        stage = _NoopStage()
        assert stage.name == "noop"

    def test_process_returns_context(self):
        stage = _NoopStage()
        ctx = _make_ctx()
        result = stage.process(ctx)
        assert result is ctx

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            PipelineStage()  # type: ignore
