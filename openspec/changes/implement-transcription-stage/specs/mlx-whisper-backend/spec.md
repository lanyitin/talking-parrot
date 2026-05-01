## ADDED Requirements

### Requirement: MLXWhisperBackend wraps mlx_whisper.transcribe

The system SHALL provide `MLXWhisperBackend(TranscriptionBackend)` whose `name` property returns the literal string `"mlx-whisper"` and whose `transcribe()` method drives `mlx_whisper.transcribe`.

The backend SHALL lazy-import `mlx_whisper` on the first `transcribe()` call. If the import fails, the backend MUST raise `ImportError` whose message names the install extra `talking-parrot[mlx]`.

#### Scenario: Missing optional dependency raises actionable error

- **WHEN** `MLXWhisperBackend.transcribe()` is called and `mlx_whisper` is not importable
- **THEN** the call MUST raise `ImportError` whose message contains the substring `talking-parrot[mlx]`

### Requirement: MLXWhisperBackend enforces Apple Silicon macOS at construction

`MLXWhisperBackend.__init__` SHALL inspect `sys.platform` and `platform.machine()`. If `sys.platform != "darwin"` OR `platform.machine() != "arm64"`, the constructor MUST raise `RuntimeError` whose message contains the substring `Apple Silicon macOS`.

#### Scenario: Linux instantiation rejected

- **GIVEN** `sys.platform` is patched to `"linux"`
- **WHEN** `MLXWhisperBackend()` is invoked
- **THEN** the call MUST raise `RuntimeError` containing `"Apple Silicon macOS"`

#### Scenario: Intel macOS instantiation rejected

- **GIVEN** `sys.platform == "darwin"` and `platform.machine()` is patched to `"x86_64"`
- **WHEN** `MLXWhisperBackend()` is invoked
- **THEN** the call MUST raise `RuntimeError` containing `"Apple Silicon macOS"`

### Requirement: MLXWhisperBackend decodes chunk window via audio-io

`MLXWhisperBackend.transcribe()` SHALL load the source audio file, extract the float32 sample window covering `[chunk.start_ms, chunk.end_ms]` using the project's `audio-io` helpers, and pass that numpy array to `mlx_whisper.transcribe(audio_array, path_or_hf_repo=model, language=language)`.

The backend SHALL pass the supplied `model` string verbatim to `path_or_hf_repo` without rewriting (so e.g. `"large-v3"` is forwarded as-is and any HF-repo translation is the caller's responsibility).

#### Scenario: Chunk window forwarded as numpy array

- **GIVEN** a chunk with `start_ms=2000`, `end_ms=4000` and a mocked `mlx_whisper.transcribe`
- **WHEN** `transcribe()` is called
- **THEN** `mlx_whisper.transcribe` MUST be called with a numpy array whose length equals `(4000 - 2000) * sample_rate / 1000` samples
- **AND** the `path_or_hf_repo` keyword MUST equal the `model` argument unchanged

### Requirement: MLXWhisperBackend assembles TranscriptionResult per the backend contract

`MLXWhisperBackend.transcribe()` SHALL iterate the `segments` field of the value returned by `mlx_whisper.transcribe`, joining segment `text` values with a single space and stripping the result for `TranscriptionResult.text`. It SHALL compute `TranscriptionMetrics` using the same rules declared in `transcription-backend` (weighted-mean `avg_logprob` and `compression_ratio`, max `no_speech_prob`, locally-computed `repetition_ratio`). It SHALL set `language` to the `language` field of the returned dict when present, otherwise to the supplied `language` argument.

#### Scenario: Library-provided language surfaced

- **GIVEN** `mlx_whisper.transcribe(...)` returns a dict with `language="en"`
- **WHEN** `transcribe()` is called with `language=None`
- **THEN** the returned `TranscriptionResult.language` MUST equal `"en"`
