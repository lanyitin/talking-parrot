## ADDED Requirements

### Requirement: PipelineStage interface

The system SHALL provide a `PipelineStage` abstract interface that every pipeline stage implements. The interface SHALL expose a read-only `name` property of type `str` and a single method `process(ctx: PipelineContext) -> PipelineContext`. Implementations SHALL NOT mutate the input context; they MUST return a new context (or the same instance unchanged when the stage is disabled in configuration).

#### Scenario: Disabled stage returns context unchanged

- **WHEN** a stage's corresponding section in `PipelineConfig` has `enabled = False` and `process(ctx)` is invoked
- **THEN** the stage MUST return the input `ctx` unchanged (same object identity or a structurally equal copy) and MUST NOT perform any side effects (no I/O, no model loading, no log output beyond a single DEBUG line)

#### Scenario: Enabled stage produces new context

- **WHEN** a concrete stage is enabled and `process(ctx)` runs to completion
- **THEN** the returned context MUST be a new `PipelineContext` instance (frozen dataclass; produced via `dataclasses.replace`) with the stage's output fields populated and all upstream fields preserved

### Requirement: PipelineContext immutability and field semantics

The `PipelineContext` SHALL be a `@dataclass(frozen=True)` with the fields specified in `pipeline-data-models`. Stages SHALL update fields exclusively via `dataclasses.replace`. Stages MUST NOT mutate any list, dict, or nested object reachable from the context.

#### Scenario: Replacing a list field

- **WHEN** a stage produces an updated `vad_segments` list
- **THEN** the stage MUST return `dataclasses.replace(ctx, vad_segments=new_list)` and MUST NOT call `ctx.vad_segments.append(...)`

### Requirement: PipelineOrchestrator drives stages in order

The system SHALL provide a `PipelineOrchestrator` that accepts an ordered sequence of `PipelineStage` instances at construction time and a `run(ctx: PipelineContext) -> PipelineContext` method that invokes each stage's `process()` in order, threading the returned context into the next stage.

#### Scenario: Stage ordering preserved

- **WHEN** an orchestrator is constructed with stages `[A, B, C]` and `run(ctx0)` is called
- **THEN** the orchestrator MUST invoke `A.process(ctx0) -> ctx1`, then `B.process(ctx1) -> ctx2`, then `C.process(ctx2) -> ctx3`, and return `ctx3`

#### Scenario: Stage exception aborts pipeline

- **WHEN** any stage's `process()` raises an exception
- **THEN** the orchestrator MUST propagate the exception unmodified and MUST NOT invoke subsequent stages

### Requirement: Orchestrator owns no business logic

The `PipelineOrchestrator` SHALL contain no stage-specific logic, no decision-making about which stages run, no audio reading, and no configuration validation. Its sole responsibility is sequencing.

#### Scenario: Orchestrator inspection

- **WHEN** the `PipelineOrchestrator` source is reviewed
- **THEN** it MUST NOT import any module under `talking_parrot.vad`, `talking_parrot.transcription`, `talking_parrot.alignment`, `talking_parrot.post_processing`, `talking_parrot.export`, `talking_parrot.expression`, or `talking_parrot.io`
