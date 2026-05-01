"""Factory that resolves :class:`AlignmentBackend` instances by language and granularity."""

from __future__ import annotations

from typing import ClassVar

from talking_parrot.alignment.backend import AlignmentBackend
from talking_parrot.alignment.english_backend import EnglishAlignmentBackend
from talking_parrot.alignment.japanese_backend import JapaneseAlignmentBackend
from talking_parrot.models.context import AlignmentGranularity, GranularityPreference


class AlignmentBackendFactory:
    """Routes ``(language, GranularityPreference)`` pairs to backend classes.

    The factory caches instances by ``(language, AlignmentGranularity)`` so
    repeated ``create()`` calls that resolve to the same key return the same
    object (verifiable via ``is`` identity).
    """

    _REGISTRY: ClassVar[
        dict[tuple[str, AlignmentGranularity], type[AlignmentBackend]]
    ] = {
        ("en", AlignmentGranularity.WORD): EnglishAlignmentBackend,
        ("ja", AlignmentGranularity.CHARACTER): JapaneseAlignmentBackend,
    }
    _DEFAULTS: ClassVar[dict[str, AlignmentGranularity]] = {
        "en": AlignmentGranularity.WORD,
        "ja": AlignmentGranularity.CHARACTER,
    }

    def __init__(self) -> None:
        """Initialise an empty per-instance cache."""
        self._cache: dict[tuple[str, AlignmentGranularity], AlignmentBackend] = {}

    def create(
        self,
        language: str,
        granularity_pref: GranularityPreference = GranularityPreference.AUTO,
    ) -> AlignmentBackend:
        """Resolve and return a backend for ``(language, granularity_pref)``.

        Args:
            language: ISO language code, e.g. ``"en"`` or ``"ja"``.
            granularity_pref: User preference. ``AUTO`` resolves to the
                language's natural granularity defined in ``_DEFAULTS``.

        Returns:
            A cached or freshly instantiated :class:`AlignmentBackend`.

        Raises:
            ValueError: If ``language`` is unknown (under AUTO) or no backend
                exists for ``(language, requested_granularity)``.
        """
        if granularity_pref is GranularityPreference.AUTO:
            if language not in self._DEFAULTS:
                raise ValueError(f"No alignment backend for language: {language}")
            granularity = self._DEFAULTS[language]
        else:
            granularity = AlignmentGranularity(granularity_pref.value)

        cls = self._REGISTRY.get((language, granularity))
        if cls is None:
            raise ValueError(
                f"No {granularity.value}-granularity alignment backend "
                f"for language: {language}"
            )

        cached = self._cache.get((language, granularity))
        if cached is not None:
            return cached
        instance = cls()
        self._cache[(language, granularity)] = instance
        return instance
