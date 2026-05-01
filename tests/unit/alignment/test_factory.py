"""Tests for :class:`AlignmentBackendFactory`.

The English and Japanese backend ``__init__`` methods are patched to no-ops
so the test does not require ``torch`` / ``torchaudio`` / ``transformers``.
"""

from __future__ import annotations

import pytest

from talking_parrot.alignment.english_backend import EnglishAlignmentBackend
from talking_parrot.alignment.factory import AlignmentBackendFactory
from talking_parrot.alignment.japanese_backend import JapaneseAlignmentBackend
from talking_parrot.models.context import GranularityPreference


@pytest.fixture(autouse=True)
def _stub_backend_inits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the heavy ``__init__`` methods with no-ops for every test."""

    def _noop(self: object) -> None:
        """No-op constructor used to avoid loading torch/transformers in tests."""
        return None

    monkeypatch.setattr(EnglishAlignmentBackend, "__init__", _noop)
    monkeypatch.setattr(JapaneseAlignmentBackend, "__init__", _noop)


def test_create_en_auto_returns_english_backend() -> None:
    """``create("en", AUTO)`` MUST return an ``EnglishAlignmentBackend``."""
    factory = AlignmentBackendFactory()
    be = factory.create("en", GranularityPreference.AUTO)
    assert isinstance(be, EnglishAlignmentBackend)


def test_create_ja_auto_returns_japanese_backend() -> None:
    """``create("ja", AUTO)`` MUST return a ``JapaneseAlignmentBackend``."""
    factory = AlignmentBackendFactory()
    be = factory.create("ja", GranularityPreference.AUTO)
    assert isinstance(be, JapaneseAlignmentBackend)


def test_create_en_word_returns_english_backend() -> None:
    """Explicit ``WORD`` for English MUST return an ``EnglishAlignmentBackend``."""
    factory = AlignmentBackendFactory()
    be = factory.create("en", GranularityPreference.WORD)
    assert isinstance(be, EnglishAlignmentBackend)


def test_create_ja_character_returns_japanese_backend() -> None:
    """Explicit ``CHARACTER`` for Japanese MUST return a ``JapaneseAlignmentBackend``."""
    factory = AlignmentBackendFactory()
    be = factory.create("ja", GranularityPreference.CHARACTER)
    assert isinstance(be, JapaneseAlignmentBackend)


def test_create_unknown_language_raises_value_error() -> None:
    """Unknown ``language`` under AUTO MUST raise the exact-substring ValueError."""
    factory = AlignmentBackendFactory()
    with pytest.raises(ValueError, match="No alignment backend for language: fr"):
        factory.create("fr", GranularityPreference.AUTO)


def test_create_en_character_raises_value_error() -> None:
    """English has no CHARACTER backend → ValueError with documented substring."""
    factory = AlignmentBackendFactory()
    with pytest.raises(ValueError, match="No CHARACTER-granularity alignment backend"):
        factory.create("en", GranularityPreference.CHARACTER)


def test_create_ja_word_raises_value_error() -> None:
    """Japanese has no WORD backend → ValueError with documented substring."""
    factory = AlignmentBackendFactory()
    with pytest.raises(ValueError, match="No WORD-granularity alignment backend"):
        factory.create("ja", GranularityPreference.WORD)


def test_create_caches_by_language_and_granularity() -> None:
    """Two AUTO calls for English MUST return the same instance."""
    factory = AlignmentBackendFactory()
    a = factory.create("en")
    b = factory.create("en")
    assert a is b


def test_auto_and_explicit_word_resolve_to_same_instance_for_english() -> None:
    """For English, AUTO and explicit WORD resolve to the same cached instance."""
    factory = AlignmentBackendFactory()
    a = factory.create("en", GranularityPreference.AUTO)
    b = factory.create("en", GranularityPreference.WORD)
    assert a is b
