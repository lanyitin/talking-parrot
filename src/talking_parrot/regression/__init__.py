"""Regression harness for the talking-parrot transcription pipeline.

Realises the **Decision: Module decomposition follows SRP** module split
from the ``regression-runner`` change's ``design.md``:

- :mod:`scorer` is a pure ``score(snapshot, descriptor) -> ScoreCard``.
- :mod:`baseline` defines the :class:`BaselineStore` protocol and the
  default :class:`JsonBaselineStore` implementation.
- :mod:`reporter` renders the JSON + HTML report and writes both to
  disk.
- :mod:`runner` discovers samples and drives the pipeline once per
  variant.
- :mod:`cli` parses command-line arguments and wires the pieces.
- :mod:`__main__` makes ``uv run python -m talking_parrot.regression``
  the supported entry point.
"""

from __future__ import annotations

from talking_parrot.regression.baseline import (
    BaselineSchemaError,
    BaselineStore,
    JsonBaselineStore,
)
from talking_parrot.regression.reporter import (
    RegressionReport,
    SampleReportEntry,
    render_report,
    write_report,
)
from talking_parrot.regression.runner import (
    DEFAULT_CER_TOLERANCE,
    DEFAULT_CONFIDENCE_TOLERANCE,
    PipelineRunner,
    PipelineRunnerFactory,
    RegressionRunner,
    RunResult,
    compute_delta,
    compute_verdict,
    discover_samples,
)
from talking_parrot.regression.scorer import (
    SampleDescriptor,
    SampleVariant,
    score,
)

__all__ = [
    "BaselineSchemaError",
    "BaselineStore",
    "DEFAULT_CER_TOLERANCE",
    "DEFAULT_CONFIDENCE_TOLERANCE",
    "JsonBaselineStore",
    "PipelineRunner",
    "PipelineRunnerFactory",
    "RegressionReport",
    "RegressionRunner",
    "RunResult",
    "SampleDescriptor",
    "SampleReportEntry",
    "SampleVariant",
    "compute_delta",
    "compute_verdict",
    "discover_samples",
    "render_report",
    "score",
    "write_report",
]
