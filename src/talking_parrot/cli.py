from __future__ import annotations

import argparse
import datetime

from talking_parrot.logging_config import setup_logging
from talking_parrot.config.loader import ConfigLoader
from talking_parrot.io.media_hasher import MediaHasher
from talking_parrot.models.media import MediaInfo
from talking_parrot.models.context import PipelineContext
from talking_parrot.models.project_file import ProjectFile
from talking_parrot.pipeline.orchestrator import PipelineOrchestrator
from talking_parrot.io.project_writer import ProjectFileWriter


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(
        prog="talking-parrot",
        description="Subtitle generation pipeline",
    )
    parser.add_argument("input", help="Path to the media file")
    parser.add_argument(
        "--config", required=True, help="Path to the pipeline YAML config"
    )
    parser.add_argument("--output", required=True, help="Path for the output JSON file")
    args = parser.parse_args()

    cfg = ConfigLoader.load(args.config)

    sha256 = MediaHasher.hash(args.input)
    media_info = MediaInfo(path=args.input, duration_ms=0, sha256=sha256)

    ctx = PipelineContext(config=cfg, media_info=media_info)
    orchestrator = PipelineOrchestrator([])
    ctx = orchestrator.run(ctx)

    project_file = ProjectFile(
        version="0.1.0",
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        media={
            "path": media_info.path,
            "sha256": media_info.sha256,
            "duration_ms": media_info.duration_ms,
        },
        config=cfg.model_dump(),
        vad_segments=ctx.vad_segments,
        transcription_results=ctx.transcription_results,
        subtitles=ctx.subtitles,
    )

    ProjectFileWriter.write(project_file, args.output)


if __name__ == "__main__":
    main()
