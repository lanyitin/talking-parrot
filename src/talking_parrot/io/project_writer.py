from __future__ import annotations

import dataclasses
import enum
import json
from pathlib import PurePath

from talking_parrot.models.project_file import ProjectFile


def _default_encoder(obj):
    """JSON encoder for enums, dataclasses, and ``pathlib`` paths."""
    if isinstance(obj, enum.Enum):
        return obj.name
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, PurePath):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class ProjectFileWriter:
    @staticmethod
    def write(project_file: ProjectFile, output_path: str) -> None:
        data = dataclasses.asdict(project_file)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, default=_default_encoder, ensure_ascii=False, indent=2)
