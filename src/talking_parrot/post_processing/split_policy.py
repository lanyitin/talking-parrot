"""Split-boundary policies used by the cue-split processors.

Spec: ``split-boundary-policy`` (change ``japanese-aware-cue-split``).

A :class:`SplitBoundaryPolicy` is a structural type with a single method,
:meth:`SplitBoundaryPolicy.adjust`, that the cue-split processors call
after computing a linearly-interpolated candidate index.  Implementations
return the actual character index at which the cue should be sliced.

The default implementation, :class:`LinearSplitBoundaryPolicy`, is a no-op
that returns the candidate unchanged — preserving the historical
linear-interpolation behaviour for non-Japanese pipelines.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SplitBoundaryPolicy(Protocol):
    """Structural type for objects that adjust a cue split index.

    Implementations are dependency-injected into
    :class:`CharacterBoundarySplitProcessor` and
    :class:`TimeBasedSplitProcessor` so the processors stay
    language-agnostic.
    """

    def adjust(self, text: str, candidate_index: int, search_radius: int) -> int:
        """Return the character index at which to slice ``text``.

        Args:
            text: The cue's text. Implementations MUST NOT mutate it.
            candidate_index: The linearly-interpolated candidate index
                produced by the calling processor. Always in
                ``[1, len(text) - 1]`` when called by the processors.
            search_radius: Half-width (in characters) of the window the
                policy is permitted to search around ``candidate_index``.

        Returns:
            An integer in ``[1, len(text) - 1]``.
        """
        ...

    def is_valid(self, text: str, index: int) -> bool:
        """Return whether ``index`` is a non-forbidden cut point inside ``text``.

        Implementations MUST be pure and MUST NOT mutate ``text``.
        Contract: if ``is_valid(text, i)`` is True then ``adjust(text, i, 0)``
        SHALL return ``i`` (radius-0 fixed point).

        Args:
            text: The cue's text. Implementations MUST NOT mutate it.
            index: A candidate split index. Callers SHALL clamp to
                ``[1, len(text) - 1]`` before calling; behaviour outside
                that range is unspecified.

        Returns:
            ``True`` when cutting between ``text[index - 1]`` and
            ``text[index]`` is permitted by the policy's rules,
            ``False`` otherwise.
        """
        ...


class LinearSplitBoundaryPolicy:
    """No-op policy that returns the candidate index unchanged.

    Used by default for non-Japanese pipelines so the historical
    linear-interpolation split behaviour is preserved.
    """

    def adjust(self, text: str, candidate_index: int, search_radius: int) -> int:
        """Return ``candidate_index`` verbatim, ignoring ``search_radius``."""
        return candidate_index

    def is_valid(self, text: str, index: int) -> bool:
        """Return ``True`` unconditionally — every in-range index is valid."""
        return True
