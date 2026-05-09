"""Baseline persistence for the regression harness.

Realises the **Decision: BaselineStore is a Protocol with a JSON
implementation** and the **Decision: Implementation Contract — Baseline
JSON format** from the ``regression-runner`` change's ``design.md``.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from talking_parrot.shared import CueDiff, MetricBundle, ScoreCard

_SCHEMA_VERSION = 1
_logger = logging.getLogger("talking_parrot.regression.baseline")


class BaselineSchemaError(Exception):
    """Raised when an on-disk baseline file declares an unknown schema."""


@runtime_checkable
class BaselineStore(Protocol):
    """Persistence port for per-sample :class:`ScoreCard` baselines.

    Implementations MUST persist a ``ScoreCard`` keyed by ``sample_id``
    such that ``load`` returns an equal-by-value ``ScoreCard`` after a
    prior ``save``. ``load`` MUST return ``None`` when no baseline has
    been saved for ``sample_id``.
    """

    def load(self, sample_id: str) -> ScoreCard | None:
        """Return the saved :class:`ScoreCard` for ``sample_id`` or ``None``."""
        ...

    def save(self, sample_id: str, card: ScoreCard) -> None:
        """Persist ``card`` under the key ``sample_id``."""
        ...


def _serialise_score_card(
    card: ScoreCard,
    *,
    sample_id: str,
    variant_file: str,
    captured_at: str,
    label: str | None,
) -> dict:
    """Serialise ``card`` into the schema-v1 dict shape.

    ``cue_diffs`` is always emitted (empty list when none).
    """
    return {
        "schema_version": _SCHEMA_VERSION,
        "sample_id": sample_id,
        "variant_file": variant_file,
        "captured_at": captured_at,
        "label": label,
        "score_card": {
            "sample_id": card.sample_id,
            "overall_score": card.overall_score,
            "metric_bundle": {
                "cer": card.metric_bundle.cer,
                "confidence_mean": card.metric_bundle.confidence_mean,
                "confidence_p10": card.metric_bundle.confidence_p10,
                "repetition_ratio_mean": card.metric_bundle.repetition_ratio_mean,
                "no_speech_prob_mean": card.metric_bundle.no_speech_prob_mean,
            },
            "cue_diffs": [
                {
                    "index": d.index,
                    "reference_text": d.reference_text,
                    "hypothesis_text": d.hypothesis_text,
                    "cer": d.cer,
                    "start_ms_delta": d.start_ms_delta,
                    "end_ms_delta": d.end_ms_delta,
                }
                for d in card.cue_diffs
            ],
        },
    }


def _deserialise_score_card(payload: dict) -> ScoreCard:
    """Inverse of :func:`_serialise_score_card`. Raises on unknown schema."""
    raw_version = payload.get("schema_version")
    if raw_version != _SCHEMA_VERSION:
        raise BaselineSchemaError(
            f"unknown baseline schema_version={raw_version!r}; expected {_SCHEMA_VERSION}"
        )
    sc = payload["score_card"]
    mb = sc["metric_bundle"]
    metric_bundle = MetricBundle(
        cer=float(mb["cer"]),
        confidence_mean=float(mb["confidence_mean"]),
        confidence_p10=float(mb["confidence_p10"]),
        repetition_ratio_mean=float(mb["repetition_ratio_mean"]),
        no_speech_prob_mean=float(mb["no_speech_prob_mean"]),
    )
    cue_diffs = [
        CueDiff(
            index=int(d["index"]),
            reference_text=str(d["reference_text"]),
            hypothesis_text=str(d["hypothesis_text"]),
            cer=float(d["cer"]),
            start_ms_delta=int(d["start_ms_delta"]),
            end_ms_delta=int(d["end_ms_delta"]),
        )
        for d in sc.get("cue_diffs", [])
    ]
    return ScoreCard(
        sample_id=str(sc["sample_id"]),
        overall_score=float(sc["overall_score"]),
        metric_bundle=metric_bundle,
        cue_diffs=cue_diffs,
    )


class JsonBaselineStore:
    """JSON file-backed :class:`BaselineStore`.

    Each baseline is written to ``<root_dir>/<sample_id>/baseline.json``
    atomically via tempfile + :func:`os.replace`. ``load`` returns
    ``None`` for missing files and raises :class:`BaselineSchemaError`
    for unknown ``schema_version``.
    """

    def __init__(
        self,
        root_dir: Path,
        *,
        captured_at: str = "",
        label: str | None = None,
        variant_file: str = "",
    ) -> None:
        """Construct a store rooted at ``root_dir``.

        ``captured_at``, ``label``, and ``variant_file`` are recorded in
        each saved baseline document. Tests typically pass fixed values
        for determinism.
        """
        self._root_dir = Path(root_dir)
        self._captured_at = captured_at
        self._label = label
        self._variant_file = variant_file

    def _path_for(self, sample_id: str) -> Path:
        return self._root_dir / sample_id / "baseline.json"

    def load(self, sample_id: str) -> ScoreCard | None:
        """Return the persisted card for ``sample_id`` or ``None``."""
        path = self._path_for(sample_id)
        _logger.debug("baseline.load path=%s", path)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        assert isinstance(payload, dict), (
            f"baseline file {path} did not deserialise to a dict — "
            "stdlib json contract may have changed"
        )
        return _deserialise_score_card(payload)

    def save(self, sample_id: str, card: ScoreCard) -> None:
        """Atomically write ``card`` to ``<root>/<sample_id>/baseline.json``."""
        path = self._path_for(sample_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _serialise_score_card(
            card,
            sample_id=sample_id,
            variant_file=self._variant_file,
            captured_at=self._captured_at,
            label=self._label,
        )
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        _logger.debug("baseline.save path=%s bytes=%d", path, len(text))
        # Atomic: write to sibling tempfile in the same directory then replace.
        fd, tmp_name = tempfile.mkstemp(
            prefix="baseline-", suffix=".json.tmp", dir=str(path.parent)
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp_path, path)
        except Exception:
            # Best-effort cleanup if replace failed.
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            raise


__all__ = [
    "BaselineSchemaError",
    "BaselineStore",
    "JsonBaselineStore",
]
