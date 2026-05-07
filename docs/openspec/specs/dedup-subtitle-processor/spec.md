# dedup-subtitle-processor Specification

## Purpose

TBD - created by archiving change 'segment-level-postprocessing-pipeline'. Update Purpose after archive.

## Requirements

### Requirement: DedupSubtitleProcessor merges runs of near-duplicate consecutive cues

The system SHALL provide `DedupSubtitleProcessor(SubtitleProcessor)` (in `src/talking_parrot/post_processing/dedup.py`). When `process(subtitles, config)` is called, the processor SHALL walk `subtitles` left-to-right and group any maximal run of two or more consecutive `Subtitle` entries `s_i, s_{i+1}, …, s_{i+k}` that satisfy BOTH:

1. Pairwise text similarity between adjacent members of the run is `>= config.dedup_similarity_threshold` (default `0.9`), measured by `difflib.SequenceMatcher(None, a.text, b.text).ratio()`.
2. The gap between adjacent members of the run is `<= config.dedup_max_gap_ms` (default `600`), where gap is `b.start_ms - a.end_ms`.

Each group SHALL be replaced by a single merged `Subtitle` with:

- `start_ms = run[0].start_ms`
- `end_ms = run[-1].end_ms`
- `text = run[0].text`
- `index` reassigned in the post-merge sequence.

After merging, the processor SHALL renumber `Subtitle.index` 1-based across the returned list.

When `config.dedup_enabled is False`, the processor SHALL return the input list unchanged (same content, original indexes preserved).

#### Scenario: Two near-duplicate cues collapse into one with extended end

- **GIVEN** subtitles `S1(text="hello world", start=1000, end=1500)` and `S2(text="hello worlds", start=1700, end=2200)` with default thresholds
- **WHEN** `DedupSubtitleProcessor.process(...)` runs
- **THEN** the returned list MUST have length 1 with `text="hello world"`, `start_ms=1000`, `end_ms=2200`, and `index=1`

#### Scenario: Gap above threshold prevents merge

- **GIVEN** S1 and S2 identical in text but with gap 800 ms (above the 600 ms default)
- **WHEN** the processor runs
- **THEN** the returned list MUST have length 2 with both subtitles unchanged except for renumbering

#### Scenario: Three-cue run merges into a single cue

- **GIVEN** S1, S2, S3 all with text similarity ≥ 0.9 pairwise and gap ≤ 600 ms
- **WHEN** the processor runs
- **THEN** the returned list MUST have length 1 with `start_ms=S1.start_ms`, `end_ms=S3.end_ms`, `text=S1.text`

#### Scenario: Disabled processor returns input unchanged

- **GIVEN** `config.dedup_enabled is False`
- **WHEN** the processor runs over any list
- **THEN** the returned list MUST be element-wise equal to the input (text, start, end, index unchanged)

##### Example: similarity / gap decision table

| pair                                  | similarity | gap (ms) | merged? | rationale                |
| ------------------------------------- | ---------- | -------- | ------- | ------------------------ |
| `"hello world"` / `"hello worlds"`    | 0.95       | 200      | yes     | both thresholds satisfied|
| `"hello world"` / `"goodbye world"`   | 0.55       | 200      | no      | similarity < 0.9         |
| `"hello world"` / `"hello world"`     | 1.00       | 800      | no      | gap > 600 ms             |
| `"あ"` / `"あ"`                        | 1.00       | 100      | yes     | identical short text     |

<!-- @trace
source: segment-level-postprocessing-pipeline
updated: 2026-05-08
code:
  - src/talking_parrot/post_processing/factory.py
  - sample1.srt
  - src/talking_parrot/stages/transcription_stage.py
  - src/talking_parrot/stages/hallucination_filter_stage.py
  - src/talking_parrot/transcription/mlx_whisper_backend.py
  - src/talking_parrot/transcription/faster_whisper_backend.py
  - src/talking_parrot/transcription/backend.py
  - src/talking_parrot/cli.py
  - src/talking_parrot/post_processing/japanese.py
  - sample1.json
  - src/talking_parrot/config/models.py
  - src/talking_parrot/logging_config.py
  - CLAUDE.md
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/post_processing/dedup.py
tests:
  - tests/unit/stages/test_transcription_stage.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/transcription/test_backend.py
  - tests/unit/transcription/test_mlx_whisper_backend.py
  - tests/unit/transcription/test_faster_whisper_backend.py
  - tests/unit/cli/test_cli_wiring.py
  - tests/unit/config/test_loader.py
  - tests/integration/test_pipeline_smoke.py
  - tests/unit/post_processing/test_japanese.py
  - tests/unit/config/test_models.py
  - tests/unit/post_processing/test_factory.py
  - tests/unit/stages/test_hallucination_filter_stage.py
  - tests/unit/post_processing/test_dedup.py
-->