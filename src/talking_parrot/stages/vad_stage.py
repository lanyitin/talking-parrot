"""VADStage — Voice Activity Detection pipeline stage.

Coordinates one or more ``VADBackend`` instances to produce a list of
``VadSegment`` objects from raw PCM audio.

Processing pipeline within the stage:
1. Run each backend's ``analyze()`` on the pipeline audio bytes.
2. Align per-frame probabilities from all backends onto a unified timeline
   using nearest-neighbour matching with a 50 ms tolerance window.
3. Compute a composite score for each unified frame via ``FormulaEvaluator``.
4. Apply a two-threshold hysteresis state machine to merge frames into raw
   speech segments.
5. Apply post-merge refinement: gap merging, short-segment filtering,
   long-segment splitting, and speech padding.
6. Compute per-segment statistics (mean probabilities) and return
   ``VadSegment`` objects.
"""

from __future__ import annotations

import bisect
import dataclasses
from typing import TYPE_CHECKING

import structlog

from talking_parrot.stages.base import PipelineStage

from talking_parrot.models.vad import RawVadFrame

if TYPE_CHECKING:
    from talking_parrot.expression.formula import FormulaEvaluator
    from talking_parrot.io.audio_reader import AudioReader
    from talking_parrot.models.context import PipelineContext
    from talking_parrot.models.vad import VadSegment
    from talking_parrot.vad.backend import VADBackend

logger = structlog.get_logger(__name__)


class VADStage(PipelineStage):
    """Pipeline stage that detects speech segments using VAD backends.

    Args:
        backends: List of ``VADBackend`` instances to run in parallel. Their
            per-frame probabilities are aligned and merged by this stage.
        formula_evaluator: A ``FormulaEvaluator`` used to compute the
            composite score per unified frame.
    """

    def __init__(
        self,
        backends: list["VADBackend"],
        formula_evaluator: "FormulaEvaluator",
        audio_reader: "AudioReader",
    ) -> None:
        """Initialise VADStage with its backends and formula evaluator.

        Args:
            backends: Ordered list of VAD backends to run.
            formula_evaluator: Evaluator for the composite score formula.
            audio_reader: Source of raw PCM bytes; ``read(0, duration_ms)``
                supplies audio to every backend's ``analyze``.
        """
        self._backends = backends
        self._formula_evaluator = formula_evaluator
        self._audio_reader = audio_reader

    @property
    def name(self) -> str:
        """Human-readable stage name."""
        return "vad"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def process(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run VAD on the pipeline context and return updated context.

        Returns *ctx* unchanged if ``ctx.config.vad`` is ``None`` or if
        ``ctx.config.vad.enabled`` is ``False``.

        Args:
            ctx: The current pipeline context.

        Returns:
            A new ``PipelineContext`` with ``vad_segments`` populated, or the
            original *ctx* if the stage is disabled.
        """
        vad_cfg = ctx.config.vad
        if vad_cfg is None or not vad_cfg.enabled:
            logger.debug("VADStage is disabled — returning context unchanged")
            return ctx

        logger.debug("VADStage processing", num_backends=len(self._backends))

        audio_data = self._audio_reader.read(0, ctx.media_info.duration_ms)
        sample_rate = self._audio_reader.sample_rate

        backend_frames: dict[str, list["RawVadFrame"]] = {}
        for backend in self._backends:
            logger.debug(
                "calling VADBackend.analyze",
                backend_name=backend.name,
                audio_len=len(audio_data),
                sample_rate=sample_rate,
            )
            frames = backend.analyze(audio_data, sample_rate)
            logger.debug(
                "VADBackend.analyze returned",
                backend_name=backend.name,
                result_type=type(frames).__name__,
                result_summary=repr(frames)[:200],
            )
            assert isinstance(frames, list), (
                f"VADBackend({backend.name!r}).analyze() returned "
                f"{type(frames)!r}, expected list. "
                "Check whether the backend implementation is correct."
            )
            backend_frames[backend.name] = frames

        # Build the tagged per-backend frame list now (frames already carry
        # their backend tag from each ``VADBackend.analyze``). This is the
        # foundation of ``ctx.vad_frames`` regardless of how alignment turns
        # out below.
        tagged_frames: list["RawVadFrame"] = []
        for name, frames in backend_frames.items():
            for frame in frames:
                # Every real backend tags its own frames; defensively replace
                # any mistagged frame with one carrying the configured name.
                if frame.backend == name:
                    tagged_frames.append(frame)
                else:
                    tagged_frames.append(dataclasses.replace(frame, backend=name))

        if not any(backend_frames.values()):
            # No frames at all — return empty segments and empty vad_frames.
            return dataclasses.replace(ctx, vad_segments=[], vad_frames=[])

        # Step 2: align frames onto a unified timeline
        aligned = self._align_frames(backend_frames)

        if not aligned:
            return dataclasses.replace(ctx, vad_segments=[], vad_frames=tagged_frames)

        # Step 3: compute composite score per unified frame
        backend_names = [b.name for b in self._backends]
        for point in aligned:
            variables = {
                f"{name}_prob": point.get(f"{name}_prob", 0.0) for name in backend_names
            }
            logger.debug(
                "calling FormulaEvaluator.evaluate",
                formula=vad_cfg.formula,
                variables=variables,
            )
            score = self._formula_evaluator.evaluate(vad_cfg.formula, variables)
            logger.debug(
                "FormulaEvaluator.evaluate returned",
                result_type=type(score).__name__,
                result_summary=repr(score)[:200],
            )
            assert isinstance(score, (int, float)), (
                f"FormulaEvaluator.evaluate() returned {type(score)!r}, "
                "expected int or float. Check the formula."
            )
            point["composite_score"] = float(score)

        # Append synthetic composite-backend frames — one per unified time
        # point — to the tagged frame list so downstream consumers (writer,
        # GUI) see the composite timeline as a first-class series.
        for point in aligned:
            tagged_frames.append(
                RawVadFrame(
                    time_ms=int(point["time_ms"]),
                    prob=float(point["composite_score"]),
                    backend="composite",
                )
            )

        # Determine frame duration for hysteresis (use median gap or default 16ms)
        frame_duration_ms = _estimate_frame_duration(aligned)

        # Step 4: hysteresis-based segment merging
        raw_segments = self._hysteresis_merge(
            aligned,
            activity_threshold=vad_cfg.activity_threshold,
            neg_threshold=vad_cfg.neg_threshold,
            frame_duration_ms=frame_duration_ms,
        )

        # Step 5: post-merge refinement (in order)
        audio_duration_ms = ctx.media_info.duration_ms

        segments = self._merge_gaps(raw_segments, vad_cfg.min_silence_duration_ms)
        segments = self._filter_short_segments(segments, vad_cfg.min_speech_duration_ms)
        segments = self._split_long_segments(segments, vad_cfg.max_speech_duration_ms)
        segments = self._apply_padding(
            segments, vad_cfg.speech_pad_ms, audio_duration_ms
        )

        # Step 6: build VadSegment objects with per-segment statistics
        vad_segments: list["VadSegment"] = [
            self._compute_segment_stats(
                start_ms=start,
                end_ms=end,
                frames=[pt for pt in aligned if start <= pt["time_ms"] < end],
                backend_names=backend_names,
            )
            for start, end in segments
        ]

        return dataclasses.replace(
            ctx, vad_segments=vad_segments, vad_frames=tagged_frames
        )

    # ------------------------------------------------------------------
    # Step 2: Frame alignment
    # ------------------------------------------------------------------

    def _align_frames(
        self,
        backend_frames: dict[str, list["RawVadFrame"]],
    ) -> list[dict]:
        """Build a unified timeline by nearest-neighbour alignment.

        For each time point in the union of all backend frame ``time_ms``
        values, the probability from a given backend is the ``prob`` of its
        closest frame within a 50 ms tolerance window.  If no frame falls
        within tolerance, the probability defaults to ``0.0``.

        Args:
            backend_frames: Mapping from backend name to its list of frames.

        Returns:
            List of dicts with keys ``time_ms`` and ``{name}_prob`` for each
            backend, sorted by ascending ``time_ms``.
        """
        _TOLERANCE_MS = 50

        # Collect all unique time points
        all_times: set[int] = set()
        for frames in backend_frames.values():
            for frame in frames:
                all_times.add(frame.time_ms)

        # Pre-build sorted time_ms index per backend for O(log n) lookup.
        # Frames are already in ascending time order (produced sequentially
        # by each backend), so no extra sort is needed.
        backend_times: dict[str, list[int]] = {
            name: [f.time_ms for f in frames]
            for name, frames in backend_frames.items()
        }

        aligned: list[dict] = []
        for t in sorted(all_times):
            point: dict = {"time_ms": t}
            for name, frames in backend_frames.items():
                if not frames:
                    point[f"{name}_prob"] = 0.0
                    continue
                times = backend_times[name]
                pos = bisect.bisect_left(times, t)
                candidates = []
                if pos > 0:
                    candidates.append(frames[pos - 1])
                if pos < len(frames):
                    candidates.append(frames[pos])
                nearest = min(candidates, key=lambda f: abs(f.time_ms - t))
                if abs(nearest.time_ms - t) <= _TOLERANCE_MS:
                    point[f"{name}_prob"] = nearest.prob
                else:
                    point[f"{name}_prob"] = 0.0
            aligned.append(point)

        return aligned

    # ------------------------------------------------------------------
    # Step 4: Hysteresis-based segment merging
    # ------------------------------------------------------------------

    def _hysteresis_merge(
        self,
        frames: list[dict],
        activity_threshold: float,
        neg_threshold: float,
        frame_duration_ms: int = 16,
    ) -> list[tuple[int, int]]:
        """Merge frames into raw speech segments using a two-threshold state machine.

        Transitions:
        - SILENCE → SPEECH when ``composite_score >= activity_threshold``
        - SPEECH → SILENCE when ``composite_score < neg_threshold``

        Args:
            frames: Aligned frames with ``time_ms`` and ``composite_score``.
            activity_threshold: Score threshold to start a speech segment.
            neg_threshold: Score threshold to end a speech segment.
            frame_duration_ms: Estimated duration of one frame in ms; used to
                compute the end time of the last active frame.

        Returns:
            List of ``(start_ms, end_ms)`` tuples representing raw segments.
        """
        _SILENCE = "SILENCE"
        _SPEECH = "SPEECH"

        state = _SILENCE
        seg_start: int | None = None
        segments: list[tuple[int, int]] = []

        for frame in frames:
            score = frame.get("composite_score", 0.0)
            t = frame["time_ms"]

            if state == _SILENCE:
                if score >= activity_threshold:
                    state = _SPEECH
                    seg_start = t
            else:  # state == _SPEECH
                if score < neg_threshold:
                    # End segment at the previous frame boundary
                    assert seg_start is not None
                    segments.append((seg_start, t))
                    state = _SILENCE
                    seg_start = None

        # Close any open segment at the last frame
        if state == _SPEECH and seg_start is not None:
            last_t = frames[-1]["time_ms"]
            segments.append((seg_start, last_t + frame_duration_ms))

        return segments

    # ------------------------------------------------------------------
    # Step 5: Post-merge refinement
    # ------------------------------------------------------------------

    def _merge_gaps(
        self,
        segments: list[tuple[int, int]],
        min_silence_duration_ms: int,
    ) -> list[tuple[int, int]]:
        """Merge adjacent segments whose silence gap is strictly less than the threshold.

        Args:
            segments: List of ``(start_ms, end_ms)`` tuples (sorted ascending).
            min_silence_duration_ms: Gaps strictly smaller than this value are merged.

        Returns:
            New list of merged ``(start_ms, end_ms)`` tuples.
        """
        if not segments:
            return []

        merged: list[tuple[int, int]] = [segments[0]]
        for start, end in segments[1:]:
            prev_start, prev_end = merged[-1]
            gap = start - prev_end
            if gap < min_silence_duration_ms:
                merged[-1] = (prev_start, end)
            else:
                merged.append((start, end))
        return merged

    def _filter_short_segments(
        self,
        segments: list[tuple[int, int]],
        min_speech_duration_ms: int,
    ) -> list[tuple[int, int]]:
        """Discard segments shorter than ``min_speech_duration_ms``.

        Args:
            segments: List of ``(start_ms, end_ms)`` tuples.
            min_speech_duration_ms: Segments with duration strictly less than
                this value (i.e. ``end - start < min``) are discarded. Segments
                with duration equal to the minimum are kept.

        Returns:
            Filtered list of ``(start_ms, end_ms)`` tuples.
        """
        return [
            (start, end)
            for start, end in segments
            if (end - start) >= min_speech_duration_ms
        ]

    def _split_long_segments(
        self,
        segments: list[tuple[int, int]],
        max_speech_duration_ms: int,
    ) -> list[tuple[int, int]]:
        """Split segments longer than ``max_speech_duration_ms`` at the midpoint.

        Splitting is applied recursively until all segments meet the constraint.

        Args:
            segments: List of ``(start_ms, end_ms)`` tuples.
            max_speech_duration_ms: Maximum allowed segment duration in ms.

        Returns:
            New list of ``(start_ms, end_ms)`` tuples where no segment exceeds
            the maximum duration.
        """
        result: list[tuple[int, int]] = []
        for start, end in segments:
            duration = end - start
            if duration > max_speech_duration_ms:
                mid = start + duration // 2
                result.append((start, mid))
                result.append((mid, end))
            else:
                result.append((start, end))
        return result

    def _apply_padding(
        self,
        segments: list[tuple[int, int]],
        speech_pad_ms: int,
        audio_duration_ms: int,
    ) -> list[tuple[int, int]]:
        """Extend each segment by ``speech_pad_ms`` on both sides, clamped to audio bounds.

        Args:
            segments: List of ``(start_ms, end_ms)`` tuples.
            speech_pad_ms: Milliseconds to add before and after each segment.
            audio_duration_ms: Total audio duration in ms; caps the segment end.

        Returns:
            New list of padded and clamped ``(start_ms, end_ms)`` tuples.
        """
        return [
            (
                max(0, start - speech_pad_ms),
                min(audio_duration_ms, end + speech_pad_ms),
            )
            for start, end in segments
        ]

    # ------------------------------------------------------------------
    # Step 6: Segment statistics
    # ------------------------------------------------------------------

    def _compute_segment_stats(
        self,
        start_ms: int,
        end_ms: int,
        frames: list[dict],
        backend_names: list[str],
    ) -> "VadSegment":
        """Compute per-segment statistics and return a ``VadSegment``.

        Statistics are the mean of each backend's probability and the mean
        of the composite scores across the segment's aligned frames.

        Args:
            start_ms: Segment start in milliseconds.
            end_ms: Segment end in milliseconds.
            frames: Aligned frame dicts covering this segment.
            backend_names: Ordered list of backend name strings.

        Returns:
            A ``VadSegment`` with populated ``ten_vad_prob``,
            ``silero_vad_prob``, and ``composite_score`` fields.
        """
        from talking_parrot.models.vad import VadSegment

        def _mean(values: list[float]) -> float:
            """Return the mean of *values*, or 0.0 if the list is empty."""
            return sum(values) / len(values) if values else 0.0

        ten_vad_probs = [f.get("ten_vad_prob", 0.0) for f in frames]
        silero_vad_probs = [f.get("silero_vad_prob", 0.0) for f in frames]
        composite_scores = [f.get("composite_score", 0.0) for f in frames]

        return VadSegment(
            start_ms=start_ms,
            end_ms=end_ms,
            ten_vad_prob=_mean(ten_vad_probs),
            silero_vad_prob=_mean(silero_vad_probs),
            composite_score=_mean(composite_scores),
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _estimate_frame_duration(aligned: list[dict]) -> int:
    """Estimate the typical frame duration in milliseconds.

    Uses the first gap between consecutive frames, falling back to 16 ms if
    fewer than two frames exist.

    Args:
        aligned: List of aligned frame dicts with a ``time_ms`` key.

    Returns:
        Estimated frame duration in milliseconds.
    """
    if len(aligned) < 2:
        return 16
    return aligned[1]["time_ms"] - aligned[0]["time_ms"]
