"""Tests for :class:`PostProcessingStage` (Stage 5).

Spec: ``post-processing-stage``. Design: D1, D2, D7, D9, D10.
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

from talking_parrot.config.models import (
    PipelineConfig,
    PostProcessingConfig,
    TranscribingStep,
)
from talking_parrot.models.context import (
    AlignmentGranularity,
    AlignmentStatus,
    PipelineContext,
)
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.post_processing.base import SubtitleProcessor
from talking_parrot.post_processing.factory import (
    GranularityAwareProcessorFactory,
)
from talking_parrot.stages.post_processing_stage import PostProcessingStage


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _metrics() -> TranscriptionMetrics:
    """Build default metrics."""
    return TranscriptionMetrics(
        avg_logprob=0.0,
        compression_ratio=1.0,
        no_speech_prob=0.0,
        repetition_ratio=0.0,
    )


def _tr(start_ms: int, end_ms: int, text: str) -> TranscriptionResult:
    """Build a TranscriptionResult."""
    return TranscriptionResult(
        chunk_index=0,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        language="en",
        model_used="test",
        metrics=_metrics(),
    )


def _config(post: PostProcessingConfig | None) -> PipelineConfig:
    """Build a PipelineConfig with the given post-processing config."""
    return PipelineConfig(
        expected_language="en",
        transcribing=[TranscribingStep(condition="true", backend="whisper")],
        post_processing=post,
    )


def _media() -> MediaInfo:
    """Build a placeholder MediaInfo."""
    return MediaInfo(path=Path("x"), duration_ms=10_000, sha256="0" * 64)


def _ctx(
    *,
    config: PipelineConfig,
    transcription_results: list[TranscriptionResult],
    alignment_status: AlignmentStatus = AlignmentStatus.DISABLED,
    alignment_granularity: AlignmentGranularity | None = None,
) -> PipelineContext:
    """Build a PipelineContext for tests."""
    return PipelineContext(
        config=config,
        media_info=_media(),
        transcription_results=transcription_results,
        alignment_status=alignment_status,
        alignment_granularity=alignment_granularity,
    )


class _RecordingProcessor(SubtitleProcessor):
    """Processor that records its inputs and returns a tagged copy."""

    def __init__(self, tag: str) -> None:
        """Store the tag and call log."""
        self.tag = tag
        self.calls: list[list[Subtitle]] = []

    def process(
        self, subtitles: list[Subtitle], config: PostProcessingConfig
    ) -> list[Subtitle]:
        """Record input and return a list with text suffixed by ``-tag``."""
        self.calls.append(list(subtitles))
        return [dataclasses.replace(s, text=f"{s.text}-{self.tag}") for s in subtitles]


class _RecordingFactory(GranularityAwareProcessorFactory):
    """Factory that records call args and returns the configured processors."""

    def __init__(self, processors: list[SubtitleProcessor]) -> None:
        """Store the processors and call log."""
        self._processors = processors
        self.calls: list[
            tuple[AlignmentGranularity | None, list[TranscriptionResult]]
        ] = []

    def create(
        self,
        granularity: AlignmentGranularity | None,
        ctx: PipelineContext,
    ) -> list[SubtitleProcessor]:
        """Record the call and return the configured processors."""
        self.calls.append((granularity, list(ctx.transcription_results)))
        return list(self._processors)


class _NoOpProcessor(SubtitleProcessor):
    """Identity processor used when factory output is irrelevant."""

    def process(
        self, subtitles: list[Subtitle], config: PostProcessingConfig
    ) -> list[Subtitle]:
        """Return the input list unchanged."""
        return list(subtitles)


class _ChangingIndexProcessor(SubtitleProcessor):
    """Processor that returns subtitles with arbitrary ``index`` values."""

    def process(
        self, subtitles: list[Subtitle], config: PostProcessingConfig
    ) -> list[Subtitle]:
        """Return the same cues but with bizarre indices."""
        return [dataclasses.replace(s, index=99 - i) for i, s in enumerate(subtitles)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNameAndConstruction:
    """Spec: name and constructor injection."""

    def test_name_property(self):
        """``name`` MUST equal ``"post_processing"``."""
        stage = PostProcessingStage(processor_factory=_RecordingFactory([]))
        assert stage.name == "post_processing"

    def test_constructor_accepts_factory(self):
        """The factory is injected via constructor."""
        factory = _RecordingFactory([])
        stage = PostProcessingStage(processor_factory=factory)
        assert stage._processor_factory is factory


class TestSeedSubtitles:
    """Spec D1: one seed subtitle per TranscriptionResult."""

    def test_seed_built_via_disabled_path(self):
        """Disabled-path returns seed cues — verifies seed shape."""
        ctx = _ctx(
            config=_config(None),
            transcription_results=[
                _tr(0, 1000, "a"),
                _tr(1500, 3000, "b"),
            ],
        )
        stage = PostProcessingStage(processor_factory=_RecordingFactory([]))
        out = stage.process(ctx)
        assert out.subtitles == [
            Subtitle(index=1, start_ms=0, end_ms=1000, text="a"),
            Subtitle(index=2, start_ms=1500, end_ms=3000, text="b"),
        ]

    def test_input_context_not_mutated(self):
        """Returned context is a different object; input is unchanged."""
        ctx_in = _ctx(
            config=_config(None),
            transcription_results=[_tr(0, 1000, "a")],
        )
        original_subs = ctx_in.subtitles
        stage = PostProcessingStage(processor_factory=_RecordingFactory([]))
        ctx_out = stage.process(ctx_in)
        assert ctx_out is not ctx_in
        assert ctx_in.subtitles is original_subs
        assert ctx_in.subtitles == []


class TestDisabledPath:
    """Spec D9: disabled-path semantics."""

    def test_post_processing_none_skips_factory(self):
        """``config.post_processing is None`` returns seed and skips factory."""
        factory = _RecordingFactory([_NoOpProcessor()])
        ctx = _ctx(
            config=_config(None),
            transcription_results=[_tr(0, 1000, "a"), _tr(1000, 2000, "b")],
        )
        out = PostProcessingStage(processor_factory=factory).process(ctx)
        assert len(out.subtitles) == 2
        assert factory.calls == []

    def test_disabled_flag_skips_factory(self):
        """``enabled=False`` returns seed and skips factory."""
        factory = _RecordingFactory([_NoOpProcessor()])
        cfg = PostProcessingConfig(enabled=False)
        ctx = _ctx(
            config=_config(cfg),
            transcription_results=[
                _tr(0, 1000, "a"),
                _tr(1000, 2000, "b"),
                _tr(2000, 3000, "c"),
            ],
        )
        out = PostProcessingStage(processor_factory=factory).process(ctx)
        assert len(out.subtitles) == 3
        assert [s.index for s in out.subtitles] == [1, 2, 3]
        assert factory.calls == []


class TestFactoryGroupSelection:
    """Spec D10 / SUCCESS / DISABLED / FAILED resolution."""

    def test_success_forwards_granularity(self):
        """SUCCESS path passes ``ctx.alignment_granularity`` through."""
        factory = _RecordingFactory([_NoOpProcessor()])
        ctx = _ctx(
            config=_config(PostProcessingConfig()),
            transcription_results=[_tr(0, 1000, "a")],
            alignment_status=AlignmentStatus.SUCCESS,
            alignment_granularity=AlignmentGranularity.WORD,
        )
        PostProcessingStage(processor_factory=factory).process(ctx)
        assert len(factory.calls) == 1
        assert factory.calls[0][0] is AlignmentGranularity.WORD

    def test_failed_warns_and_uses_none(self, caplog):
        """FAILED logs WARNING and forces ``granularity=None``."""
        factory = _RecordingFactory([_NoOpProcessor()])
        ctx = _ctx(
            config=_config(PostProcessingConfig()),
            transcription_results=[_tr(0, 1000, "a")],
            alignment_status=AlignmentStatus.FAILED,
            alignment_granularity=None,
        )
        with caplog.at_level(logging.WARNING, logger="talking_parrot.stages"):
            PostProcessingStage(processor_factory=factory).process(ctx)
        assert len(factory.calls) == 1
        assert factory.calls[0][0] is None
        assert any(
            r.levelno == logging.WARNING and "alignment FAILED" in r.getMessage()
            for r in caplog.records
        )

    def test_disabled_silent_fallback(self, caplog):
        """DISABLED uses ``None`` and emits no WARNING."""
        factory = _RecordingFactory([_NoOpProcessor()])
        ctx = _ctx(
            config=_config(PostProcessingConfig()),
            transcription_results=[_tr(0, 1000, "a")],
            alignment_status=AlignmentStatus.DISABLED,
            alignment_granularity=None,
        )
        with caplog.at_level(logging.WARNING):
            PostProcessingStage(processor_factory=factory).process(ctx)
        assert len(factory.calls) == 1
        assert factory.calls[0][0] is None
        # No WARNING about alignment FAILED.
        assert not any(
            r.levelno == logging.WARNING and "alignment FAILED" in r.getMessage()
            for r in caplog.records
        )


class TestProcessorPipeline:
    """Spec: processors run in factory-returned order; final indices renumbered."""

    def test_processors_run_in_order(self):
        """ProcA's output is ProcB's input."""
        proc_a = _RecordingProcessor(tag="A")
        proc_b = _RecordingProcessor(tag="B")
        factory = _RecordingFactory([proc_a, proc_b])
        ctx = _ctx(
            config=_config(PostProcessingConfig()),
            transcription_results=[_tr(0, 1000, "x")],
            alignment_status=AlignmentStatus.DISABLED,
        )
        out = PostProcessingStage(processor_factory=factory).process(ctx)

        # ProcA called first with seed; ProcB called with ProcA's output.
        assert len(proc_a.calls) == 1
        assert len(proc_b.calls) == 1
        assert proc_a.calls[0][0].text == "x"
        assert proc_b.calls[0][0].text == "x-A"
        assert out.subtitles[0].text == "x-A-B"

    def test_final_indices_renumbered(self):
        """Final output is renumbered to ``1..N``."""
        factory = _RecordingFactory([_ChangingIndexProcessor()])
        ctx = _ctx(
            config=_config(PostProcessingConfig()),
            transcription_results=[
                _tr(0, 1000, "a"),
                _tr(1000, 2000, "b"),
                _tr(2000, 3000, "c"),
                _tr(3000, 4000, "d"),
            ],
            alignment_status=AlignmentStatus.DISABLED,
        )
        out = PostProcessingStage(processor_factory=factory).process(ctx)
        assert [s.index for s in out.subtitles] == [1, 2, 3, 4]


class TestEmptyTranscriptionResults:
    """Spec: empty input yields empty subtitles."""

    def test_empty_input_returns_empty_subtitles(self):
        """``transcription_results == []`` → ``subtitles == []`` regardless of config."""
        factory = _RecordingFactory([_NoOpProcessor()])
        ctx = _ctx(
            config=_config(PostProcessingConfig()),
            transcription_results=[],
            alignment_status=AlignmentStatus.SUCCESS,
            alignment_granularity=AlignmentGranularity.WORD,
        )
        out = PostProcessingStage(processor_factory=factory).process(ctx)
        assert out.subtitles == []

    def test_empty_input_disabled_path(self):
        """Empty input + disabled config still returns empty."""
        factory = _RecordingFactory([_NoOpProcessor()])
        ctx = _ctx(config=_config(None), transcription_results=[])
        out = PostProcessingStage(processor_factory=factory).process(ctx)
        assert out.subtitles == []
        assert factory.calls == []
