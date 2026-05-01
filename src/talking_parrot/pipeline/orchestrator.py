from __future__ import annotations

from typing import Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from talking_parrot.stages.base import PipelineStage
    from talking_parrot.models.context import PipelineContext


class PipelineOrchestrator:
    """Drives a sequence of PipelineStage instances in order.

    Owns no business logic — sole responsibility is sequencing.
    """

    def __init__(self, stages: Sequence["PipelineStage"]) -> None:
        self._stages = list(stages)

    def run(self, ctx: "PipelineContext") -> "PipelineContext":
        for stage in self._stages:
            ctx = stage.process(ctx)
        return ctx
