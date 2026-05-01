from __future__ import annotations

import logging
import pydantic
import yaml
import structlog

from talking_parrot.config.models import PipelineConfig

log = structlog.get_logger()
_logger = logging.getLogger(__name__)


class ConfigLoader:
    @staticmethod
    def load(path: str) -> PipelineConfig:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        cfg = PipelineConfig.model_validate(raw)

        if cfg.transcribing[0].condition != "true":
            raise pydantic.ValidationError.from_exception_data(
                title="PipelineConfig",
                input_type="python",
                line_errors=[
                    {
                        "type": "value_error",
                        "loc": ("transcribing", 0, "condition"),
                        "msg": 'First transcribing step condition must be "true"',
                        "input": cfg.transcribing[0].condition,
                        "ctx": {"error": ValueError('must be "true"')},
                    }
                ],
            )

        ConfigLoader._check_vad_chunking_consistency(cfg)

        return cfg

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
                "Inconsistent VAD/chunking durations: vad.max_speech_duration_ms=%d > "
                "chunking.max_chunk_seconds*1000=%d. "
                "The chunker may have to perform a hard cut mid-word.",
                vad.max_speech_duration_ms,
                chunking.max_chunk_seconds * 1000,
            )
