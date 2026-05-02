"""Subtitle post-processing subsystem (Stage 5).

Public surface:

- :class:`SubtitleProcessor` — abstract base for all post-processing operators.
- :class:`GranularityAwareProcessorFactory` /
  :class:`DefaultGranularityAwareProcessorFactory` — selects the processor
  group for a given :class:`AlignmentGranularity`.
- Six concrete processors split into three groups:

  * Word: :class:`WordBoundaryMergeProcessor`,
    :class:`WordBoundarySplitProcessor`
  * Character: :class:`CharacterBoundaryMergeProcessor`,
    :class:`CharacterBoundarySplitProcessor`
  * Time-based fallback: :class:`TimeBasedMergeProcessor`,
    :class:`TimeBasedSplitProcessor`
"""

from talking_parrot.post_processing.base import SubtitleProcessor
from talking_parrot.post_processing.character_boundary import (
    CharacterBoundaryMergeProcessor,
    CharacterBoundarySplitProcessor,
)
from talking_parrot.post_processing.factory import (
    DefaultGranularityAwareProcessorFactory,
    GranularityAwareProcessorFactory,
)
from talking_parrot.post_processing.time_based import (
    TimeBasedMergeProcessor,
    TimeBasedSplitProcessor,
)
from talking_parrot.post_processing.word_boundary import (
    WordBoundaryMergeProcessor,
    WordBoundarySplitProcessor,
)

__all__ = [
    "CharacterBoundaryMergeProcessor",
    "CharacterBoundarySplitProcessor",
    "DefaultGranularityAwareProcessorFactory",
    "GranularityAwareProcessorFactory",
    "SubtitleProcessor",
    "TimeBasedMergeProcessor",
    "TimeBasedSplitProcessor",
    "WordBoundaryMergeProcessor",
    "WordBoundarySplitProcessor",
]
