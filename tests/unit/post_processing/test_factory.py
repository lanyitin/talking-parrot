"""Tests for ``GranularityAwareProcessorFactory`` and its default impl.

Spec: ``granularity-aware-processor-factory``. Design: D3, D7.
"""

from __future__ import annotations

import enum

import pytest

from talking_parrot.config.models import PipelineConfig
from talking_parrot.models.context import AlignmentGranularity, PipelineContext
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.transcription import (
    AlignedToken,
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.post_processing.character_boundary import (
    CharacterBoundaryMergeProcessor,
    CharacterBoundarySplitProcessor,
)
from talking_parrot.post_processing.factory import (
    DefaultGranularityAwareProcessorFactory,
    GranularityAwareProcessorFactory,
)
from talking_parrot.post_processing.time_based import (
    TimeBasedMergeProcessor,
    TimeBasedSplitProcessor,
)
from talking_parrot.post_processing.word_boundary import (
    WordBoundaryMergeProcessor,
    WordBoundarySplitProcessor,
)


def _metrics() -> TranscriptionMetrics:
    """Build default metrics for tests."""
    return TranscriptionMetrics(
        avg_logprob=0.0,
        compression_ratio=1.0,
        no_speech_prob=0.0,
        repetition_ratio=0.0,
    )


def _tr(
    chunk_index: int,
    start_ms: int,
    end_ms: int,
    text: str,
    aligned_tokens: list[AlignedToken] | None = None,
) -> TranscriptionResult:
    """Build a TranscriptionResult with default metrics."""
    return TranscriptionResult(
        chunk_index=chunk_index,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        language="en",
        model_used="test",
        metrics=_metrics(),
        aligned_tokens=aligned_tokens,
    )


def _tok(word: str, start_ms: int, end_ms: int) -> AlignedToken:
    """Build an AlignedToken for tests."""
    return AlignedToken(word=word, start_ms=start_ms, end_ms=end_ms, score=1.0)


def _ctx(results: list[TranscriptionResult]) -> PipelineContext:
    """Build a minimal PipelineContext carrying ``transcription_results``."""
    from talking_parrot.config.models import TranscribingStep

    config = PipelineConfig(
        expected_language="en",
        transcribing=[TranscribingStep(condition="true", backend="whisper")],
    )
    media_info = MediaInfo(path="x", duration_ms=10_000, sha256="0" * 64)
    return PipelineContext(
        config=config,
        media_info=media_info,
        transcription_results=results,
    )


class TestGranularityAwareProcessorFactoryABC:
    """Spec: ABC + concrete class. Direct instantiation raises ``TypeError``."""

    def test_abstract_base_cannot_be_instantiated(self):
        """``GranularityAwareProcessorFactory()`` raises ``TypeError``."""
        with pytest.raises(TypeError):
            GranularityAwareProcessorFactory()  # type: ignore[abstract]

    def test_default_factory_can_be_instantiated(self):
        """``DefaultGranularityAwareProcessorFactory()`` is constructible."""
        factory = DefaultGranularityAwareProcessorFactory()
        assert isinstance(factory, GranularityAwareProcessorFactory)


class TestFactoryWordGranularity:
    """Spec: WORD returns ``[WordBoundaryMerge, WordBoundarySplit]``."""

    def test_word_returns_merge_then_split(self):
        """Order is ``[Merge, Split]`` (D7)."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "hi", aligned_tokens=[_tok("hi", 0, 1000)])]
        out = factory.create(AlignmentGranularity.WORD, _ctx(results))
        assert len(out) == 2
        assert isinstance(out[0], WordBoundaryMergeProcessor)
        assert isinstance(out[1], WordBoundarySplitProcessor)


class TestFactoryCharacterGranularity:
    """Spec: CHARACTER returns ``[CharacterBoundaryMerge, CharacterBoundarySplit]``."""

    def test_character_returns_merge_then_split(self):
        """Order is ``[Merge, Split]`` (D7)."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "你好")]
        out = factory.create(AlignmentGranularity.CHARACTER, _ctx(results))
        assert len(out) == 2
        assert isinstance(out[0], CharacterBoundaryMergeProcessor)
        assert isinstance(out[1], CharacterBoundarySplitProcessor)


class TestFactoryNoneFallback:
    """Spec: ``None`` returns ``[TimeBasedMerge, TimeBasedSplit]``."""

    def test_none_returns_time_based(self):
        """Order is ``[Merge, Split]`` (D7)."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "hi")]
        out = factory.create(None, _ctx(results))
        assert len(out) == 2
        assert isinstance(out[0], TimeBasedMergeProcessor)
        assert isinstance(out[1], TimeBasedSplitProcessor)


class TestFactoryUnknownGranularity:
    """Spec: unknown granularity raises ``ValueError`` containing the name."""

    def test_unknown_granularity_raises(self):
        """A synthetic enum value triggers ``ValueError`` mentioning the name."""

        class _Synthetic(enum.Enum):
            SYLLABLE = "SYLLABLE"

        factory = DefaultGranularityAwareProcessorFactory()
        with pytest.raises(ValueError, match="SYLLABLE"):
            factory.create(_Synthetic.SYLLABLE, _ctx([]))  # type: ignore[arg-type]


class TestFactoryWordTokenMap:
    """Spec D3: WORD path bakes in a ``token_map_by_index`` keyed by 1-based seed index."""

    def test_token_map_keys_match_seed_indices(self):
        """Three results yield keys ``{1, 2, 3}``."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [
            _tr(0, 0, 1000, "a", aligned_tokens=[_tok("a", 0, 1000)]),
            _tr(1, 1000, 2000, "b", aligned_tokens=[_tok("b", 1000, 2000)]),
            _tr(2, 2000, 3000, "c", aligned_tokens=[_tok("c", 2000, 3000)]),
        ]
        merge, split = factory.create(AlignmentGranularity.WORD, _ctx(results))
        assert isinstance(merge, WordBoundaryMergeProcessor)
        assert isinstance(split, WordBoundarySplitProcessor)
        assert set(merge.token_map_by_index.keys()) == {1, 2, 3}
        assert set(split.token_map_by_index.keys()) == {1, 2, 3}

    def test_missing_tokens_map_to_empty_list(self):
        """``aligned_tokens=None`` becomes ``[]`` in the map (spec example)."""
        factory = DefaultGranularityAwareProcessorFactory()
        t1 = _tok("hello", 0, 500)
        t2 = _tok("world", 500, 1000)
        results = [
            _tr(0, 0, 1000, "hello world", aligned_tokens=[t1, t2]),
            _tr(1, 1000, 2000, "silent", aligned_tokens=None),
        ]
        merge, _split = factory.create(AlignmentGranularity.WORD, _ctx(results))
        assert isinstance(merge, WordBoundaryMergeProcessor)
        assert merge.token_map_by_index[1] == [t1, t2]
        assert merge.token_map_by_index[2] == []

    def test_empty_aligned_tokens_map_to_empty_list(self):
        """An empty-list ``aligned_tokens`` stays empty in the map."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [
            _tr(0, 0, 1000, "x", aligned_tokens=[]),
        ]
        merge, _split = factory.create(AlignmentGranularity.WORD, _ctx(results))
        assert isinstance(merge, WordBoundaryMergeProcessor)
        assert merge.token_map_by_index[1] == []
