import dataclasses
import pytest

from talking_parrot.pipeline.orchestrator import PipelineOrchestrator
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


class _MarkerStage(PipelineStage):
    """Appends its name to vad_segments (used as call trace)."""

    def __init__(self, marker: str):
        self._marker = marker

    @property
    def name(self) -> str:
        return self._marker

    def process(self, ctx: PipelineContext) -> PipelineContext:
        return dataclasses.replace(ctx, vad_segments=ctx.vad_segments + [self._marker])


class _ExplodingStage(PipelineStage):
    @property
    def name(self) -> str:
        return "boom"

    def process(self, ctx: PipelineContext) -> PipelineContext:
        raise RuntimeError("kaboom")


class TestPipelineOrchestratorOrdering:
    def test_stages_run_in_order(self):
        stages = [_MarkerStage("A"), _MarkerStage("B"), _MarkerStage("C")]
        orchestrator = PipelineOrchestrator(stages)
        ctx = orchestrator.run(_make_ctx())
        assert ctx.vad_segments == ["A", "B", "C"]

    def test_empty_stages_returns_input_context(self):
        orchestrator = PipelineOrchestrator([])
        ctx0 = _make_ctx()
        result = orchestrator.run(ctx0)
        assert result is ctx0

    def test_exception_aborts_pipeline(self):
        stages = [_MarkerStage("A"), _ExplodingStage(), _MarkerStage("C")]
        orchestrator = PipelineOrchestrator(stages)
        with pytest.raises(RuntimeError, match="kaboom"):
            orchestrator.run(_make_ctx())

    def test_no_forbidden_imports(self):
        import inspect
        import talking_parrot.pipeline.orchestrator as mod

        src = inspect.getsource(mod)
        forbidden = [
            "talking_parrot.vad",
            "talking_parrot.transcription",
            "talking_parrot.alignment",
            "talking_parrot.post_processing",
            "talking_parrot.export",
            "talking_parrot.expression",
            "talking_parrot.io",
        ]
        for imp in forbidden:
            assert imp not in src, f"Orchestrator must not import {imp!r}"
