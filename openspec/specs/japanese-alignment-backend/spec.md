# japanese-alignment-backend Specification

## Purpose

TBD - created by archiving change 'implement-alignment-stage'. Update Purpose after archive.

## Requirements

### Requirement: JapaneseAlignmentBackend wraps HuggingFace Wav2Vec2ForCTC

The system SHALL provide `JapaneseAlignmentBackend(AlignmentBackend)` whose `language` property returns the literal string `"ja"` and whose `granularity` property returns `AlignmentGranularity.CHARACTER`.

The backend SHALL lazy-import `torch` and `transformers` on the first `align()` call. If either import fails, the backend MUST raise `ImportError` whose message contains the substring `talking-parrot[align]`.

The backend SHALL load `Wav2Vec2Processor.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-japanese")` and `Wav2Vec2ForCTC.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-japanese")` exactly once and cache `processor` and `model` on the instance. The model SHALL be moved to `"cuda"` when `torch.cuda.is_available()` is `True`, otherwise to `"cpu"`.

#### Scenario: Identity properties

- **GIVEN** an instantiated `JapaneseAlignmentBackend`
- **WHEN** `language` and `granularity` are read
- **THEN** they MUST equal `"ja"` and `AlignmentGranularity.CHARACTER` respectively

#### Scenario: Missing optional dependency raises actionable error

- **WHEN** `JapaneseAlignmentBackend.align()` is called and `transformers` is not importable
- **THEN** the call MUST raise `ImportError` whose message contains the substring `talking-parrot[align]`

#### Scenario: Model loaded once and cached

- **GIVEN** `Wav2Vec2Processor.from_pretrained` and `Wav2Vec2ForCTC.from_pretrained` are mocked
- **WHEN** `align()` is called three times on the same backend instance
- **THEN** each `from_pretrained` MUST be invoked exactly once


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
### Requirement: JapaneseAlignmentBackend tokenises per Unicode codepoint

`JapaneseAlignmentBackend.align()` SHALL transform the supplied transcript into a character sequence by:
1. Stripping leading and trailing ASCII whitespace.
2. Removing all internal ASCII whitespace characters (`" "`, `"\t"`, `"\n"`).
3. Yielding `transcript_tokens = list(stripped)` so each token is a single Unicode codepoint.

The backend MUST NOT insert a `"|"` separator (Japanese alignment has no word boundary token in this model's vocabulary).

#### Scenario: Whitespace removed before tokenisation

- **GIVEN** transcript `"  こんにちは 世界  "`
- **WHEN** the backend prepares tokens
- **THEN** `transcript_tokens` MUST equal `['こ','ん','に','ち','は','世','界']`


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
### Requirement: JapaneseAlignmentBackend uses processor blank token id

`JapaneseAlignmentBackend.align()` SHALL retrieve `blank_id = self._processor.tokenizer.pad_token_id` from the cached processor and pass it to the CTC kernel. The dictionary passed to the kernel SHALL be `self._processor.tokenizer.get_vocab()` keyed by character.

#### Scenario: Blank id sourced from tokenizer

- **GIVEN** a mocked processor whose `tokenizer.pad_token_id` equals `0`
- **WHEN** the backend invokes the kernel
- **THEN** the `blank_id` argument MUST equal `0`


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
### Requirement: JapaneseAlignmentBackend returns one AlignedToken per character

The backend SHALL return the CTC kernel's output unmodified (no word grouping). Each entry in the returned list MUST correspond to exactly one Unicode codepoint from the prepared transcript, in order.

#### Scenario: Token count equals character count

- **GIVEN** transcript `"こんにちは"` and a successful CTC alignment
- **WHEN** `align()` returns
- **THEN** the returned list MUST contain exactly `5` `AlignedToken` instances and each `token.word` MUST be one of `['こ','ん','に','ち','は']` in that order


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
### Requirement: JapaneseAlignmentBackend uses a 50 Hz frame rate

The backend SHALL pass `frame_rate_hz=50.0` to the CTC kernel, matching the wav2vec2 XLSR convolutional stride at 16 kHz input.

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