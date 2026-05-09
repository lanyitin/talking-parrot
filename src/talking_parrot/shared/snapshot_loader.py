"""Loader abstraction for materialising a ``ProjectSnapshot`` from a source.

``SnapshotLoader`` is a structural protocol so tests and downstream code can
substitute fixtures or alternative sources without inheriting from a base
class. ``FileSnapshotLoader`` is the default file-backed implementation that
reads a ``.tp`` JSON file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import fields
from pathlib import Path
from typing import Protocol, runtime_checkable

from talking_parrot.models.chunk import Chunk
from talking_parrot.models.subtitle import Subtitle
from talking_parrot.models.transcription import (
    AlignedToken,
    TranscriptionMetrics,
    TranscriptionResult,
)
from talking_parrot.models.vad import RawVadFrame, VadSegment
from talking_parrot.shared.project_snapshot import AudioInfo, ProjectSnapshot

_REQUIRED_SCALAR_FIELDS = (
    "version",
    "created_at",
    "source_path",
    "config_snapshot",
    "audio_info",
)
_OPTIONAL_LIST_FIELDS = (
    "vad_frames",
    "vad_segments",
    "chunks",
    "transcription_results",
    "pre_postprocess_subtitles",
    "subtitles",
)

_logger = logging.getLogger(__name__)


@runtime_checkable
class SnapshotLoader(Protocol):
    """Structural protocol for any object that can load a ``ProjectSnapshot``."""

    def load(self, source: str | Path) -> ProjectSnapshot:
        """Load a snapshot from the given source."""
        ...


class FileSnapshotLoader:
    """Default file-backed loader that reads a ``.tp`` JSON file from disk."""

    def load(self, source: str | Path) -> ProjectSnapshot:
        """Read the file at ``source`` and return a fully populated snapshot.

        Raises:
            FileNotFoundError: ``source`` does not exist (propagated unchanged).
            json.JSONDecodeError: ``source`` is not valid JSON (propagated
                unchanged).
            KeyError: A required scalar field is missing from the JSON; the
                error message names the missing field.
        """
        path = Path(source)
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)

        for required in _REQUIRED_SCALAR_FIELDS:
            if required not in payload:
                raise KeyError(required)

        list_kwargs: dict[str, list] = {}
        for list_field in _OPTIONAL_LIST_FIELDS:
            if list_field in payload:
                list_kwargs[list_field] = _decode_list(
                    list_field, payload[list_field], path
                )
            else:
                _logger.debug(
                    "snapshot field %r missing on disk; defaulting to []", list_field
                )
                list_kwargs[list_field] = []

        return ProjectSnapshot(
            version=str(payload["version"]),
            created_at=str(payload["created_at"]),
            source_path=str(payload["source_path"]),
            config_snapshot=dict(payload["config_snapshot"]),
            audio_info=_decode_audio_info(payload["audio_info"]),
            **list_kwargs,
        )


def _decode_audio_info(raw: dict) -> AudioInfo:
    return AudioInfo(**{f.name: raw[f.name] for f in fields(AudioInfo)})


def _decode_list(field_name: str, raw: list, source_path: Path | None = None) -> list:
    """Decode a JSON list payload into the typed ``ProjectSnapshot`` list field.

    The ``source_path`` is used only by the ``vad_frames`` legacy fallback so
    that the warning message can name the file being loaded.
    """
    if field_name == "vad_frames":
        decoded: list[RawVadFrame] = []
        legacy_count = 0
        for item in raw:
            if "backend" not in item:
                legacy_count += 1
                decoded.append(RawVadFrame(**item, backend="unknown"))
            else:
                decoded.append(RawVadFrame(**item))
        if legacy_count > 0:
            _logger.warning(
                "%s: legacy vad_frames without 'backend' tag — %d "
                "frame(s) defaulted to backend='unknown'",
                source_path,
                legacy_count,
            )
        return decoded
    if field_name == "vad_segments":
        return [VadSegment(**item) for item in raw]
    if field_name == "chunks":
        return [_decode_chunk(item) for item in raw]
    if field_name == "transcription_results":
        return [_decode_transcription_result(item) for item in raw]
    if field_name in ("pre_postprocess_subtitles", "subtitles"):
        return [Subtitle(**item) for item in raw]
    return list(raw)


def _decode_chunk(item: dict) -> Chunk:
    source_segments = [VadSegment(**seg) for seg in item.get("source_segments", [])]
    return Chunk(
        index=item["index"],
        start_ms=item["start_ms"],
        end_ms=item["end_ms"],
        source_segments=source_segments,
    )


def _decode_transcription_result(item: dict) -> TranscriptionResult:
    metrics = TranscriptionMetrics(**item["metrics"])
    aligned_tokens_raw = item.get("aligned_tokens")
    aligned_tokens: list[AlignedToken] | None = (
        [AlignedToken(**tok) for tok in aligned_tokens_raw]
        if aligned_tokens_raw is not None
        else None
    )
    return TranscriptionResult(
        chunk_index=item["chunk_index"],
        start_ms=item["start_ms"],
        end_ms=item["end_ms"],
        text=item["text"],
        language=item["language"],
        model_used=item["model_used"],
        metrics=metrics,
        aligned_tokens=aligned_tokens,
    )
