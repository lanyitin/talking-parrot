## Problem

`cli.main` constructs `MediaInfo(path=args.input, duration_ms=0, sha256=sha256)` with `duration_ms` hardcoded to `0` (`src/talking_parrot/cli.py:188`). The VAD stage's padding step caps each segment's end at `min(audio_duration_ms, end + speech_pad_ms)` (`src/talking_parrot/stages/vad_stage.py:389`); with `audio_duration_ms == 0` every segment collapses to `[0, 0]` after padding. The result is zero VAD segments → zero transcriptions → zero subtitles, AND no error is raised. The pipeline appears to "succeed" while producing an empty SRT file. This was observed running `talking-parrot --config config.example.yaml --output sample1.srt sample1.mp3`: the project JSON contained empty `vad_segments`, `transcription_results`, and `subtitles`.

## Root Cause

`MediaInfo.duration_ms` is never populated from the actual media file. The CLI was wired with a placeholder `0` and no subsequent step writes the real value back. `FfmpegAudioReader` already probes duration internally (`_probe_duration_ms`) but it is only constructed inside `AlignmentStage` and its result is not surfaced to `MediaInfo` before VAD runs.

## Proposed Solution

1. Expose a public `duration_ms` property on `FfmpegAudioReader` (it already stores `self._duration_ms` from `_probe_duration_ms`).
2. In `cli.main`, probe the input media's duration **before** constructing `MediaInfo` and pass the real value:
   - Construct a temporary `FfmpegAudioReader(args.input)` and read `.duration_ms`. (Reuse later in `_build_stages` for `AlignmentStage` when `cfg.align is not None` so the file is probed only once.)
3. Treat a probe failure (e.g. ffmpeg cannot read the file) as a hard error: `cli.main` SHALL exit non-zero with a clear message before running the pipeline. No silent fallback to `0`.

## Non-Goals

- Reading the full audio at CLI start; only the duration needs probing.
- Adding a separate `MediaProber` abstraction. `FfmpegAudioReader` already encapsulates ffmpeg probing; introducing a parallel API is unnecessary.
- Changing `VadStage._apply_padding` to be defensive against `duration_ms == 0`. The fix is to populate the real value upstream; downstream defensive caps would mask legitimate misuse and could hide future regressions of the same bug.
- Changing `MediaInfo.duration_ms`'s type or making it optional. It remains a required `int`; CLI just computes it correctly.

## Success Criteria

- Running `talking-parrot --config <cfg with VAD enabled> --output <out>.srt <input>.mp3` against a non-empty audio file SHALL produce a non-empty SRT file (assuming the audio contains speech and transcription succeeds).
- `MediaInfo.duration_ms` written into the project-JSON `media.duration_ms` field equals the audio's real duration in milliseconds, within rounding tolerance (≤ 1 ms) of `ffmpeg.probe`'s reported value.
- Passing a non-existent or unreadable input file SHALL cause `cli.main` to exit non-zero with an error mentioning the file path, BEFORE any pipeline stage runs.
- No existing test in `tests/unit/cli/test_cli_wiring.py` regresses.

## Impact

- Affected specs: `pipeline-end-to-end-wiring` (delta — adds a requirement for media-duration probing).
- Affected code:
  - Modified: `src/talking_parrot/cli.py` (probe duration before building `MediaInfo`)
  - Modified: `src/talking_parrot/io/audio_decoder.py` (expose public `duration_ms` property)
  - Modified: `tests/unit/cli/test_cli_wiring.py` (existing tests stub `FfmpegAudioReader`; verify duration is read; add probe-failure test)
