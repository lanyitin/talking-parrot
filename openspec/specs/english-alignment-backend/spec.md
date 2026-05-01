# english-alignment-backend Specification

## Purpose

TBD - created by archiving change 'implement-alignment-stage'. Update Purpose after archive.

## Requirements

### Requirement: EnglishAlignmentBackend wraps torchaudio WAV2VEC2_ASR_BASE_960H

The system SHALL provide `EnglishAlignmentBackend(AlignmentBackend)` whose `language` property returns the literal string `"en"` and whose `granularity` property returns `AlignmentGranularity.WORD`.

The backend SHALL lazy-import `torch` and `torchaudio` on the first `align()` call. If either import fails, the backend MUST raise `ImportError` whose message contains the substring `talking-parrot[align]`.

The backend SHALL load `torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H` exactly once and cache its `model` and `labels` on the instance. The model SHALL be moved to `"cuda"` when `torch.cuda.is_available()` is `True`, otherwise to `"cpu"`.

#### Scenario: Identity properties

- **GIVEN** an instantiated `EnglishAlignmentBackend`
- **WHEN** `language` and `granularity` are read
- **THEN** they MUST equal `"en"` and `AlignmentGranularity.WORD` respectively

#### Scenario: Missing optional dependency raises actionable error

- **WHEN** `EnglishAlignmentBackend.align()` is called and `torchaudio` is not importable
- **THEN** the call MUST raise `ImportError` whose message contains the substring `talking-parrot[align]`

#### Scenario: Model loaded once and cached

- **GIVEN** `torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H` is mocked
- **WHEN** `align()` is called three times on the same backend instance
- **THEN** `bundle.get_model` MUST be invoked exactly once


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: EnglishAlignmentBackend tokenises into characters with pipe word separator

`EnglishAlignmentBackend.align()` SHALL transform the supplied transcript into a character sequence by:
1. Lower-casing the transcript.
2. Replacing each ASCII space `" "` with the pipe character `"|"` (the wav2vec2 word boundary token).
3. Yielding `transcript_tokens = list(transformed)` for the CTC kernel.

#### Scenario: Lowercase and pipe substitution

- **GIVEN** transcript `"Hello World"`
- **WHEN** the backend prepares tokens
- **THEN** `transcript_tokens` MUST equal `['h','e','l','l','o','|','w','o','r','l','d']`


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: EnglishAlignmentBackend groups characters back into words

After the shared CTC kernel returns one `AlignedToken` per character (where `word` holds a single character), `EnglishAlignmentBackend` SHALL group consecutive non-`"|"` characters into word-level `AlignedToken` instances:
- The word's `word` field is the concatenation of the grouped characters.
- The word's `start_ms` is the first character's `start_ms`.
- The word's `end_ms` is the last character's `end_ms`.
- The word's `score` is the arithmetic mean of the grouped characters' `score` values.

`"|"` tokens MUST be discarded (they are word separators only). If two consecutive `"|"` tokens appear, the word boundary still flushes the pending word; an empty pending word MUST NOT produce an output token.

#### Scenario: Two-word grouping

- **GIVEN** the kernel returns characters with timings:
  | char | start_ms | end_ms | score |
  |------|----------|--------|-------|
  | h    | 0        | 50     | 0.9   |
  | i    | 50       | 100    | 0.8   |
  | \|   | 100      | 120    | 0.0   |
  | y    | 120      | 180    | 0.7   |
  | o    | 180      | 220    | 0.6   |
- **WHEN** the backend groups characters back into words
- **THEN** the returned token list MUST equal:
  | word | start_ms | end_ms | score |
  |------|----------|--------|-------|
  | hi   | 0        | 100    | 0.85  |
  | yo   | 120      | 220    | 0.65  |


<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->

---
### Requirement: EnglishAlignmentBackend uses a 50 Hz frame rate

The backend SHALL pass `frame_rate_hz=50.0` to the CTC kernel, matching `WAV2VEC2_ASR_BASE_960H`'s convolutional stride at 16 kHz input.

#### Scenario: Frame rate constant

- **WHEN** the backend invokes the kernel
- **THEN** the `frame_rate_hz` argument MUST equal `50.0`

<!-- @trace
source: implement-alignment-stage
updated: 2026-05-01
code:
  - src/talking_parrot/alignment/english_backend.py
  - src/talking_parrot/alignment/__init__.py
  - src/talking_parrot/alignment/backend.py
  - src/talking_parrot/alignment/japanese_backend.py
  - pyproject.toml
  - tests/unit/alignment/__init__.py
  - src/talking_parrot/stages/__init__.py
  - uv.lock
  - src/talking_parrot/alignment/ctc.py
  - src/talking_parrot/stages/alignment_stage.py
  - src/talking_parrot/alignment/factory.py
tests:
  - tests/unit/alignment/test_japanese_backend.py
  - tests/unit/stages/test_alignment_stage.py
  - tests/unit/alignment/test_backend.py
  - tests/unit/alignment/test_ctc.py
  - tests/unit/alignment/test_english_backend.py
  - tests/unit/alignment/test_factory.py
-->