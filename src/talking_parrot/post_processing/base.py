"""Abstract base class for post-processing operators.

See spec ``subtitle-processor`` and design decisions D2 / D3 of
``implement-post-processing-stage``.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import TYPE_CHECKING

from talking_parrot.models.subtitle import Subtitle

if TYPE_CHECKING:
    from talking_parrot.config.models import PostProcessingConfig
    from talking_parrot.models.transcription import AlignedToken


class SubtitleProcessor(abc.ABC):
    """Pure transformation from one ``Subtitle`` sequence to another.

    Concrete implementations MUST be side-effect-free: they neither mutate the
    input list nor any input ``Subtitle`` instance, and they always return a
    newly constructed list (D2). They also handle the empty-input case by
    returning an empty list.
    """

    @abc.abstractmethod
    def process(
        self, subtitles: list[Subtitle], config: "PostProcessingConfig"
    ) -> list[Subtitle]:
        """Run the transformation and return a new list of subtitles."""


def _renumber(subs: list[Subtitle]) -> list[Subtitle]:
    """Return a new list with ``index`` reset to ``1..len(subs)``.

    This helper is used by every concrete processor to honor the SRT contract
    that subtitle indices are contiguous and 1-based.
    """
    return [dataclasses.replace(s, index=i + 1) for i, s in enumerate(subs)]


def _with_token_map(
    new_subs: list[Subtitle],
    parent_map: dict[int, list["AlignedToken"]],
    child_to_parents: dict[int, list[int]] | None = None,
    per_child_tokens: dict[int, list["AlignedToken"]] | None = None,
) -> dict[int, list["AlignedToken"]]:
    """Aggregate a parent token map onto a new (post-transform) subtitle list.

    Two modes (D3):

    1. ``child_to_parents`` — each child cue's tokens are the concatenation of
       the parent cues' tokens (used for merge).
    2. ``per_child_tokens`` — explicit per-child token slices (used for split).

    Exactly one of ``child_to_parents`` / ``per_child_tokens`` MUST be
    provided.

    The returned dict is keyed by ``Subtitle.index`` of ``new_subs``.
    """
    if (child_to_parents is None) == (per_child_tokens is None):
        raise ValueError(
            "_with_token_map requires exactly one of "
            "child_to_parents / per_child_tokens"
        )

    out: dict[int, list["AlignedToken"]] = {}
    if per_child_tokens is not None:
        for sub in new_subs:
            out[sub.index] = list(per_child_tokens.get(sub.index, []))
        return out

    assert child_to_parents is not None  # for type checkers
    for sub in new_subs:
        parents = child_to_parents.get(sub.index, [])
        aggregated: list["AlignedToken"] = []
        for parent_idx in parents:
            aggregated.extend(parent_map.get(parent_idx, []))
        out[sub.index] = aggregated
    return out
