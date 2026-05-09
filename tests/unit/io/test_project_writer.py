import json

from talking_parrot.models.project_file import ProjectFile
from talking_parrot.models.context import GranularityPreference
from talking_parrot.io.project_writer import ProjectFileWriter


def _make_project_file(**kwargs):
    defaults = dict(
        version="0.1.0",
        created_at="2026-01-01T00:00:00Z",
        media={"path": "/tmp/t.mp4", "sha256": "abc", "duration_ms": 1000},
        config={"transcribing": [{"condition": "true", "backend": "faster-whisper"}]},
    )
    defaults.update(kwargs)
    return ProjectFile(**defaults)


class TestProjectFileWriter:
    def test_writes_valid_json(self, tmp_path):
        pf = _make_project_file()
        out = tmp_path / "out.json"
        ProjectFileWriter.write(pf, str(out))
        content = out.read_text()
        parsed = json.loads(content)
        assert parsed is not None

    def test_enum_serialized_by_name(self, tmp_path):
        pf = _make_project_file(
            config={"align": {"granularity": GranularityPreference.AUTO}}
        )
        out = tmp_path / "out.json"
        ProjectFileWriter.write(pf, str(out))
        content = out.read_text()
        assert '"AUTO"' in content
        assert '"2"' not in content

    def test_datetime_string_preserved(self, tmp_path):
        pf = _make_project_file(created_at="2026-05-01T12:00:00Z")
        out = tmp_path / "out.json"
        ProjectFileWriter.write(pf, str(out))
        data = json.loads(out.read_text())
        assert data["created_at"] == "2026-05-01T12:00:00Z"

    def test_project_file_vad_frames_round_trip(self, tmp_path):
        """``vad_frames`` items round-trip through writer with ``backend`` tag."""
        from talking_parrot.models.vad import RawVadFrame

        pf = _make_project_file(
            vad_frames=[
                RawVadFrame(time_ms=0, prob=0.9, backend="silero_vad"),
                RawVadFrame(time_ms=16, prob=0.85, backend="ten_vad"),
                RawVadFrame(time_ms=32, prob=0.875, backend="composite"),
            ]
        )
        out = tmp_path / "out.json"
        ProjectFileWriter.write(pf, str(out))
        data = json.loads(out.read_text())
        assert "vad_frames" in data
        assert len(data["vad_frames"]) == 3
        assert data["vad_frames"][0] == {
            "time_ms": 0,
            "prob": 0.9,
            "backend": "silero_vad",
        }
        assert data["vad_frames"][1]["backend"] == "ten_vad"
        assert data["vad_frames"][2]["backend"] == "composite"
