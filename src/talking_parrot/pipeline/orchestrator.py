from __future__ import annotations

import time
from typing import Sequence, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from talking_parrot.stages.base import PipelineStage
    from talking_parrot.models.context import PipelineContext

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """Drives a sequence of PipelineStage instances in order.

    Owns no business logic — sole responsibility is sequencing.
    After :meth:`run` completes, :attr:`stage_timings` holds the
    wall-clock elapsed seconds for each stage keyed by stage name.
    """

    def __init__(self, stages: Sequence["PipelineStage"]) -> None:
        """Initialise the orchestrator with an ordered stage list."""
        self._stages = list(stages)
        self.stage_timings: dict[str, float] = {}

    def run(self, ctx: "PipelineContext") -> "PipelineContext":
        """Run each stage in order, logging stage boundaries at INFO level.

        Per-stage wall-clock time is recorded in :attr:`stage_timings` and
        logged alongside the ``stage end`` event.
        """
        self.stage_timings = {}
        for stage in self._stages:
            logger.info("stage start", stage=stage.name)
            t0 = time.perf_counter()
            ctx = stage.process(ctx)
            elapsed = time.perf_counter() - t0
            self.stage_timings[stage.name] = elapsed
            logger.info("stage end", stage=stage.name, elapsed_s=round(elapsed, 3))
        return ctx
