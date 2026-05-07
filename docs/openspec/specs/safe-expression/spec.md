# safe-expression Specification

## Purpose

TBD - created by archiving change 'bootstrap-pipeline-foundation'. Update Purpose after archive.

## Requirements

### Requirement: SafeExpressionEvaluator forbids eval and exec

The `SafeExpressionEvaluator` base class SHALL implement expression evaluation using the Python standard-library `ast` module with a whitelist node walker. The implementation MUST NOT call `eval()`, `exec()`, `compile(..., mode="exec")`, or any third-party library that exposes `eval`/`exec` semantics.

#### Scenario: Source code review

- **WHEN** the source files of `SafeExpressionEvaluator` and its subclasses are inspected
- **THEN** they MUST NOT contain any call to `eval(`, `exec(`, or `__import__(`


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: Whitelist enforcement is default-deny

The base evaluator SHALL traverse the AST with a default behaviour of raising `ExpressionError` for any node type not explicitly whitelisted by the subclass. Subclasses MUST be unable to disable the default-deny behaviour; they may only extend the allowed set.

#### Scenario: Disallowed node rejected

- **WHEN** any subclass evaluates an expression containing a `Call`, `Attribute`, `Subscript`, `Lambda`, `ListComp`, `Import`, `Assign`, `Name` referring to a builtin (`__builtins__`, `open`), or any other non-whitelisted node
- **THEN** evaluation MUST raise `ExpressionError` before producing a value

##### Example: rejected expressions

| Expression | Rejected because |
| ---------- | ---------------- |
| `__import__("os").system("ls")` | `Call` and `Subscript` not in any whitelist |
| `(lambda x: x)(1)` | `Lambda` and `Call` not in any whitelist |
| `prob.upper()` | `Attribute` and `Call` not in any whitelist |
| `[x for x in range(10)]` | `ListComp`, `Call`, and `Name("range")` not in any whitelist |


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: ExpressionError on undefined identifiers

When an expression references an identifier (`Name` node) that is not present in the supplied `variables` mapping, evaluation MUST raise `ExpressionError`. The error message MUST identify the undefined name.

#### Scenario: Undefined variable

- **WHEN** `evaluator.evaluate("a + b", variables={"a": 1.0})` is called (no `b`)
- **THEN** the call MUST raise `ExpressionError` whose message contains the string `"b"`


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: Subclass-declared whitelists

Subclasses SHALL declare their allowed operators and literal types via the read-only properties `allowed_operators: set[OperatorKind]` and `allowed_literal_types: set[type]`. The base walker MUST consult these properties when validating `BinOp`, `UnaryOp`, `BoolOp`, `Compare`, and `Constant` nodes.

#### Scenario: Operator outside subclass whitelist rejected

- **WHEN** a subclass declares `allowed_operators = {ADD, SUB}` and evaluates `"a * b"`
- **THEN** evaluation MUST raise `ExpressionError` identifying the disallowed operator


<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->

---
### Requirement: ExpressionError type hierarchy

The system SHALL define `ExpressionError` as a subclass of `Exception` and SHALL define `ConditionError` and `FormulaError` as subclasses of `ExpressionError`. Callers can catch all three by catching `ExpressionError`.

#### Scenario: Subclass relationship

- **WHEN** `issubclass(ConditionError, ExpressionError)` and `issubclass(FormulaError, ExpressionError)` are evaluated
- **THEN** both expressions MUST return `True`

<!-- @trace
source: bootstrap-pipeline-foundation
updated: 2026-05-01
code:
  - .python-version
  - .spectra.yaml
  - src/talking_parrot/models/__pycache__/media.cpython-313.pyc
  - src/talking_parrot/models/vad.py
  - mise.toml
  - fnox.toml
  - src/talking_parrot/logging_config.py
  - tests/unit/config/__init__.py
  - src/talking_parrot/models/context.py
  - tests/unit/models/__init__.py
  - tests/__init__.py
  - src/talking_parrot/expression/__pycache__/__init__.cpython-313.pyc
  - uv.lock
  - pyproject.toml
  - src/talking_parrot/models/subtitle.py
  - tests/unit/io/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/cli.py
  - tests/unit/__init__.py
  - src/talking_parrot/models/__pycache__/vad.cpython-313.pyc
  - tests/unit/io/__init__.py
  - src/talking_parrot/io/__pycache__/audio_decoder.cpython-313.pyc
  - src/talking_parrot/pipeline/orchestrator.py
  - src/talking_parrot/config/models.py
  - src/talking_parrot/__pycache__/cli.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/formula.cpython-313.pyc
  - src/talking_parrot/expression/__init__.py
  - src/talking_parrot/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/stages/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__pycache__/logging_config.cpython-313.pyc
  - src/talking_parrot/pipeline/__pycache__/orchestrator.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/subtitle.cpython-313.pyc
  - tests/unit/pipeline/__init__.py
  - tests/unit/pipeline/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/media_hasher.cpython-313.pyc
  - src/talking_parrot/io/__init__.py
  - src/talking_parrot/models/project_file.py
  - src/talking_parrot/models/__init__.py
  - src/talking_parrot/io/__pycache__/project_writer.cpython-313.pyc
  - tests/unit/stages/__pycache__/__init__.cpython-313.pyc
  - tests/integration/__init__.py
  - src/talking_parrot/expression/__pycache__/condition.cpython-313.pyc
  - src/talking_parrot/io/__pycache__/audio_reader.cpython-313.pyc
  - src/talking_parrot/io/media_hasher.py
  - src/talking_parrot/config/__init__.py
  - src/talking_parrot/models/__pycache__/context.cpython-313.pyc
  - src/talking_parrot/models/transcription.py
  - src/talking_parrot/expression/base.py
  - src/talking_parrot/models/__pycache__/project_file.cpython-313.pyc
  - src/talking_parrot/io/audio_decoder.py
  - tests/unit/__pycache__/__init__.cpython-313.pyc
  - tests/unit/expression/__init__.py
  - tests/unit/models/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/__init__.py
  - src/talking_parrot/io/project_writer.py
  - src/talking_parrot/models/media.py
  - CLAUDE.md
  - src/talking_parrot/models/__pycache__/chunk.cpython-313.pyc
  - src/talking_parrot/models/__pycache__/transcription.cpython-313.pyc
  - src/talking_parrot/expression/condition.py
  - src/talking_parrot/expression/formula.py
  - src/talking_parrot/stages/base.py
  - src/talking_parrot/io/audio_reader.py
  - src/talking_parrot/config/__pycache__/models.cpython-313.pyc
  - tests/integration/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/expression/__pycache__/base.cpython-313.pyc
  - tests/unit/expression/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/loader.py
  - src/talking_parrot/stages/__pycache__/base.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/__init__.cpython-313.pyc
  - tests/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/pipeline/__init__.py
  - src/talking_parrot/io/__pycache__/__init__.cpython-313.pyc
  - README.md
  - src/talking_parrot/stages/__init__.py
  - tests/unit/stages/__init__.py
  - src/talking_parrot/models/chunk.py
  - tests/unit/config/__pycache__/__init__.cpython-313.pyc
  - src/talking_parrot/config/__pycache__/loader.cpython-313.pyc
  - src/talking_parrot/__pycache__/__init__.cpython-313.pyc
tests:
  - tests/unit/models/test_project_file.py
  - tests/unit/config/__pycache__/test_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader_warning.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_audio_reader.py
  - tests/unit/config/test_models.py
  - tests/unit/io/__pycache__/test_media_hasher.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_context.cpython-313-pytest-9.0.3.pyc
  - tests/unit/expression/test_base.py
  - tests/unit/io/__pycache__/test_audio_reader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_data_models.py
  - tests/unit/pipeline/test_orchestrator.py
  - tests/integration/__pycache__/test_pipeline_smoke.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/__pycache__/test_transcription.cpython-313-pytest-9.0.3.pyc
  - tests/unit/models/test_transcription.py
  - tests/unit/test_logging_config.py
  - tests/unit/io/test_project_writer.py
  - tests/unit/__pycache__/test_logging_config.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/__pycache__/test_project_writer.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/__pycache__/test_base.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/test_loader.py
  - tests/unit/models/test_context.py
  - tests/unit/models/__pycache__/test_project_file.cpython-313-pytest-9.0.3.pyc
  - tests/unit/config/__pycache__/test_loader.cpython-313-pytest-9.0.3.pyc
  - tests/unit/stages/test_base.py
  - tests/unit/models/__pycache__/test_data_models.cpython-313-pytest-9.0.3.pyc
  - tests/unit/io/test_media_hasher.py
  - tests/unit/config/test_loader_warning.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/pipeline/__pycache__/test_orchestrator.cpython-313-pytest-9.0.3.pyc
-->