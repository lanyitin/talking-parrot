"""Unit tests for ChunkingStage — disabled-path and greedy accumulation behaviour.

Covers tasks 2.1, 2.2, 3.1 and 3.2 of the implement-chunking-stage change:
- When ``config.chunking`` is ``None``, the stage returns the input context
  unchanged.
- When ``config.chunking.enabled`` is ``False``, the stage returns the input
  context unchanged with no chunks populated.
- Greedy accumulation: segments are grouped left-to-right into chunks that do
  not exceed ``max_chunk_seconds``.
"""

from __future__ import annotations

import pytest

from talking_parrot.config.models import ChunkingConfig, PipelineConfig
from talking_parrot.models.context import PipelineContext
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.vad import VadSegment
from talking_parrot.stages.chunking_stage import ChunkingStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vad_segments() -> list[VadSegment]:
    """Return a non-empty list of VadSegment objects for use in fixtures."""
    return [
        VadSegment(
            start_ms=0,
            end_ms=500,
            ten_vad_prob=0.9,
            silero_vad_prob=0.85,
            composite_score=0.875,
        ),
        VadSegment(
            start_ms=1000,
            end_ms=2000,
            ten_vad_prob=0.8,
            silero_vad_prob=0.75,
            composite_score=0.775,
        ),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ctx_chunking_disabled() -> PipelineContext:
    """Return a PipelineContext with ``config.chunking.enabled = False`` and non-empty vad_segments."""
    cfg = PipelineConfig(
        transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        chunking=ChunkingConfig(enabled=False),
    )
    info = MediaInfo(path="/tmp/test.mp4", duration_ms=5000, sha256="deadbeef")
    return PipelineContext(
        config=cfg,
        media_info=info,
        vad_segments=_make_vad_segments(),
        chunks=[],
    )


@pytest.fixture()
def ctx_chunking_none() -> PipelineContext:
    """Return a PipelineContext with ``config.chunking = None`` and non-empty vad_segments."""
    cfg = PipelineConfig(
        transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        chunking=None,
    )
    info = MediaInfo(path="/tmp/test.mp4", duration_ms=5000, sha256="deadbeef")
    return PipelineContext(
        config=cfg,
        media_info=info,
        vad_segments=_make_vad_segments(),
        chunks=[],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChunkingStageDisabled:
    """ChunkingStage disabled-path tests."""

    def test_disabled_stage_returns_ctx_unchanged(
        self, ctx_chunking_disabled: PipelineContext
    ) -> None:
        """When enabled=False, process() returns the input context with chunks == []."""
        stage = ChunkingStage()
        result = stage.process(ctx_chunking_disabled)

        assert result is ctx_chunking_disabled, (
            "ChunkingStage with enabled=False must return the same context object"
        )
        assert result.chunks == [], (
            "ChunkingStage with enabled=False must not populate chunks"
        )

    def test_chunking_none_returns_ctx_unchanged(
        self, ctx_chunking_none: PipelineContext
    ) -> None:
        """When config.chunking is None, process() returns the input context with chunks == []."""
        stage = ChunkingStage()
        result = stage.process(ctx_chunking_none)

        assert result is ctx_chunking_none, (
            "ChunkingStage with chunking=None must return the same context object"
        )
        assert result.chunks == [], (
            "ChunkingStage with chunking=None must not populate chunks"
        )

    def test_name_property(self) -> None:
        """ChunkingStage.name returns 'chunking'."""
        stage = ChunkingStage()
        assert stage.name == "chunking"


# ---------------------------------------------------------------------------
# Greedy accumulation tests
# ---------------------------------------------------------------------------


def _make_seg(start_ms: int, end_ms: int) -> VadSegment:
    """Return a VadSegment with the given boundaries and placeholder probability values."""
    return VadSegment(
        start_ms=start_ms,
        end_ms=end_ms,
        ten_vad_prob=0.9,
        silero_vad_prob=0.85,
        composite_score=0.875,
    )


def _make_enabled_ctx(
    vad_segments: list[VadSegment],
    max_chunk_seconds: int = 30,
    silence_pad_ms: int = 0,
) -> "PipelineContext":
    """Return a PipelineContext with chunking enabled and the given segments."""
    from talking_parrot.models.media import MediaInfo

    cfg = PipelineConfig(
        transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        chunking=ChunkingConfig(
            enabled=True,
            max_chunk_seconds=max_chunk_seconds,
            silence_pad_ms=silence_pad_ms,
        ),
    )
    info = MediaInfo(path="/tmp/test.mp4", duration_ms=60_000, sha256="deadbeef")
    return PipelineContext(
        config=cfg,
        media_info=info,
        vad_segments=vad_segments,
        chunks=[],
    )


class TestChunkingStageGreedyAccumulation:
    """ChunkingStage greedy accumulation tests (tasks 3.1 and 3.2)."""

    def test_all_segments_fit_one_chunk(self) -> None:
        """When all segments span less than max_chunk_seconds, they are grouped into one chunk.

        Three segments spanning 0–25 000 ms (25 s) with a 30 s limit must
        produce exactly one chunk containing all three source segments.
        """
        segs = [
            _make_seg(0, 10_000),
            _make_seg(11_000, 21_000),
            _make_seg(20_500, 25_000),
        ]
        ctx = _make_enabled_ctx(segs, max_chunk_seconds=30, silence_pad_ms=0)

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) == 1, (
            f"Expected 1 chunk when all segments fit within max_chunk_seconds, got {len(chunks)}"
        )
        assert chunks[0].source_segments == segs, (
            "The single chunk must contain all three source segments"
        )

    def test_segments_split_at_max_chunk_seconds(self) -> None:
        """Segments are split into multiple chunks when cumulative span exceeds max_chunk_seconds.

        Spec example: three segments 0–10 000 ms, 11 000–21 000 ms, 22 000–32 000 ms
        with a 30 s limit.  Segments 0 and 1 span 21 s (fit); adding segment 2
        would span 32 s (exceeds 30) so segment 2 starts a new chunk.

        Expected:
        - chunk 0: segs 0+1, start_ms=0, end_ms=21 000
        - chunk 1: seg 2, start_ms=22 000, end_ms=32 000
        - indices: [0, 1]
        """
        seg0 = _make_seg(0, 10_000)
        seg1 = _make_seg(11_000, 21_000)
        seg2 = _make_seg(22_000, 32_000)
        segs = [seg0, seg1, seg2]
        ctx = _make_enabled_ctx(segs, max_chunk_seconds=30, silence_pad_ms=0)

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) == 2, (
            f"Expected 2 chunks for the spec example, got {len(chunks)}"
        )

        assert chunks[0].source_segments == [seg0, seg1], (
            "Chunk 0 must contain segments 0 and 1"
        )
        assert chunks[0].start_ms == 0, (
            f"Chunk 0 start_ms must be 0, got {chunks[0].start_ms}"
        )
        assert chunks[0].end_ms == 21_000, (
            f"Chunk 0 end_ms must be 21 000, got {chunks[0].end_ms}"
        )

        assert chunks[1].source_segments == [seg2], (
            "Chunk 1 must contain only segment 2"
        )
        assert chunks[1].start_ms == 22_000, (
            f"Chunk 1 start_ms must be 22 000, got {chunks[1].start_ms}"
        )
        assert chunks[1].end_ms == 32_000, (
            f"Chunk 1 end_ms must be 32 000, got {chunks[1].end_ms}"
        )

        assert [c.index for c in chunks] == [0, 1], (
            f"Chunk indices must be [0, 1], got {[c.index for c in chunks]}"
        )

    def test_empty_vad_segments_yields_empty_chunks(self) -> None:
        """When vad_segments is empty, chunks must be an empty list."""
        ctx = _make_enabled_ctx([], max_chunk_seconds=30, silence_pad_ms=0)

        stage = ChunkingStage()
        result = stage.process(ctx)

        assert result.chunks == [], (
            f"Expected empty chunks for empty vad_segments, got {result.chunks}"
        )

    def test_chunk_indices_are_zero_based_contiguous(self) -> None:
        """Chunk indices must be zero-based and contiguous: [0, 1, 2, ...].

        Uses four segments that produce at least 3 chunks (each 11 s, limit 10 s).
        """
        segs = [
            _make_seg(0, 10_000),
            _make_seg(11_000, 21_000),
            _make_seg(22_000, 32_000),
            _make_seg(33_000, 43_000),
        ]
        # 10 s limit means each segment forms its own chunk (each spans 10 s exactly,
        # which is not > 10 s, so actually segs may accumulate — use 9 s limit instead).
        ctx = _make_enabled_ctx(segs, max_chunk_seconds=9, silence_pad_ms=0)

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) >= 3, (
            f"Expected at least 3 chunks with 9 s limit, got {len(chunks)}"
        )
        assert [c.index for c in chunks] == list(range(len(chunks))), (
            f"Chunk indices must be zero-based contiguous, got {[c.index for c in chunks]}"
        )


# ---------------------------------------------------------------------------
# Hard-cut fallback tests (tasks 4.1 and 4.2)
# ---------------------------------------------------------------------------


class TestChunkingStageHardCut:
    """ChunkingStage hard-cut fallback tests for oversized segments (tasks 4.1 and 4.2).

    When a single VadSegment has duration > max_chunk_seconds * 1000 ms, the
    stage must split it into consecutive sub-chunks of exactly max_chunk_seconds
    * 1000 ms each (except the final sub-chunk which may be shorter).
    """

    def test_oversized_segment_split_exact_spec_example(self) -> None:
        """Exact spec example: 75 s segment with 30 s limit produces three chunks.

        GIVEN one VadSegment(start_ms=0, end_ms=75_000) and max_chunk_seconds=30
        WHEN ChunkingStage.process(ctx) runs
        THEN three chunks are produced:
          - chunks[0]: start_ms=0,      end_ms=30_000, source_segments=[original_seg]
          - chunks[1]: start_ms=30_000, end_ms=60_000, source_segments=[original_seg]
          - chunks[2]: start_ms=60_000, end_ms=75_000, source_segments=[original_seg]
          - indices: [0, 1, 2]
        """
        original_seg = _make_seg(0, 75_000)
        ctx = _make_enabled_ctx([original_seg], max_chunk_seconds=30, silence_pad_ms=0)

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) == 3, (
            f"Expected 3 chunks for a 75 s segment with 30 s limit, got {len(chunks)}"
        )

        assert chunks[0].start_ms == 0, (
            f"chunks[0].start_ms must be 0, got {chunks[0].start_ms}"
        )
        assert chunks[0].end_ms == 30_000, (
            f"chunks[0].end_ms must be 30_000, got {chunks[0].end_ms}"
        )
        assert chunks[0].source_segments == [original_seg], (
            "chunks[0].source_segments must be [original_seg]"
        )

        assert chunks[1].start_ms == 30_000, (
            f"chunks[1].start_ms must be 30_000, got {chunks[1].start_ms}"
        )
        assert chunks[1].end_ms == 60_000, (
            f"chunks[1].end_ms must be 60_000, got {chunks[1].end_ms}"
        )
        assert chunks[1].source_segments == [original_seg], (
            "chunks[1].source_segments must be [original_seg]"
        )

        assert chunks[2].start_ms == 60_000, (
            f"chunks[2].start_ms must be 60_000, got {chunks[2].start_ms}"
        )
        assert chunks[2].end_ms == 75_000, (
            f"chunks[2].end_ms must be 75_000, got {chunks[2].end_ms}"
        )
        assert chunks[2].source_segments == [original_seg], (
            "chunks[2].source_segments must be [original_seg]"
        )

        assert [c.index for c in chunks] == [0, 1, 2], (
            f"Chunk indices must be [0, 1, 2], got {[c.index for c in chunks]}"
        )

    def test_oversized_segment_no_gap_no_overlap(self) -> None:
        """Sub-chunks produced by hard-cut must have no gap and no overlap.

        For all consecutive chunk pairs, end of chunk[i] must equal start of chunk[i+1].
        """
        original_seg = _make_seg(0, 75_000)
        ctx = _make_enabled_ctx([original_seg], max_chunk_seconds=30, silence_pad_ms=0)

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) >= 2, (
            f"Expected at least 2 chunks for hard-cut test, got {len(chunks)}"
        )

        for i in range(len(chunks) - 1):
            assert chunks[i].end_ms == chunks[i + 1].start_ms, (
                f"Gap or overlap detected between chunk[{i}] (end_ms={chunks[i].end_ms}) "
                f"and chunk[{i + 1}] (start_ms={chunks[i + 1].start_ms})"
            )

    def test_exactly_at_limit_not_split(self) -> None:
        """A segment of exactly max_chunk_seconds * 1000 ms must NOT be split.

        The condition uses strict inequality (>), so a segment at exactly the
        limit is not oversized and must remain as a single chunk.
        """
        # 30 s exactly — should NOT be split
        original_seg = _make_seg(0, 30_000)
        ctx = _make_enabled_ctx([original_seg], max_chunk_seconds=30, silence_pad_ms=0)

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) == 1, (
            f"A segment at exactly max_chunk_seconds must NOT be split, got {len(chunks)} chunks"
        )
        assert chunks[0].start_ms == 0
        assert chunks[0].end_ms == 30_000
        assert chunks[0].source_segments == [original_seg]


# ---------------------------------------------------------------------------
# Silence-pad expansion tests (tasks 5.1 and 5.2)
# ---------------------------------------------------------------------------


def _make_silence_pad_ctx(
    vad_segments: list[VadSegment],
    silence_pad_ms: int,
    duration_ms: int,
    max_chunk_seconds: int = 30,
) -> "PipelineContext":
    """Return a PipelineContext configured for silence-pad expansion tests.

    Args:
        vad_segments: The VAD segments to include in the context.
        silence_pad_ms: Number of milliseconds to pad each chunk boundary.
        duration_ms: Total audio duration in milliseconds (used for clamping).
        max_chunk_seconds: Maximum chunk duration in seconds (default: 30).

    Returns:
        A ``PipelineContext`` with chunking enabled and the given parameters.
    """
    from talking_parrot.models.media import MediaInfo

    cfg = PipelineConfig(
        transcribing=[{"condition": "true", "backend": "faster-whisper"}],
        chunking=ChunkingConfig(
            enabled=True,
            max_chunk_seconds=max_chunk_seconds,
            silence_pad_ms=silence_pad_ms,
        ),
    )
    info = MediaInfo(path="/tmp/test.mp4", duration_ms=duration_ms, sha256="deadbeef")
    return PipelineContext(
        config=cfg,
        media_info=info,
        vad_segments=vad_segments,
        chunks=[],
    )


class TestChunkingStagesilencePad:
    """ChunkingStage silence-pad expansion tests (tasks 5.1 and 5.2).

    After sealing all chunks, each chunk's boundaries are expanded by
    ``config.chunking.silence_pad_ms`` milliseconds:
    - ``start_ms`` is decreased by ``silence_pad_ms`` (clamped to 0)
    - ``end_ms`` is increased by ``silence_pad_ms`` (clamped to ``ctx.media_info.duration_ms``)
    """

    def test_silence_pad_applied_within_bounds(self) -> None:
        """Silence pad is applied to a chunk that fits within the audio bounds.

        WHEN silence_pad_ms=50 and a chunk has start_ms=100, end_ms=5000
        THEN returned chunk MUST have start_ms=50 and end_ms=5050.
        """
        seg = _make_seg(100, 5000)
        ctx = _make_silence_pad_ctx(
            vad_segments=[seg],
            silence_pad_ms=50,
            duration_ms=10_000,
        )

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
        assert chunks[0].start_ms == 50, (
            f"start_ms must be 50 after silence pad, got {chunks[0].start_ms}"
        )
        assert chunks[0].end_ms == 5050, (
            f"end_ms must be 5050 after silence pad, got {chunks[0].end_ms}"
        )

    def test_silence_pad_clamped_at_audio_start(self) -> None:
        """Silence pad at audio start is clamped to 0 (not negative).

        WHEN silence_pad_ms=200 and a chunk has start_ms=100
        THEN returned chunk MUST have start_ms=0 (not -100).
        """
        seg = _make_seg(100, 5000)
        ctx = _make_silence_pad_ctx(
            vad_segments=[seg],
            silence_pad_ms=200,
            duration_ms=10_000,
        )

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
        assert chunks[0].start_ms == 0, (
            f"start_ms must be clamped to 0 (not -100), got {chunks[0].start_ms}"
        )

    def test_silence_pad_clamped_at_audio_end(self) -> None:
        """Silence pad at audio end is clamped to duration_ms.

        WHEN silence_pad_ms=200 and a chunk has end_ms within 100 ms of duration_ms
        THEN returned chunk's end_ms MUST equal duration_ms.
        """
        seg = _make_seg(1000, 9950)
        ctx = _make_silence_pad_ctx(
            vad_segments=[seg],
            silence_pad_ms=200,
            duration_ms=10_000,
        )

        stage = ChunkingStage()
        result = stage.process(ctx)

        chunks = result.chunks
        assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
        assert chunks[0].end_ms == 10_000, (
            f"end_ms must be clamped to duration_ms=10_000, got {chunks[0].end_ms}"
        )
