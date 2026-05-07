"""Japanese-specific post-processors.

Spec: ``japanese-postprocessors`` (change
``segment-level-postprocessing-pipeline``). Design decision: *Japanese
processors appended only when ``expected_language == "ja"``*.

Two processors live here:

* :class:`JapaneseFillerProcessor` strips a leading filler token from each
  cue's text. Default tokens: ``あの``, ``あのー``, ``えっと``, ``えーと``,
  ``えー``, ``まあ``, ``そのー``, ``その``, ``なんか``, ``ね``. Cues whose
  text becomes empty after stripping are dropped; survivors are renumbered
  1-based.
* :class:`JapaneseRepetitionProcessor` collapses any run of three or more
  identical adjacent characters in a cue's text down to exactly two
  characters, with the exception that runs whose underlying two-character
  cycle is in the configured onomatopoeia whitelist are preserved verbatim.

Both processors honour the disabled-path convention used by
:mod:`talking_parrot.post_processing.dedup`: when their respective
``*_enabled`` flag is ``False`` the input list is returned as a shallow
copy with original indexes preserved.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

import structlog

from talking_parrot.models.subtitle import Subtitle
from talking_parrot.post_processing.base import SubtitleProcessor, _renumber

if TYPE_CHECKING:
    from talking_parrot.config.models import PostProcessingConfig

logger = structlog.get_logger(__name__)


# Leading whitespace plus Japanese / ASCII punctuation that may follow a
# stripped filler. The spec scenario "あのー、こんにちは → こんにちは"
# requires that the trailing comma also be removed, so we strip leading
# punctuation immediately after slicing off the filler token.
_LEADING_TRIM_RE = re.compile(r"^[\s、。，．,.　]+")

# Run of 3+ identical non-whitespace characters (used for repetition collapse).
_CHAR_REPEAT_RE = re.compile(r"(\S)\1{2,}")


def _build_filler_regex(tokens: list[str]) -> re.Pattern[str] | None:
    """Build an anchored alternation regex for ``tokens``.

    Tokens are sorted longest-first so that, e.g., ``あのー`` matches before
    ``あの`` and does not leave ``ー`` behind. ``re.escape`` is applied for
    safety against arbitrary configuration values.
    """
    cleaned = [t for t in tokens if t]
    if not cleaned:
        return None
    cleaned.sort(key=len, reverse=True)
    pattern = "^(?:" + "|".join(re.escape(t) for t in cleaned) + ")"
    return re.compile(pattern)


def _build_whitelist_regex(whitelist: list[str]) -> re.Pattern[str] | None:
    """Build a regex matching any whitelisted onomatopoeia run (length >= 4).

    Each whitelist entry is treated as a two-character cycle (e.g.
    ``"どきどき"``); we match one or more repetitions of that cycle so the
    repetition-collapse step can leave whitelisted runs untouched.
    """
    cleaned = [w for w in whitelist if w]
    if not cleaned:
        return None
    cleaned.sort(key=len, reverse=True)
    pattern = "(?:" + "|".join(f"(?:{re.escape(w)})+" for w in cleaned) + ")"
    return re.compile(pattern)


class JapaneseFillerProcessor(SubtitleProcessor):
    """Strip leading Japanese filler tokens; drop cues that become empty."""

    def process(
        self,
        subtitles: list[Subtitle],
        config: "PostProcessingConfig",
    ) -> list[Subtitle]:
        """Strip leading filler words; drop cues that become empty; renumber."""
        if not subtitles:
            return []

        if not config.japanese_filler_enabled:
            # Spec: disabled processor returns input unchanged (preserve indexes).
            return list(subtitles)

        survivors: list[Subtitle] = []
        filler_re = _build_filler_regex(list(config.japanese_filler_words))
        if filler_re is None:
            # No filler words configured; behave as a pass-through but still
            # drop empty cues to honour the "drop empty" invariant.
            survivors = [s for s in subtitles if s.text.strip()]
            return _renumber(survivors)

        dropped = 0
        for sub in subtitles:
            # Strip leading whitespace before matching, per spec wording.
            text = sub.text.lstrip()
            match = filler_re.match(text)
            if match is not None:
                text = text[match.end() :]
                # Spec: "After filler removal, leading whitespace SHALL be
                # stripped." The scenario also expects leading punctuation to
                # be stripped (``あのー、こんにちは`` → ``こんにちは``).
                text = _LEADING_TRIM_RE.sub("", text)

            if not text.strip():
                dropped += 1
                continue

            if text != sub.text:
                survivors.append(dataclasses.replace(sub, text=text))
            else:
                survivors.append(sub)

        if dropped:
            logger.debug(
                "JapaneseFillerProcessor dropped filler-only cues",
                input_count=len(subtitles),
                output_count=len(survivors),
                dropped=dropped,
            )
        return _renumber(survivors)


class JapaneseRepetitionProcessor(SubtitleProcessor):
    """Collapse runs of 3+ identical chars to 2; preserve whitelisted onomatopoeia.

    Algorithm: split the text into alternating "protected" spans (any run of
    a whitelisted two-character cycle of length >= 4) and "free" spans;
    collapse single-character 3+ runs only in the free spans, then concat.
    """

    def process(
        self,
        subtitles: list[Subtitle],
        config: "PostProcessingConfig",
    ) -> list[Subtitle]:
        """Collapse runs of 3+ identical adjacent characters to 2; renumber."""
        if not subtitles:
            return []

        if not config.japanese_repetition_enabled:
            return list(subtitles)

        whitelist_re = _build_whitelist_regex(
            list(config.japanese_onomatopoeia_whitelist)
        )

        survivors: list[Subtitle] = []
        dropped = 0
        for sub in subtitles:
            cleaned = _collapse_repetitions(sub.text, whitelist_re)
            if not cleaned.strip():
                dropped += 1
                continue
            if cleaned != sub.text:
                survivors.append(dataclasses.replace(sub, text=cleaned))
            else:
                survivors.append(sub)

        if dropped:
            logger.debug(
                "JapaneseRepetitionProcessor dropped empty cues",
                input_count=len(subtitles),
                output_count=len(survivors),
                dropped=dropped,
            )
        return _renumber(survivors)


def _collapse_repetitions(text: str, whitelist_re: re.Pattern[str] | None) -> str:
    """Collapse 3+ char runs to 2, leaving whitelisted onomatopoeia spans intact."""
    if not text:
        return text
    if whitelist_re is None:
        return _CHAR_REPEAT_RE.sub(r"\1\1", text)

    out: list[str] = []
    cursor = 0
    for m in whitelist_re.finditer(text):
        # Free span before the protected match — apply collapse here.
        free = text[cursor : m.start()]
        if free:
            out.append(_CHAR_REPEAT_RE.sub(r"\1\1", free))
        # Protected span — leave verbatim.
        out.append(m.group(0))
        cursor = m.end()
    # Trailing free span.
    tail = text[cursor:]
    if tail:
        out.append(_CHAR_REPEAT_RE.sub(r"\1\1", tail))
    return "".join(out)
