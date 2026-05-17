"""Sample discovery and per-variant pipeline orchestration.

Realises the **Decision: Sample discovery and pipeline invocation**,
**Decision: Regression verdict is rule-based with explicit thresholds**,
and **Decision: Module decomposition follows SRP** from the
``regression-runner`` change's ``design.md``.

A real production run constructs a single
:class:`talking_parrot.pipeline.orchestrator.PipelineOrchestrator`
instance and reuses it across variants. Tests inject a stub orchestrator
factory so the runner can be exercised without real audio.
"""

from __future__ import annotations

import datetime as _dt
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from talking_parrot.shared import ProjectSnapshot, ScoreCard

from talking_parrot.regression.baseline import BaselineStore
from talking_parrot.regression.reporter import (
    RegressionReport,
    SampleReportEntry,
)
from talking_parrot.regression.scorer import (
    SampleDescriptor,
    SampleVariant,
    score,
)

_logger = logging.getLogger("talking_parrot.regression.runner")

# ----- Verdict / threshold defaults -----------------------------------------

DEFAULT_CER_TOLERANCE = 0.02
DEFAULT_CONFIDENCE_TOLERANCE = 0.05


# ----- Run results ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunResult:
    """Result of running one variant of one sample."""

    sample_id: str
    variant_file: str
    snapshot: ProjectSnapshot | None
    score_card: ScoreCard | None
    run_timestamp: str
    verdict: str  # one of: regressed/improved/stable/bootstrapped/skipped/unscored


# ----- Sample discovery -----------------------------------------------------


def discover_samples(samples_dir: Path) -> list[SampleDescriptor]:
    """Return one :class:`SampleDescriptor` per ``descriptor.yml``.

    Sample directories are iterated in deterministic alphabetical order.
    Variants preserve their declaration order inside the YAML.

    Raises:
        FileNotFoundError: when ``samples_dir`` does not exist. Callers
            (the CLI) are responsible for translating this into the
            documented exit code 2.
    """
    samples_dir = Path(samples_dir)
    if not samples_dir.exists():
        raise FileNotFoundError(f"samples directory not found: {samples_dir}")

    descriptors: list[SampleDescriptor] = []
    for sample_path in sorted(p for p in samples_dir.iterdir() if p.is_dir()):
        descriptor_path = sample_path / "descriptor.yml"
        if not descriptor_path.exists():
            _logger.debug(
                "discover_samples skip path=%s reason=no descriptor.yml",
                sample_path,
            )
            continue
        _logger.debug("discover_samples reading path=%s", descriptor_path)
        with descriptor_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        assert isinstance(raw, dict), (
            f"descriptor.yml at {descriptor_path} did not yield a mapping; "
            "pyyaml.safe_load contract may have changed"
        )
        base_file = str(raw.get("file", ""))
        reference_text = str(raw.get("text", ""))
        raw_variants = raw.get("variants") or []
        assert isinstance(raw_variants, list), (
            f"descriptor.yml at {descriptor_path}: 'variants' must be a list"
        )
        variants_list: list[SampleVariant] = []
        for v in raw_variants:
            if not isinstance(v, dict):
                continue
            variants_list.append(
                SampleVariant(
                    file=str(v.get("file", "")),
                    description=str(v.get("description", "")),
                )
            )
        descriptors.append(
            SampleDescriptor(
                sample_id=sample_path.name,
                base_file=base_file,
                reference_text=reference_text,
                variants=tuple(variants_list),
            )
        )
    _logger.debug("discover_samples found=%d", len(descriptors))
    return descriptors


# ----- Verdict computation --------------------------------------------------


def compute_verdict(
    *,
    current: ScoreCard,
    baseline: ScoreCard | None,
    cer_tolerance: float = DEFAULT_CER_TOLERANCE,
    confidence_tolerance: float = DEFAULT_CONFIDENCE_TOLERANCE,
) -> str:
    """Return the verdict string for one current/baseline pair.

    Pure function. ``bootstrapped`` when no baseline exists. ``regressed``
    when CER rises by more than ``cer_tolerance`` OR confidence_mean
    drops by more than ``confidence_tolerance``. ``improved`` when CER
    drops by more than tolerance and confidence does not regress.
    Otherwise ``stable``.
    """
    if baseline is None:
        return "bootstrapped"
    cer_delta = current.metric_bundle.cer - baseline.metric_bundle.cer
    conf_delta = (
        current.metric_bundle.confidence_mean - baseline.metric_bundle.confidence_mean
    )
    if cer_delta > cer_tolerance or conf_delta < -confidence_tolerance:
        return "regressed"
    if cer_delta < -cer_tolerance and conf_delta >= -confidence_tolerance:
        return "improved"
    return "stable"


def compute_delta(current: ScoreCard, baseline: ScoreCard) -> dict[str, float]:
    """Return the per-:class:`MetricBundle`-field delta (current minus baseline)."""
    cm = current.metric_bundle
    bm = baseline.metric_bundle
    return {
        "cer": cm.cer - bm.cer,
        "confidence_mean": cm.confidence_mean - bm.confidence_mean,
        "confidence_p10": cm.confidence_p10 - bm.confidence_p10,
        "repetition_ratio_mean": cm.repetition_ratio_mean - bm.repetition_ratio_mean,
        "no_speech_prob_mean": cm.no_speech_prob_mean - bm.no_speech_prob_mean,
    }


# ----- Orchestrator port ----------------------------------------------------

# A pipeline runner takes (sample_dir, variant_file) and returns a snapshot.
# The production factory builds the real PipelineOrchestrator once and reuses
# it. Tests inject a stub.
PipelineRunner = Callable[[Path, str], ProjectSnapshot]
PipelineRunnerFactory = Callable[[], PipelineRunner]


def _default_pipeline_runner_factory() -> PipelineRunner:
    """Build a default pipeline runner backed by :mod:`talking_parrot.pipeline`.

    The returned callable constructs a single
    :class:`PipelineOrchestrator` lazily and reuses it across variants.
    Wiring up real stages requires the project's stage registry, which
    is out of scope for this change; the default raises
    :class:`NotImplementedError` so an operator MUST provide an
    explicit factory for now (the integration test injects a stub).
    """

    def _runner(sample_dir: Path, variant_file: str) -> ProjectSnapshot:
        raise NotImplementedError(
            "default pipeline runner is not wired in this change; "
            "operators must inject a PipelineRunnerFactory until the "
            "stage-registry integration lands"
        )

    return _runner


# ----- Runner ---------------------------------------------------------------


class RegressionRunner:
    """Drive the pipeline across all discovered samples and variants.

    Caches one :class:`PipelineRunner` instance across variants per
    :class:`PipelineRunnerFactory` invocation, satisfying the
    **Decision: Sample discovery and pipeline invocation** rule.
    """

    def __init__(
        self,
        *,
        samples_dir: Path,
        baseline_store: BaselineStore,
        pipeline_runner_factory: PipelineRunnerFactory | None = None,
        cer_tolerance: float = DEFAULT_CER_TOLERANCE,
        confidence_tolerance: float = DEFAULT_CONFIDENCE_TOLERANCE,
        strict_missing: bool = False,
        reset_baseline: bool = False,
        label: str | None = None,
        clock: Callable[[], _dt.datetime] | None = None,
    ) -> None:
        """Construct a runner.

        ``pipeline_runner_factory`` defaults to a stub that raises
        :class:`NotImplementedError`; tests and the production wiring
        inject their own factories. ``clock`` returns the current UTC
        timestamp; tests may inject a fixed clock for determinism.
        """
        self._samples_dir = Path(samples_dir)
        self._baseline_store = baseline_store
        self._pipeline_runner_factory = (
            pipeline_runner_factory or _default_pipeline_runner_factory
        )
        self._cer_tolerance = cer_tolerance
        self._confidence_tolerance = confidence_tolerance
        self._strict_missing = strict_missing
        self._reset_baseline = reset_baseline
        self._label = label
        self._clock = clock or (
            lambda: _dt.datetime.now(_dt.UTC).replace(microsecond=0)
        )

    # -- discovery / per-variant -------------------------------------------

    def discover(self) -> list[SampleDescriptor]:
        """Return the list of :class:`SampleDescriptor` found under samples_dir."""
        return discover_samples(self._samples_dir)

    def _run_variant(
        self,
        descriptor: SampleDescriptor,
        variant_file: str,
        runner: PipelineRunner,
    ) -> RunResult:
        """Run one variant and produce a :class:`RunResult`."""
        sample_dir = self._samples_dir / descriptor.sample_id
        audio_path = sample_dir / variant_file
        timestamp = self._clock().isoformat()

        if not audio_path.exists():
            _logger.warning(
                "run_variant missing audio sample_id=%s variant=%s path=%s",
                descriptor.sample_id,
                variant_file,
                audio_path,
            )
            return RunResult(
                sample_id=descriptor.sample_id,
                variant_file=variant_file,
                snapshot=None,
                score_card=None,
                run_timestamp=timestamp,
                verdict="skipped",
            )

        _logger.debug(
            "run_variant invoking runner sample_id=%s variant=%s",
            descriptor.sample_id,
            variant_file,
        )
        snapshot = runner(sample_dir, variant_file)
        assert isinstance(snapshot, ProjectSnapshot), (
            "pipeline runner did not return ProjectSnapshot — "
            "shared layer API may have changed"
        )
        card = score(snapshot, descriptor)

        baseline = (
            None
            if self._reset_baseline
            else self._baseline_store.load(descriptor.sample_id)
        )
        if self._reset_baseline:
            self._baseline_store.save(descriptor.sample_id, card)
            verdict = "bootstrapped"
        elif not descriptor.reference_text:
            verdict = "unscored"
        elif baseline is None:
            self._baseline_store.save(descriptor.sample_id, card)
            verdict = "bootstrapped"
        else:
            verdict = compute_verdict(
                current=card,
                baseline=baseline,
                cer_tolerance=self._cer_tolerance,
                confidence_tolerance=self._confidence_tolerance,
            )

        return RunResult(
            sample_id=descriptor.sample_id,
            variant_file=variant_file,
            snapshot=snapshot,
            score_card=card,
            run_timestamp=timestamp,
            verdict=verdict,
        )

    # -- top-level run -----------------------------------------------------

    def run_all(self) -> tuple[RegressionReport, list[RunResult]]:
        """Run every variant of every sample.

        Returns the aggregate :class:`RegressionReport` plus the
        per-variant :class:`RunResult` list. The pipeline runner is
        constructed exactly once and shared across every variant.
        """
        descriptors = self.discover()
        # Build the pipeline runner ONCE for this invocation.
        pipeline_runner = self._pipeline_runner_factory()
        results: list[RunResult] = []
        entries: list[SampleReportEntry] = []
        for descriptor in descriptors:
            for variant_file in descriptor.all_files:
                result = self._run_variant(descriptor, variant_file, pipeline_runner)
                results.append(result)
                entries.append(self._to_entry(result, descriptor))

        generated_at = self._clock().isoformat()
        report = RegressionReport(
            schema_version=1,
            generated_at=generated_at,
            label=self._label,
            samples=tuple(entries),
        )
        return report, results

    def _to_entry(
        self,
        result: RunResult,
        descriptor: SampleDescriptor,
    ) -> SampleReportEntry:
        """Convert a :class:`RunResult` into a :class:`SampleReportEntry`."""
        stage_timings = (
            dict(result.snapshot.stage_timings)
            if result.snapshot is not None
            else {}
        )
        if result.score_card is None:
            # Skipped — produce an empty placeholder ScoreCard so the entry
            # type stays homogeneous. We use shared.MetricBundle zeros.
            from talking_parrot.shared import MetricBundle, ScoreCard as _SC

            placeholder = _SC(
                sample_id=descriptor.sample_id,
                overall_score=0.0,
                metric_bundle=MetricBundle(
                    cer=0.0,
                    confidence_mean=0.0,
                    confidence_p10=0.0,
                    repetition_ratio_mean=0.0,
                    no_speech_prob_mean=0.0,
                ),
                cue_diffs=[],
            )
            return SampleReportEntry(
                sample_id=result.sample_id,
                variant_file=result.variant_file,
                verdict=result.verdict,
                current=placeholder,
                baseline=None,
                delta=None,
                stage_timings=stage_timings,
            )
        # For reporting we want the baseline (if any) at the time of run.
        baseline = (
            None
            if result.verdict == "bootstrapped"
            else self._baseline_store.load(descriptor.sample_id)
        )
        delta = compute_delta(result.score_card, baseline) if baseline else None
        return SampleReportEntry(
            sample_id=result.sample_id,
            variant_file=result.variant_file,
            verdict=result.verdict,
            current=result.score_card,
            baseline=baseline,
            delta=delta,
            stage_timings=stage_timings,
        )


def _attach_pipeline_module(_unused: Any) -> None:
    """Touch the pipeline module so import-time wiring stays alive."""
    # Imported here only for the side-effect of validating the module path
    # named in design.md. Production wiring will replace this with a real
    # factory; the integration test injects a stub factory.
    import talking_parrot.pipeline.orchestrator  # noqa: F401


__all__ = [
    "DEFAULT_CER_TOLERANCE",
    "DEFAULT_CONFIDENCE_TOLERANCE",
    "PipelineRunner",
    "PipelineRunnerFactory",
    "RegressionRunner",
    "RunResult",
    "compute_delta",
    "compute_verdict",
    "discover_samples",
]
