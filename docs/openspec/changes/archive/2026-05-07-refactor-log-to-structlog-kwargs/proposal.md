## Summary

Convert all remaining stdlib-logging idioms in `src/` (`%`-formatted message strings with positional args, and `extra={...}` payloads) to structlog's idiomatic kwargs style, so the codebase consistently uses one logging API.

## Motivation

The recent migration from stdlib `logging` to `structlog` left source code in a mixed state: structlog is configured to route through stdlib (preserving `caplog`), and `PositionalArgumentsFormatter` is wired in so legacy `logger.warning("msg %d", x)` calls still render. But these calls are now anti-idiomatic — structlog's value is structured key/value pairs, which `%`-formatting and `extra={...}` defeat. Standardizing on kwargs:

- Makes log records machine-parseable (each field is a key in the event dict, not embedded in a formatted string).
- Removes the need for `PositionalArgumentsFormatter` and the cognitive overhead of two logging styles.
- Aligns the project with structlog's documented idiom.

## Proposed Solution

For every `logger.<level>(...)` call site under `src/talking_parrot/`:

1. **`%`-formatted strings with positional args** → split the format string into a static event message plus structured kwargs.
   - Before: `logger.warning("alignment failed for chunk %d: %s", idx, exc)`
   - After: `logger.warning("alignment failed for chunk", chunk_index=idx, error=str(exc))`

2. **`extra={...}` payloads** → unpack the dict into kwargs directly.
   - Before: `logger.debug("step 0 invoked", extra={"chunk_index": chunk.index, "backend": step.backend})`
   - After: `logger.debug("step 0 invoked", chunk_index=chunk.index, backend=step.backend)`

3. **Static-string log calls** (no args, no `extra=`) — leave unchanged.

After conversion, remove `structlog.stdlib.PositionalArgumentsFormatter()` from the structlog processor chain in `logging_config.py` since no remaining call site relies on it.

Update tests that assert on rendered log messages (e.g. substring matches like `"alignment failed for chunk 0"` in `caplog`) to assert on the event message and structured fields instead — `caplog` records expose the bound kwargs via `record.__dict__` once structlog routes through stdlib.

## Non-Goals

- Adding new log call sites or new log levels.
- Changing the structlog processor chain beyond removing `PositionalArgumentsFormatter`.
- Touching test files that already assert on structlog kwargs or that don't inspect log content.
- Reworking `logger = structlog.get_logger(__name__)` acquisition pattern.
- Introducing a custom renderer or JSON output.

## Alternatives Considered

- **Keep `PositionalArgumentsFormatter` indefinitely**: rejected — dual-style logging is a long-term maintenance tax and obscures structlog's structured-data value.
- **Mechanical regex-only conversion**: rejected — many call sites need a meaningful event-name split (the static prefix vs. the dynamic field names) that requires per-site judgment.

## Impact

- Affected specs: none — this is a code-style/internal refactor with no spec-level behavior change.
- Affected code:
  - Modified:
    - src/talking_parrot/logging_config.py
    - src/talking_parrot/config/loader.py
    - src/talking_parrot/io/subtitle_export/base.py
    - src/talking_parrot/io/subtitle_export/srt.py
    - src/talking_parrot/io/subtitle_export/webvtt.py
    - src/talking_parrot/io/subtitle_export/factory.py
    - src/talking_parrot/post_processing/time_based.py
    - src/talking_parrot/post_processing/word_boundary.py
    - src/talking_parrot/post_processing/character_boundary.py
    - src/talking_parrot/post_processing/factory.py
    - src/talking_parrot/transcription/faster_whisper_backend.py
    - src/talking_parrot/transcription/mlx_whisper_backend.py
    - src/talking_parrot/alignment/english_backend.py
    - src/talking_parrot/alignment/japanese_backend.py
    - src/talking_parrot/stages/alignment_stage.py
    - src/talking_parrot/stages/transcription_stage.py
    - src/talking_parrot/stages/post_processing_stage.py
    - src/talking_parrot/stages/chunking_stage.py
    - src/talking_parrot/stages/vad_stage.py
    - src/talking_parrot/vad/silero_vad.py
    - src/talking_parrot/vad/ten_vad.py
    - tests/unit/stages/test_alignment_stage.py
    - tests/unit/stages/test_transcription_stage.py
  - New: (none)
  - Removed: (none)
