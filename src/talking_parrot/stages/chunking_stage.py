"""ChunkingStage — pipeline stage that groups VAD segments into audio chunks.

This module provides the ``ChunkingStage`` class, which is responsible for
grouping ``VadSegment`` objects (produced by ``VADStage``) into ``Chunk``
objects that represent discrete audio windows suitable for transcription.

The greedy accumulation algorithm iterates over ``ctx.vad_segments``
left-to-right and accumulates segments into a pending chunk.  When adding the
next segment would cause the pending chunk to exceed ``max_chunk_seconds``, the
pending chunk is sealed and a new one is started.

Hard-cut fallback: when a single ``VadSegment`` is longer than
``max_chunk_seconds * 1000 ms``, it is pre-split into consecutive sub-chunks of
exactly ``max_chunk_seconds * 1000 ms`` (except the final sub-chunk which may be
shorter) before being fed into the greedy accumulation loop.

Silence-padding post-pass: after all chunks are sealed, each chunk's boundaries
are expanded by ``config.chunking.silence_pad_ms`` milliseconds.  ``start_ms``
is decreased (clamped to 0) and ``end_ms`` is increased (clamped to
``ctx.media_info.duration_ms``).  A pad of 0 is a no-op.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, NamedTuple

import structlog

from talking_parrot.models.chunk import Chunk
from talking_parrot.models.vad import VadSegment
from talking_parrot.stages.base import PipelineStage

if TYPE_CHECKING:
    from talking_parrot.models.context import PipelineContext

logger = structlog.get_logger(__name__)


class _SegmentItem(NamedTuple):
    """Internal representation of a (possibly split) segment used in greedy accumulation.

    Attributes:
        start_ms: Start time in milliseconds.
        end_ms: End time in milliseconds.
        source_segments: The original ``VadSegment`` object(s) this item maps to.
            For normal (non-oversized) segments this is ``[seg]``.
            For sub-chunks of an oversized segment this is ``[original_seg]``.
    """

    start_ms: int
    end_ms: int
    source_segments: list[VadSegment]


class ChunkingStage(PipelineStage):
    """Pipeline stage that groups VAD segments into transcription-ready chunks.

    When the chunking stage is disabled (i.e. ``config.chunking`` is ``None``
    or ``config.chunking.enabled`` is ``False``), the stage returns the input
    context unchanged with no side effects.

    When enabled, the stage applies a greedy accumulation strategy: segments
    are added to the current pending chunk as long as the cumulative span does
    not exceed ``config.chunking.max_chunk_seconds``.  When a segment would
    exceed the limit, the pending chunk is sealed and a new one begins with
    that segment.

    Oversized segments (duration > ``max_chunk_seconds * 1000 ms``) are split
    into consecutive sub-chunks via a hard-cut fallback before the greedy pass.
    """

    @property
    def name(self) -> str:
        """Human-readable stage name."""
        return "chunking"

    def process(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run the chunking stage and return the (possibly updated) context.

        Returns *ctx* unchanged when the stage is disabled:
        - ``ctx.config.chunking`` is ``None``, or
        - ``ctx.config.chunking.enabled`` is ``False``.

        When enabled, applies greedy accumulation over ``ctx.vad_segments``,
        then expands each chunk's boundaries by ``config.chunking.silence_pad_ms``
        (clamped to the audio bounds), and returns a new ``PipelineContext``
        with ``chunks`` populated.

        Args:
            ctx: The current pipeline context carrying ``vad_segments`` and
                configuration.

        Returns:
            A ``PipelineContext`` with ``chunks`` populated when enabled, or
            the original *ctx* when disabled.
        """
        chunking_cfg = ctx.config.chunking
        if chunking_cfg is None or not chunking_cfg.enabled:
            logger.debug("ChunkingStage disabled, returning ctx unchanged")
            return ctx

        max_ms = chunking_cfg.max_chunk_seconds * 1000

        # Pre-process segments: expand oversized ones into sub-chunk items.
        items: list[_SegmentItem] = []
        for seg in ctx.vad_segments:
            if (seg.end_ms - seg.start_ms) > max_ms:
                logger.debug(
                    "ChunkingStage expanding oversized segment",
                    start_ms=seg.start_ms,
                    end_ms=seg.end_ms,
                    max_ms=max_ms,
                )
                items.extend(_expand_oversized(seg, max_ms))
            else:
                items.append(_SegmentItem(seg.start_ms, seg.end_ms, [seg]))

        chunks = _greedy_accumulate(items, chunking_cfg.max_chunk_seconds)

        logger.debug(
            "ChunkingStage produced chunks",
            num_chunks=len(chunks),
            num_input_segments=len(ctx.vad_segments),
        )

        chunks = _apply_silence_pad(
            chunks, chunking_cfg.silence_pad_ms, ctx.media_info.duration_ms
        )

        return dataclasses.replace(ctx, chunks=chunks)


def _expand_oversized(segment: VadSegment, max_ms: int) -> list[_SegmentItem]:
    """Split an oversized segment into consecutive sub-chunk items.

    Emits sub-chunks of exactly *max_ms* each, except the final sub-chunk
    which may be shorter.  Each sub-chunk carries the original *segment* as
    its sole ``source_segments`` entry.

    The condition for "oversized" is ``(segment.end_ms - segment.start_ms) > max_ms``.
    This helper assumes the caller has already verified that condition.

    Args:
        segment: The ``VadSegment`` to split.
        max_ms: Maximum duration in milliseconds for each sub-chunk
            (equals ``max_chunk_seconds * 1000``).

    Returns:
        A non-empty list of ``_SegmentItem`` tuples covering the full span of
        *segment* with no gap and no overlap.
    """
    items: list[_SegmentItem] = []
    i = 0
    while True:
        sub_start = segment.start_ms + i * max_ms
        sub_end = min(segment.start_ms + (i + 1) * max_ms, segment.end_ms)
        items.append(_SegmentItem(sub_start, sub_end, [segment]))
        logger.debug(
            "_expand_oversized emitting sub-chunk",
            sub_chunk_index=i,
            sub_start=sub_start,
            sub_end=sub_end,
        )
        if sub_end >= segment.end_ms:
            break
        i += 1
    return items


def _apply_silence_pad(
    chunks: list[Chunk],
    silence_pad_ms: int,
    duration_ms: int,
) -> list[Chunk]:
    """Expand each chunk's boundaries by *silence_pad_ms* milliseconds.

    Applies a post-pass over all sealed chunks, independently expanding each
    one:

    - ``start_ms`` is decreased by *silence_pad_ms*, clamped to ``0``.
    - ``end_ms`` is increased by *silence_pad_ms*, clamped to *duration_ms*.

    When *silence_pad_ms* is ``0`` the operation is a no-op and the original
    list is returned unchanged.

    Args:
        chunks: The sealed list of ``Chunk`` objects produced by the greedy
            accumulation pass.
        silence_pad_ms: Number of milliseconds to add around each chunk
            boundary.  Must be non-negative (validated by ``ChunkingConfig``).
        duration_ms: Total duration of the source audio in milliseconds, used
            as the upper clamp for ``end_ms``.

    Returns:
        A new list of ``Chunk`` objects with expanded (and clamped) boundaries.
        Source-segment lists and chunk indices are preserved unchanged.
    """
    if silence_pad_ms == 0:
        return chunks

    padded: list[Chunk] = []
    for chunk in chunks:
        new_start = max(0, chunk.start_ms - silence_pad_ms)
        new_end = min(duration_ms, chunk.end_ms + silence_pad_ms)
        logger.debug(
            "_apply_silence_pad expanding chunk",
            chunk_index=chunk.index,
            original_start_ms=chunk.start_ms,
            original_end_ms=chunk.end_ms,
            new_start_ms=new_start,
            new_end_ms=new_end,
            silence_pad_ms=silence_pad_ms,
            duration_ms=duration_ms,
        )
        padded.append(
            dataclasses.replace(
                chunk,
                start_ms=new_start,
                end_ms=new_end,
            )
        )
    return padded


def _greedy_accumulate(
    items: list[_SegmentItem],
    max_chunk_seconds: int,
) -> list[Chunk]:
    """Group *items* into chunks using greedy left-to-right accumulation.

    An item is added to the current pending chunk when::

        (item.end_ms - pending_start_ms) / 1000 <= max_chunk_seconds

    When the next item would exceed the limit, the pending chunk is sealed
    and a new one is started with that item.  The final pending chunk is
    always sealed after all items are processed.

    Args:
        items: Ordered list of ``_SegmentItem`` objects to group.  Each item
            carries its own ``source_segments`` list (one entry for normal
            segments, one entry pointing to the original segment for hard-cut
            sub-chunks).
        max_chunk_seconds: Maximum allowed duration in seconds for any single
            chunk, measured from the first item's ``start_ms`` to the last
            item's ``end_ms`` within the chunk.

    Returns:
        A list of ``Chunk`` objects with zero-based contiguous ``index`` values.
        Returns an empty list when *items* is empty.
    """
    chunks: list[Chunk] = []

    pending_start: int | None = None
    pending_end: int | None = None
    pending_segs: list[VadSegment] = []

    for item in items:
        if pending_start is None:
            # Start a new pending chunk with this item.
            pending_start = item.start_ms
            pending_end = item.end_ms
            pending_segs = list(item.source_segments)
        elif (item.end_ms - pending_start) / 1000 > max_chunk_seconds:
            # Adding this item would exceed the limit — seal the pending chunk.
            assert pending_end is not None  # guaranteed when pending_start is set
            logger.debug(
                "_greedy_accumulate sealing chunk",
                chunk_index=len(chunks),
                start_ms=pending_start,
                end_ms=pending_end,
                num_segments=len(pending_segs),
            )
            chunks.append(
                Chunk(
                    index=len(chunks),
                    start_ms=pending_start,
                    end_ms=pending_end,
                    source_segments=list(pending_segs),
                )
            )
            # Begin a new pending chunk with the current item.
            pending_start = item.start_ms
            pending_end = item.end_ms
            pending_segs = list(item.source_segments)
        else:
            # Extend the pending chunk.
            pending_end = item.end_ms
            pending_segs.extend(item.source_segments)

    if pending_start is not None:
        assert pending_end is not None  # guaranteed when pending_start is set
        logger.debug(
            "_greedy_accumulate sealing final chunk",
            chunk_index=len(chunks),
            start_ms=pending_start,
            end_ms=pending_end,
            num_segments=len(pending_segs),
        )
        chunks.append(
            Chunk(
                index=len(chunks),
                start_ms=pending_start,
                end_ms=pending_end,
                source_segments=list(pending_segs),
            )
        )

    return chunks
