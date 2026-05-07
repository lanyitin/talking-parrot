from __future__ import annotations

from typing import Sequence, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from talking_parrot.stages.base import PipelineStage
    from talking_parrot.models.context import PipelineContext

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """Drives a sequence of PipelineStage instances in order.

    Owns no business logic — sole responsibility is sequencing.
    """

    def __init__(self, stages: Sequence["PipelineStage"]) -> None:
        self._stages = list(stages)

    def run(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run each stage in order, logging stage boundaries at INFO level."""
        for stage in self._stages:
            logger.info("stage start", stage=stage.name)
            ctx = stage.process(ctx)
            logger.info("stage end", stage=stage.name)
        return ctx
