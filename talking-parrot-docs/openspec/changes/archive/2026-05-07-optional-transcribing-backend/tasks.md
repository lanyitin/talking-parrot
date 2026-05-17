## 1. Schema Change

- [x] 1.1 In src/talking_parrot/config/models.py, change `TranscribingStep.backend` from required `str` to `Optional[str] = None`, keeping `extra: forbid` and existing fields untouched. This implements the schema half of "TranscribingStep.backend is optional with platform-aware default".

## 2. Loader Resolution

- [x] 2.1 In src/talking_parrot/config/loader.py, after `PipelineConfig.model_validate(raw)` succeeds, iterate `cfg.transcribing` and for any step where `backend is None` assign `TranscriptionBackendFactory.default_for_platform()` (import from `talking_parrot.transcription.factory`). Preserve explicit non-empty string values unchanged. This satisfies the resolution half of "TranscribingStep.backend is optional with platform-aware default" and ensures every returned `TranscribingStep.backend` is a non-empty `str`.
- [x] 2.2 Confirm the existing `TRANSCRIPTION_BACKEND` env-var override path inside `TranscriptionBackendFactory.create()` is NOT touched (loader resolution must not pre-empt the runtime env override).

## 3. Example Config

- [x] 3.1 [P] Update config.example.yaml: remove the `backend: faster-whisper` line from the fallback (`condition: "true"`) transcribing step so the example demonstrates the new platform-default behavior. Keep the explicit `backend:` on the second cascade step (e.g., `condition: "avg_logprob < -1.0"`) to show that explicit values are still honoured.

## 4. Tests

- [x] 4.1 [P] In tests/unit/config/test_models.py, add a test that `TranscribingStep(condition="true")` constructs successfully with `backend is None` (no `pydantic.ValidationError`).
- [x] 4.2 In tests/unit/config/test_loader.py, add a test for the `Omitted backend resolves to platform default` scenario: monkeypatch `TranscriptionBackendFactory.default_for_platform` (or the `sys.platform` / `platform.machine` it reads) to a known value, load YAML that omits `backend:`, and assert `cfg.transcribing[0].backend` equals the patched default.
- [x] 4.3 In tests/unit/config/test_loader.py, add a test for the `Explicit backend value preserved` scenario: even when `default_for_platform()` would return `mlx-whisper`, an explicit `backend: faster-whisper` MUST survive load unchanged.
- [x] 4.4 In tests/unit/config/test_loader.py, add a test for the `Null backend resolves to platform default` scenario: YAML with `backend: null` MUST be treated identically to the omitted case.
- [x] 4.5 In tests/unit/config/test_loader.py, add a test for the `Mixed cascade with one omitted backend` scenario: two-step cascade where step 0 omits `backend:` (resolved to platform default) and step 1 specifies an explicit value (preserved verbatim).
- [x] 4.6 [P] Cover the `platform resolution table` example in either test_loader.py or test_models.py by parametrising over `(sys.platform, platform.machine)` pairs against the expected resolved backend.

## 5. Verification

- [x] 5.1 Run `uv run ruff format .` and `uv run ruff check .` — must report zero errors.
- [x] 5.2 Run `uv run pytest` — full suite must be 100% green; pay attention to existing `test_loader.py` and `test_models.py` tests that may have asserted `backend` was required.
