## 1. Expose duration on FfmpegAudioReader

- [x] 1.1 In `src/talking_parrot/io/audio_decoder.py`, add a public `duration_ms` property on `FfmpegAudioReader` that returns `self._duration_ms` (the value already populated by `_probe_duration_ms` during `__init__`). Add a one-line docstring stating the value is in milliseconds and was probed via `ffmpeg.probe`.
- [x] 1.2 Add a unit test in `tests/unit/io/` (new file `test_audio_decoder.py` if none exists) that constructs `FfmpegAudioReader` against a small fixture audio file (or monkeypatches `ffmpeg.probe`) and asserts `reader.duration_ms` returns the expected integer milliseconds. Implements the "cli.py populates MediaInfo.duration_ms from the input file" requirement at the reader layer.

## 2. Probe duration in cli.main

- [x] 2.1 In `src/talking_parrot/cli.py`, after `ConfigLoader.load` returns and before `MediaInfo(...)` is constructed, instantiate `FfmpegAudioReader(args.input)` and read `.duration_ms` into a local variable. Use that value (instead of the hardcoded `0`) when building `MediaInfo`.
- [x] 2.2 Wrap the probe in a `try/except` (catching `ffmpeg.Error`, `KeyError`, `ValueError`, `FileNotFoundError`) and on failure call `parser.error(f"failed to probe input audio {args.input!r}: ...")` so the CLI exits non-zero before any pipeline stage runs. Implements the probe-failure half of the "cli.py populates MediaInfo.duration_ms from the input file" requirement.
- [x] 2.3 If `cfg.align is not None`, reuse the already-constructed `FfmpegAudioReader` instance for `AlignmentStage` instead of constructing a second one. Pass it through `_build_stages` (extend its signature with an optional `audio_reader` parameter that defaults to `None` for backward-compat in tests; when omitted, fall back to constructing a new reader as today). Avoids probing the file twice.

## 3. Tests

- [x] 3.1 [P] In `tests/unit/cli/test_cli_wiring.py`, add a CLI test that monkeypatches `talking_parrot.cli.FfmpegAudioReader` so `.duration_ms` returns `12345` and asserts the project-JSON written to disk contains `media.duration_ms == 12345`. Verifies the "A valid media file populates the real duration" scenario.
- [x] 3.2 [P] Add a CLI test that monkeypatches `talking_parrot.cli.FfmpegAudioReader.__init__` to raise (e.g. `FileNotFoundError`) and asserts: `cli.main` exits non-zero (`pytest.raises(SystemExit)`), the project-JSON is NOT written, and `PipelineOrchestrator.run` is not called. Verifies the "A probe failure exits before the pipeline runs" scenario.
- [x] 3.3 Audit existing tests in `tests/unit/cli/test_cli_wiring.py` that already patch heavy stage constructors. Where they previously relied on `FfmpegAudioReader` only being constructed inside `_build_stages`, ensure the new top-level construction is also patched (typically via `patch("talking_parrot.cli.FfmpegAudioReader")` returning a mock whose `duration_ms` attribute is a small integer). Do not weaken any existing assertion; add the patch alongside the existing `MediaHasher.hash` patch.

## 4. Verify

- [x] 4.1 Run `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .` and confirm zero failures and zero warnings.
- [x] 4.2 Manually re-run `uv run talking-parrot --config config.example.yaml --output sample1.srt <a real audio file>` and confirm `sample1.srt` is non-empty (assuming the audio contains speech). Confirms the success criterion from the proposal.
