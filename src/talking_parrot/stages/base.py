from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from talking_parrot.models.context import PipelineContext


class PipelineStage(abc.ABC):
    """Abstract interface every pipeline stage must implement.

    Contract:
    - `process()` MUST NOT mutate the input context.
    - When the stage is disabled, return the input ctx unchanged.
    - When enabled, return a new PipelineContext via dataclasses.replace().
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable stage name."""

    @abc.abstractmethod
    def process(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run the stage and return the (possibly updated) context."""
