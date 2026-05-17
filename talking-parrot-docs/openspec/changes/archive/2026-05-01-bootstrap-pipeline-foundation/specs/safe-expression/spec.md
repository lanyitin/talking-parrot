## ADDED Requirements

### Requirement: SafeExpressionEvaluator forbids eval and exec

The `SafeExpressionEvaluator` base class SHALL implement expression evaluation using the Python standard-library `ast` module with a whitelist node walker. The implementation MUST NOT call `eval()`, `exec()`, `compile(..., mode="exec")`, or any third-party library that exposes `eval`/`exec` semantics.

#### Scenario: Source code review

- **WHEN** the source files of `SafeExpressionEvaluator` and its subclasses are inspected
- **THEN** they MUST NOT contain any call to `eval(`, `exec(`, or `__import__(`

### Requirement: Whitelist enforcement is default-deny

The base evaluator SHALL traverse the AST with a default behaviour of raising `ExpressionError` for any node type not explicitly whitelisted by the subclass. Subclasses MUST be unable to disable the default-deny behaviour; they may only extend the allowed set.

#### Scenario: Disallowed node rejected

- **WHEN** any subclass evaluates an expression containing a `Call`, `Attribute`, `Subscript`, `Lambda`, `ListComp`, `Import`, `Assign`, `Name` referring to a builtin (`__builtins__`, `open`), or any other non-whitelisted node
- **THEN** evaluation MUST raise `ExpressionError` before producing a value

##### Example: rejected expressions

| Expression | Rejected because |
| ---------- | ---------------- |
| `__import__("os").system("ls")` | `Call` and `Subscript` not in any whitelist |
| `(lambda x: x)(1)` | `Lambda` and `Call` not in any whitelist |
| `prob.upper()` | `Attribute` and `Call` not in any whitelist |
| `[x for x in range(10)]` | `ListComp`, `Call`, and `Name("range")` not in any whitelist |

### Requirement: ExpressionError on undefined identifiers

When an expression references an identifier (`Name` node) that is not present in the supplied `variables` mapping, evaluation MUST raise `ExpressionError`. The error message MUST identify the undefined name.

#### Scenario: Undefined variable

- **WHEN** `evaluator.evaluate("a + b", variables={"a": 1.0})` is called (no `b`)
- **THEN** the call MUST raise `ExpressionError` whose message contains the string `"b"`

### Requirement: Subclass-declared whitelists

Subclasses SHALL declare their allowed operators and literal types via the read-only properties `allowed_operators: set[OperatorKind]` and `allowed_literal_types: set[type]`. The base walker MUST consult these properties when validating `BinOp`, `UnaryOp`, `BoolOp`, `Compare`, and `Constant` nodes.

#### Scenario: Operator outside subclass whitelist rejected

- **WHEN** a subclass declares `allowed_operators = {ADD, SUB}` and evaluates `"a * b"`
- **THEN** evaluation MUST raise `ExpressionError` identifying the disallowed operator

### Requirement: ExpressionError type hierarchy

The system SHALL define `ExpressionError` as a subclass of `Exception` and SHALL define `ConditionError` and `FormulaError` as subclasses of `ExpressionError`. Callers can catch all three by catching `ExpressionError`.

#### Scenario: Subclass relationship

- **WHEN** `issubclass(ConditionError, ExpressionError)` and `issubclass(FormulaError, ExpressionError)` are evaluated
- **THEN** both expressions MUST return `True`
