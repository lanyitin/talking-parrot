"""CLI entry point for the regression harness.

Realises the **Decision: CLI surface and exit codes** from the
``regression-runner`` change's ``design.md``. Exit codes:

- ``0``: every verdict is ``stable`` / ``improved`` / ``bootstrapped``
  / ``skipped`` / ``unscored``.
- ``1``: at least one verdict is ``regressed``.
- ``2``: argument or I/O failure.

``--reset-baseline`` overrides every verdict to ``bootstrapped`` and
forces exit code ``0``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from talking_parrot.regression.baseline import BaselineStore, JsonBaselineStore
from talking_parrot.regression.reporter import write_report
from talking_parrot.regression.runner import (
    DEFAULT_CER_TOLERANCE,
    DEFAULT_CONFIDENCE_TOLERANCE,
    PipelineRunnerFactory,
    RegressionRunner,
)

_DEFAULT_SAMPLES_DIR = "test-samples"
_DEFAULT_RESULTS_DIR = "test-samples/results"

_logger = logging.getLogger("talking_parrot.regression.cli")


@dataclass(frozen=True, slots=True)
class RegressionConfig:
    """Resolved CLI configuration for the regression harness."""

    samples_dir: Path
    results_dir: Path
    label: str | None
    reset_baseline: bool
    cer_tolerance: float
    confidence_tolerance: float
    strict_missing: bool


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talking_parrot.regression",
        description="Run the Talking Parrot transcription regression harness.",
    )
    parser.add_argument("--samples-dir", default=_DEFAULT_SAMPLES_DIR)
    parser.add_argument("--results-dir", default=_DEFAULT_RESULTS_DIR)
    parser.add_argument("--label", default=None)
    parser.add_argument("--reset-baseline", action="store_true")
    parser.add_argument("--cer-tolerance", default=DEFAULT_CER_TOLERANCE, type=float)
    parser.add_argument(
        "--confidence-tolerance",
        default=DEFAULT_CONFIDENCE_TOLERANCE,
        type=float,
    )
    parser.add_argument("--strict-missing", action="store_true")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> RegressionConfig:
    """Parse ``argv`` into a :class:`RegressionConfig`."""
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return RegressionConfig(
        samples_dir=Path(args.samples_dir),
        results_dir=Path(args.results_dir),
        label=args.label,
        reset_baseline=bool(args.reset_baseline),
        cer_tolerance=float(args.cer_tolerance),
        confidence_tolerance=float(args.confidence_tolerance),
        strict_missing=bool(args.strict_missing),
    )


def _ensure_stdout_logging() -> None:
    """Attach a single stdout handler to the regression logger (idempotent)."""
    has_stdout = any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, "stream", None) is sys.stdout
        for h in _logger.handlers
    )
    if not has_stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        _logger.addHandler(handler)
    if _logger.level == logging.NOTSET:
        _logger.setLevel(logging.INFO)


def _exit_code_for_verdicts(verdicts: list[str], *, strict_missing: bool) -> int:
    """Return the documented exit code for a list of per-variant verdicts."""
    has_regressed = "regressed" in verdicts
    has_skipped = "skipped" in verdicts
    if has_regressed:
        return 1
    if strict_missing and has_skipped:
        return 1
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    baseline_store_factory: (
        type[JsonBaselineStore] | None
    ) = None,  # accepted for symmetry; default uses JsonBaselineStore
    pipeline_runner_factory: PipelineRunnerFactory | None = None,
    baseline_store: BaselineStore | None = None,
) -> int:
    """CLI entry point. Returns the process exit code.

    ``pipeline_runner_factory`` and ``baseline_store`` are
    dependency-injection seams used by tests. Production callers pass
    nothing; ``baseline_store`` defaults to :class:`JsonBaselineStore`
    rooted at the configured ``samples_dir``.
    """
    _ensure_stdout_logging()
    try:
        config = parse_args(argv)
    except SystemExit as exc:
        # argparse already emitted a message on stderr.
        code = int(exc.code) if isinstance(exc.code, int) else 2
        return code

    if not config.samples_dir.exists():
        _logger.error("samples directory not found: %s", config.samples_dir)
        return 2

    store: BaselineStore = baseline_store or JsonBaselineStore(
        config.samples_dir, label=config.label
    )

    runner = RegressionRunner(
        samples_dir=config.samples_dir,
        baseline_store=store,
        pipeline_runner_factory=pipeline_runner_factory,
        cer_tolerance=config.cer_tolerance,
        confidence_tolerance=config.confidence_tolerance,
        strict_missing=config.strict_missing,
        reset_baseline=config.reset_baseline,
        label=config.label,
    )

    try:
        report, results = runner.run_all()
    except FileNotFoundError as exc:
        _logger.error("file not found: %s", exc)
        return 2
    except OSError as exc:
        _logger.error("I/O failure during regression run: %s", exc)
        return 2

    try:
        write_report(report, config.results_dir)
    except OSError as exc:
        _logger.error("failed writing report: %s", exc)
        return 2

    if config.reset_baseline:
        return 0
    verdicts = [r.verdict for r in results]
    return _exit_code_for_verdicts(verdicts, strict_missing=config.strict_missing)


__all__ = ["RegressionConfig", "main", "parse_args"]
