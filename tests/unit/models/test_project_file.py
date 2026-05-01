import inspect
from talking_parrot.models.project_file import ProjectFile


class TestProjectFileIsPureData:
    def test_no_custom_methods(self):
        auto_generated = {
            "__init__",
            "__repr__",
            "__eq__",
            "__hash__",
            "__dataclass_fields__",
            "__dataclass_params__",
            "__annotations__",
            "__doc__",
            "__module__",
            "__dict__",
            "__weakref__",
            "__match_args__",
            "__replace__",
        }
        user_defined = {
            name
            for name, member in inspect.getmembers(
                ProjectFile, predicate=inspect.isfunction
            )
            if name not in auto_generated
        }
        forbidden = {"to_json", "save", "write"}
        assert not user_defined.intersection(forbidden), (
            f"ProjectFile must not define: {user_defined.intersection(forbidden)}"
        )

    def test_has_required_fields(self):
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(ProjectFile)}
        required = {
            "version",
            "created_at",
            "media",
            "config",
            "vad_segments",
            "transcription_results",
            "subtitles",
        }
        assert required.issubset(field_names)
