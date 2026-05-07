from __future__ import annotations

import structlog

import pydantic
import yaml

from talking_parrot.config.models import PipelineConfig
from talking_parrot.transcription.factory import TranscriptionBackendFactory

log = structlog.get_logger()
_logger = structlog.get_logger(__name__)


class ConfigLoader:
    @staticmethod
    def load(path: str) -> PipelineConfig:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        cfg = PipelineConfig.model_validate(raw)

        ConfigLoader._resolve_transcribing_backends(cfg)

        if cfg.transcribing[0].condition != "true":
            raise pydantic.ValidationError.from_exception_data(
                title="PipelineConfig",
                input_type="python",
                line_errors=[
                    {
                        "type": "value_error",
                        "loc": ("transcribing", 0, "condition"),
                        "input": cfg.transcribing[0].condition,
                        "ctx": {"error": ValueError('must be "true"')},
                    }
                ],
            )

        ConfigLoader._check_vad_chunking_consistency(cfg)

        return cfg

    @staticmethod
    def _resolve_transcribing_backends(cfg: PipelineConfig) -> None:
        """Fill omitted ``TranscribingStep.backend`` values with the platform default."""
        platform_default: str | None = None
        for step in cfg.transcribing:
            if step.backend is None:
                if platform_default is None:
                    platform_default = (
                        TranscriptionBackendFactory.default_for_platform()
                    )
                step.backend = platform_default

    @staticmethod
    def _check_vad_chunking_consistency(cfg: PipelineConfig) -> None:
        vad = cfg.vad
        chunking = cfg.chunking
        if (
            vad is not None
            and vad.enabled
            and chunking is not None
            and chunking.enabled
            and vad.max_speech_duration_ms > chunking.max_chunk_seconds * 1000
        ):
            _logger.warning(
                "Inconsistent VAD/chunking durations; chunker may hard-cut mid-word",
                vad_max_speech_duration_ms=vad.max_speech_duration_ms,
                chunking_max_chunk_ms=chunking.max_chunk_seconds * 1000,
            )
