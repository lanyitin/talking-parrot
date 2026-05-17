## Tasks

### 1. Convert call sites in leaf modules (parallel)

- [x] [P] Convert %-format and `extra=` log calls to kwargs in `src/talking_parrot/io/subtitle_export/base.py`, `srt.py`, `webvtt.py`, `factory.py`
- [x] [P] Convert %-format and `extra=` log calls to kwargs in `src/talking_parrot/post_processing/time_based.py`, `word_boundary.py`, `character_boundary.py`, `factory.py`
- [x] [P] Convert %-format and `extra=` log calls to kwargs in `src/talking_parrot/transcription/faster_whisper_backend.py` and `mlx_whisper_backend.py`
- [x] [P] Convert %-format and `extra=` log calls to kwargs in `src/talking_parrot/alignment/english_backend.py` and `japanese_backend.py`
- [x] [P] Convert %-format and `extra=` log calls to kwargs in `src/talking_parrot/vad/silero_vad.py` and `ten_vad.py`
- [x] [P] Convert %-format and `extra=` log calls to kwargs in `src/talking_parrot/config/loader.py`

### 2. Convert call sites in pipeline stages (parallel)

- [x] [P] Convert log calls in `src/talking_parrot/stages/alignment_stage.py` to kwargs (event message + structured fields like `chunk_index`, `granularity`, `language`, `error`)
- [x] [P] Convert log calls in `src/talking_parrot/stages/transcription_stage.py` to kwargs (drop `extra={...}` payloads in favor of direct kwargs; convert `"transcription step %d failed: ..."` to event + `step_index`/`backend`/`model`/`error`)
- [x] [P] Convert log calls in `src/talking_parrot/stages/post_processing_stage.py` and `chunking_stage.py` to kwargs
- [x] [P] Convert log calls in `src/talking_parrot/stages/vad_stage.py` to kwargs

### 3. Update tests that assert on rendered messages

- [x] Update `tests/unit/stages/test_alignment_stage.py` assertions that check substrings of formatted messages (e.g. `"alignment failed for chunk 0"`) to assert on the static event name plus structured fields exposed on `caplog.records[i].__dict__`
- [x] Update `tests/unit/stages/test_transcription_stage.py` similarly for the converted call sites

### 4. Remove now-unused processor and verify

- [x] Remove `structlog.stdlib.PositionalArgumentsFormatter()` from the processor list in `src/talking_parrot/logging_config.py` (both `_configure_structlog` invocations)
- [x] Run `uv run pytest` — all tests must pass with zero failures
- [x] Run `uv run ruff check .` and `uv run ruff format --check .` — must report zero errors
- [x] Grep verification: `grep -rnE 'logger\.[a-z]+\([^)]*%[rsdf]' src/` returns no results, and `grep -rn 'extra={' src/` returns no results
