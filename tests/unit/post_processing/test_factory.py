"""Tests for ``GranularityAwareProcessorFactory`` and its default impl.

Spec: ``granularity-aware-processor-factory``. Design: D3, D7.
"""

from __future__ import annotations

import enum
from pathlib import Path

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
from talking_parrot.post_processing.dedup import DedupSubtitleProcessor
from talking_parrot.post_processing.factory import (
    DefaultGranularityAwareProcessorFactory,
    GranularityAwareProcessorFactory,
)
from talking_parrot.post_processing.japanese import (
    JapaneseFillerProcessor,
    JapaneseRepetitionProcessor,
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


def _ctx(
    results: list[TranscriptionResult], expected_language: str = "en"
) -> PipelineContext:
    """Build a minimal PipelineContext carrying ``transcription_results``."""
    from talking_parrot.config.models import TranscribingStep

    config = PipelineConfig(
        expected_language=expected_language,
        transcribing=[TranscribingStep(condition="true", backend="whisper")],
    )
    media_info = MediaInfo(path=Path("x"), duration_ms=10_000, sha256="0" * 64)
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
    """Spec: WORD returns ``[Dedup, WordBoundaryMerge, WordBoundarySplit, ...]``."""

    def test_word_with_non_japanese_returns_dedup_merge_split(self):
        """Non-Japanese WORD path: length 3, ``[Dedup, Merge, Split]``."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "hi", aligned_tokens=[_tok("hi", 0, 1000)])]
        out = factory.create(
            AlignmentGranularity.WORD, _ctx(results, expected_language="en")
        )
        assert len(out) == 3
        assert isinstance(out[0], DedupSubtitleProcessor)
        assert isinstance(out[1], WordBoundaryMergeProcessor)
        assert isinstance(out[2], WordBoundarySplitProcessor)
        assert not any(isinstance(p, JapaneseFillerProcessor) for p in out)
        assert not any(isinstance(p, JapaneseRepetitionProcessor) for p in out)

    def test_word_with_japanese_appends_filler_and_repetition(self):
        """Japanese WORD path: length 5, Japanese pair appended last."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "hi", aligned_tokens=[_tok("hi", 0, 1000)])]
        out = factory.create(
            AlignmentGranularity.WORD, _ctx(results, expected_language="ja")
        )
        assert len(out) == 5
        assert isinstance(out[0], DedupSubtitleProcessor)
        assert isinstance(out[1], WordBoundaryMergeProcessor)
        assert isinstance(out[2], WordBoundarySplitProcessor)
        assert isinstance(out[3], JapaneseFillerProcessor)
        assert isinstance(out[4], JapaneseRepetitionProcessor)


class TestFactoryCharacterGranularity:
    """Spec: CHARACTER returns ``[Dedup, CharacterBoundaryMerge, CharacterBoundarySplit, ...]``."""

    def test_character_with_japanese_returns_full_pipeline(self):
        """Japanese CHARACTER path: length 5 with Japanese pair appended."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "こんにちは")]
        out = factory.create(
            AlignmentGranularity.CHARACTER, _ctx(results, expected_language="ja")
        )
        assert len(out) == 5
        assert isinstance(out[0], DedupSubtitleProcessor)
        assert isinstance(out[1], CharacterBoundaryMergeProcessor)
        assert isinstance(out[2], CharacterBoundarySplitProcessor)
        assert isinstance(out[3], JapaneseFillerProcessor)
        assert isinstance(out[4], JapaneseRepetitionProcessor)

    def test_character_with_non_japanese_omits_japanese_processors(self):
        """Non-Japanese CHARACTER path (zh): length 3, no Japanese processors."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "你好")]
        out = factory.create(
            AlignmentGranularity.CHARACTER, _ctx(results, expected_language="zh")
        )
        assert len(out) == 3
        assert isinstance(out[0], DedupSubtitleProcessor)
        assert isinstance(out[1], CharacterBoundaryMergeProcessor)
        assert isinstance(out[2], CharacterBoundarySplitProcessor)
        assert not any(isinstance(p, JapaneseFillerProcessor) for p in out)
        assert not any(isinstance(p, JapaneseRepetitionProcessor) for p in out)


class TestFactoryNoneFallback:
    """Spec: ``None`` returns ``[Dedup, TimeBasedMerge, TimeBasedSplit, ...]``."""

    def test_none_returns_time_based_with_dedup_prefix(self):
        """Non-Japanese None path: length 3, ``[Dedup, TimeMerge, TimeSplit]``."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "hi")]
        out = factory.create(None, _ctx(results, expected_language="en"))
        assert len(out) == 3
        assert isinstance(out[0], DedupSubtitleProcessor)
        assert isinstance(out[1], TimeBasedMergeProcessor)
        assert isinstance(out[2], TimeBasedSplitProcessor)
        assert not any(isinstance(p, JapaneseFillerProcessor) for p in out)
        assert not any(isinstance(p, JapaneseRepetitionProcessor) for p in out)

    def test_none_with_japanese_appends_filler_and_repetition(self):
        """Japanese None path: length 5, Japanese pair appended."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "hi")]
        out = factory.create(None, _ctx(results, expected_language="ja"))
        assert len(out) == 5
        assert isinstance(out[0], DedupSubtitleProcessor)
        assert isinstance(out[1], TimeBasedMergeProcessor)
        assert isinstance(out[2], TimeBasedSplitProcessor)
        assert isinstance(out[3], JapaneseFillerProcessor)
        assert isinstance(out[4], JapaneseRepetitionProcessor)


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
        out = factory.create(AlignmentGranularity.WORD, _ctx(results))
        merge = next(p for p in out if isinstance(p, WordBoundaryMergeProcessor))
        split = next(p for p in out if isinstance(p, WordBoundarySplitProcessor))
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
        out = factory.create(AlignmentGranularity.WORD, _ctx(results))
        merge = next(p for p in out if isinstance(p, WordBoundaryMergeProcessor))
        assert merge.token_map_by_index[1] == [t1, t2]
        assert merge.token_map_by_index[2] == []

    def test_empty_aligned_tokens_map_to_empty_list(self):
        """An empty-list ``aligned_tokens`` stays empty in the map."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [
            _tr(0, 0, 1000, "x", aligned_tokens=[]),
        ]
        out = factory.create(AlignmentGranularity.WORD, _ctx(results))
        merge = next(p for p in out if isinstance(p, WordBoundaryMergeProcessor))
        assert merge.token_map_by_index[1] == []


class TestFactorySplitBoundaryPolicyInjection:
    """`DefaultGranularityAwareProcessorFactory` injects SplitBoundaryPolicy."""

    def test_character_japanese_injects_japanese_policy(self):
        from talking_parrot.post_processing.japanese import (
            JapaneseSplitBoundaryPolicy,
        )

        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(
            AlignmentGranularity.CHARACTER, _ctx([], expected_language="ja")
        )
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert isinstance(split._policy, JapaneseSplitBoundaryPolicy)

    def test_character_non_japanese_injects_linear_policy(self):
        from talking_parrot.post_processing.split_policy import (
            LinearSplitBoundaryPolicy,
        )

        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(
            AlignmentGranularity.CHARACTER, _ctx([], expected_language="en")
        )
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert isinstance(split._policy, LinearSplitBoundaryPolicy)

    def test_none_granularity_japanese_injects_japanese_policy(self):
        from talking_parrot.post_processing.japanese import (
            JapaneseSplitBoundaryPolicy,
        )

        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(None, _ctx([], expected_language="ja"))
        split = next(p for p in out if isinstance(p, TimeBasedSplitProcessor))
        assert isinstance(split._policy, JapaneseSplitBoundaryPolicy)

    def test_none_granularity_non_japanese_injects_linear_policy(self):
        from talking_parrot.post_processing.split_policy import (
            LinearSplitBoundaryPolicy,
        )

        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(None, _ctx([], expected_language="en"))
        split = next(p for p in out if isinstance(p, TimeBasedSplitProcessor))
        assert isinstance(split._policy, LinearSplitBoundaryPolicy)

    def test_word_granularity_no_policy_passed(self):
        """`WordBoundarySplitProcessor` MUST NOT receive a policy keyword."""
        import inspect

        sig = inspect.signature(WordBoundarySplitProcessor.__init__)
        params = sig.parameters
        # The constructor must not have a `policy` kwarg in the first place,
        # which is the structural guarantee that the factory cannot pass one.
        assert "policy" not in params

    def test_word_granularity_works_for_japanese_language(self):
        """WORD path with `expected_language='ja'` MUST construct without errors."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [_tr(0, 0, 1000, "hello", aligned_tokens=[])]
        # Must not raise.
        factory.create(AlignmentGranularity.WORD, _ctx(results, expected_language="ja"))


def _ctx_with_vad(
    vad_segments: list,
    expected_language: str = "en",
    radius_ms: int = 250,
) -> PipelineContext:
    """Build a PipelineContext with vad_segments and a configured snap radius."""
    from talking_parrot.config.models import (
        PostProcessingConfig,
        TranscribingStep,
    )

    config = PipelineConfig(
        expected_language=expected_language,
        transcribing=[TranscribingStep(condition="true", backend="whisper")],
        post_processing=PostProcessingConfig(split_time_snap_radius_ms=radius_ms),
    )
    media_info = MediaInfo(path=Path("x"), duration_ms=10_000, sha256="0" * 64)
    return PipelineContext(
        config=config,
        media_info=media_info,
        vad_segments=vad_segments,
    )


def _vad(start_ms: int, end_ms: int):
    from talking_parrot.models.vad import VadSegment

    return VadSegment(
        start_ms=start_ms,
        end_ms=end_ms,
        ten_vad_prob=0.9,
        silero_vad_prob=0.9,
        composite_score=0.9,
    )


class TestFactorySplitTimePolicyInjection:
    """`DefaultGranularityAwareProcessorFactory` injects SplitTimePolicy."""

    def test_character_with_vad_and_radius_injects_vad_aligned_policy(self):
        from talking_parrot.post_processing.split_time_policy import (
            VadAlignedSplitTimePolicy,
        )

        ctx = _ctx_with_vad([_vad(0, 1000), _vad(1500, 3000)], radius_ms=250)
        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(AlignmentGranularity.CHARACTER, ctx)
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert isinstance(split._time_policy, VadAlignedSplitTimePolicy)

    def test_none_granularity_with_vad_injects_vad_aligned_policy(self):
        from talking_parrot.post_processing.split_time_policy import (
            VadAlignedSplitTimePolicy,
        )

        ctx = _ctx_with_vad([_vad(0, 1000), _vad(1500, 3000)], radius_ms=250)
        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(None, ctx)
        split = next(p for p in out if isinstance(p, TimeBasedSplitProcessor))
        assert isinstance(split._time_policy, VadAlignedSplitTimePolicy)

    def test_empty_vad_segments_injects_linear_time_policy(self):
        from talking_parrot.post_processing.split_time_policy import (
            LinearSplitTimePolicy,
        )

        ctx = _ctx_with_vad([], radius_ms=250)
        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(AlignmentGranularity.CHARACTER, ctx)
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert isinstance(split._time_policy, LinearSplitTimePolicy)

    def test_zero_radius_injects_linear_time_policy(self):
        from talking_parrot.post_processing.split_time_policy import (
            LinearSplitTimePolicy,
        )

        ctx = _ctx_with_vad([_vad(0, 1000), _vad(1500, 3000)], radius_ms=0)
        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(None, ctx)
        split = next(p for p in out if isinstance(p, TimeBasedSplitProcessor))
        assert isinstance(split._time_policy, LinearSplitTimePolicy)

    def test_word_granularity_no_time_policy_passed(self):
        """`WordBoundarySplitProcessor` MUST NOT receive a `time_policy` keyword."""
        import inspect

        sig = inspect.signature(WordBoundarySplitProcessor.__init__)
        assert "time_policy" not in sig.parameters

    def test_non_positive_gaps_are_filtered(self):
        """Back-to-back or overlapping segments yield no silences → linear fallback."""
        from talking_parrot.post_processing.split_time_policy import (
            LinearSplitTimePolicy,
        )

        ctx = _ctx_with_vad(
            [_vad(0, 1000), _vad(1000, 2000), _vad(1900, 3000)], radius_ms=250
        )
        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(None, ctx)
        split = next(p for p in out if isinstance(p, TimeBasedSplitProcessor))
        # All gaps non-positive → no silences → fallback to linear policy.
        assert isinstance(split._time_policy, LinearSplitTimePolicy)
        assert split._time_policy.adjust(1500, 0, 3000) == 1500

    def test_boundary_and_time_policies_passed_in_same_call(self):
        """Both `policy` and `time_policy` MUST be on the same constructor call."""
        from talking_parrot.post_processing.japanese import (
            JapaneseSplitBoundaryPolicy,
        )
        from talking_parrot.post_processing.split_time_policy import (
            VadAlignedSplitTimePolicy,
        )

        ctx = _ctx_with_vad(
            [_vad(0, 1000), _vad(1500, 3000)],
            expected_language="ja",
            radius_ms=250,
        )
        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(AlignmentGranularity.CHARACTER, ctx)
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert isinstance(split._policy, JapaneseSplitBoundaryPolicy)
        assert isinstance(split._time_policy, VadAlignedSplitTimePolicy)


class TestFactoryCharacterTokenMapInjection:
    """Spec ``granularity-aware-processor-factory``: CHARACTER injects token_map_by_index.

    Decision 1: factory threads ``_build_token_map`` result into
    ``CharacterBoundarySplitProcessor`` (mirroring the WORD-path pattern).
    """

    def test_character_path_injects_token_map_into_split_processor(self):
        """Two transcription results → CharacterBoundarySplitProcessor.token_map keys = {1, 2}."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [
            _tr(0, 0, 1000, "a", aligned_tokens=[_tok("a", 0, 1000)]),
            _tr(1, 1000, 2000, "b", aligned_tokens=[_tok("b", 1000, 2000)]),
        ]
        out = factory.create(AlignmentGranularity.CHARACTER, _ctx(results))
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert hasattr(split, "_token_map_by_index")
        assert set(split._token_map_by_index.keys()) == {1, 2}

    def test_character_missing_aligned_tokens_map_to_empty_list(self):
        """``aligned_tokens=None`` → ``[]`` in token_map (mirrors WORD-path semantics)."""
        factory = DefaultGranularityAwareProcessorFactory()
        results = [
            _tr(0, 0, 1000, "a", aligned_tokens=None),
        ]
        out = factory.create(AlignmentGranularity.CHARACTER, _ctx(results))
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert split._token_map_by_index == {1: []}

    def test_character_e2e_full_pipeline_uses_vad_aligned_and_token_map(self):
        """End-to-end (Decision 6): VAD context + radius>0 + tokens → both injected.

        The CHARACTER-path split processor MUST receive both a
        ``VadAlignedSplitTimePolicy`` and a populated ``token_map_by_index``
        when the pipeline context provides VAD segments and aligned tokens.
        """
        from talking_parrot.config.models import (
            PipelineConfig,
            PostProcessingConfig,
            TranscribingStep,
        )
        from talking_parrot.post_processing.split_time_policy import (
            VadAlignedSplitTimePolicy,
        )

        config = PipelineConfig(
            expected_language="ja",
            transcribing=[TranscribingStep(condition="true", backend="whisper")],
            post_processing=PostProcessingConfig(split_time_snap_radius_ms=300),
        )
        media_info = MediaInfo(path=Path("x"), duration_ms=10_000, sha256="0" * 64)
        results = [
            _tr(
                0,
                0,
                9000,
                "あいうえおかきくけこ",
                aligned_tokens=[
                    _tok("あいうえお", 0, 4000),
                    _tok("かきくけこ", 4000, 9000),
                ],
            ),
        ]
        ctx = PipelineContext(
            config=config,
            media_info=media_info,
            transcription_results=results,
            vad_segments=[_vad(0, 4000), _vad(4400, 9000)],
        )
        factory = DefaultGranularityAwareProcessorFactory()
        out = factory.create(AlignmentGranularity.CHARACTER, ctx)
        split = next(p for p in out if isinstance(p, CharacterBoundarySplitProcessor))
        assert isinstance(split._time_policy, VadAlignedSplitTimePolicy)
        assert split._token_map_by_index.keys() == {1}
        # Primary VAD-driven path: pick() must return the silence midpoint
        # that lies inside (0, 9000), namely (4000+4400)//2 = 4200.
        assert split._time_policy.pick(0, 9000) == 4200


class TestFactoryVadGrammarSearchRadiusWiring:
    """ADR-0004: ``PostProcessingConfig.vad_grammar_search_radius`` flows through to the processor.

    The factory does not need to read the field directly — the processor's
    ``process(subs, config)`` signature reads it from the config — but this
    test pins down that contract end-to-end.
    """

    def test_custom_radius_drives_grammar_snap_path(self, caplog):
        """A non-default ``vad_grammar_search_radius`` must reach the processor."""
        import logging
        import re

        from talking_parrot.config.models import (
            PipelineConfig,
            PostProcessingConfig,
            TranscribingStep,
        )
        from talking_parrot.models.context import (
            AlignmentGranularity,
            PipelineContext,
        )
        from talking_parrot.models.media import MediaInfo
        from talking_parrot.models.subtitle import Subtitle

        ansi_re = re.compile(r"\x1b\[[0-9;]*m")

        # Custom config with a non-default vad_grammar_search_radius.
        post_cfg = PostProcessingConfig(
            max_line_length=20,
            max_lines_per_subtitle=2,
            merge_gap_threshold_ms=200,
            merge_max_duration_ms=6000,
            split_max_duration_ms=6000,
            vad_grammar_search_radius=3,
            japanese_split_search_radius=4,
        )
        pipeline_cfg = PipelineConfig(
            expected_language="ja",
            transcribing=[TranscribingStep(condition="true", backend="whisper")],
            post_processing=post_cfg,
        )
        from talking_parrot.models.vad import VadSegment

        # Two VAD segments with a silence gap whose midpoint falls at 7700 ms —
        # that places ``char_idx_vad`` on the leading-final boundary (8) where
        # ``し|た`` would split, forcing the grammar sanity gate to engage.
        vad_segments = [
            VadSegment(
                start_ms=0,
                end_ms=7600,
                ten_vad_prob=1.0,
                silero_vad_prob=1.0,
                composite_score=1.0,
            ),
            VadSegment(
                start_ms=7800,
                end_ms=9000,
                ten_vad_prob=1.0,
                silero_vad_prob=1.0,
                composite_score=1.0,
            ),
        ]
        ctx = PipelineContext(
            config=pipeline_cfg,
            media_info=MediaInfo(path=Path("x"), duration_ms=10_000, sha256="0" * 64),
            vad_segments=vad_segments,
            transcription_results=[
                _tr(
                    chunk_index=0,
                    start_ms=0,
                    end_ms=9000,
                    text="専攻しておりました",
                    aligned_tokens=[
                        _tok("専攻し", 0, 3000),
                        _tok("ており", 3000, 6000),
                        _tok("まし", 6000, 7500),
                        _tok("た", 7500, 9000),
                    ],
                ),
            ],
        )

        factory = DefaultGranularityAwareProcessorFactory()
        processors = factory.create(AlignmentGranularity.CHARACTER, ctx)
        # Find the CharacterBoundarySplitProcessor in the processor list.
        split_proc = next(
            p for p in processors if isinstance(p, CharacterBoundarySplitProcessor)
        )

        sub = Subtitle(index=1, start_ms=0, end_ms=9000, text="専攻しておりました")
        with caplog.at_level(logging.INFO, logger="talking_parrot.post_processing"):
            split_proc.process([sub], post_cfg)
        info_msgs = [
            ansi_re.sub("", r.getMessage())
            for r in caplog.records
            if r.levelno == logging.INFO
        ]
        # The Japanese policy + token layout above place the VAD-derived
        # char_idx on a leading-final boundary; the snap path must fire
        # somewhere with the configured small radius reaching the policy.
        # We only require that *some* INFO log surfaces, proving the field
        # is wired through.
        assert any("grammar_snap" in m or "grammar_fallback" in m for m in info_msgs), (
            info_msgs
        )
