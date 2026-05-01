"""Tests for SafeExpressionEvaluator — covers spec scenarios and example table."""

import ast
import pytest

from talking_parrot.expression.base import (
    ExpressionError,
    ConditionError,
    FormulaError,
    SafeExpressionEvaluator,
)


# ── Minimal concrete evaluator for testing ───────────────────────────────────


class _NumericEvaluator(SafeExpressionEvaluator):
    """Allows +, -, *, / on floats/ints and Name lookups."""

    @property
    def allowed_operators(self):
        return {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd}

    @property
    def allowed_literal_types(self):
        return {int, float}


class _AddOnlyEvaluator(SafeExpressionEvaluator):
    """Only allows + and - on numbers."""

    @property
    def allowed_operators(self):
        return {ast.Add, ast.Sub}

    @property
    def allowed_literal_types(self):
        return {int, float}


# ── ExpressionError hierarchy ────────────────────────────────────────────────


class TestExpressionErrorHierarchy:
    def test_condition_error_is_expression_error(self):
        assert issubclass(ConditionError, ExpressionError)

    def test_formula_error_is_expression_error(self):
        assert issubclass(FormulaError, ExpressionError)

    def test_catch_all_via_expression_error(self):
        with pytest.raises(ExpressionError):
            raise ConditionError("test")


# ── Disallowed node types (spec example table) ────────────────────────────────


class TestDisallowedNodes:
    @pytest.mark.parametrize(
        "expr,reason",
        [
            ('__import__("os").system("ls")', "Call and Subscript not in whitelist"),
            ("(lambda x: x)(1)", "Lambda and Call not in whitelist"),
            ("prob.upper()", "Attribute and Call not in whitelist"),
            ("[x for x in range(10)]", "ListComp, Call, Name(range) not in whitelist"),
        ],
    )
    def test_rejected_expressions(self, expr, reason):
        evaluator = _NumericEvaluator()
        with pytest.raises(ExpressionError):
            evaluator.evaluate(expr, variables={})

    def test_eval_not_in_source(self):
        import inspect
        import talking_parrot.expression.base as mod

        src = inspect.getsource(mod)
        assert "eval(" not in src
        assert "exec(" not in src
        assert "__import__(" not in src


# ── Whitelist enforcement ─────────────────────────────────────────────────────


class TestWhitelistEnforcement:
    def test_allowed_expression_evaluates(self):
        ev = _NumericEvaluator()
        result = ev.evaluate("a + b", variables={"a": 1.0, "b": 2.0})
        assert result == pytest.approx(3.0)

    def test_disallowed_operator_raises(self):
        ev = _AddOnlyEvaluator()
        with pytest.raises(ExpressionError):
            ev.evaluate("a * b", variables={"a": 2.0, "b": 3.0})

    def test_string_literal_rejected_by_numeric_evaluator(self):
        ev = _NumericEvaluator()
        with pytest.raises(ExpressionError):
            ev.evaluate('"hello"', variables={})


# ── Undefined identifier ──────────────────────────────────────────────────────


class TestUndefinedIdentifier:
    def test_missing_variable_raises_with_name_in_message(self):
        ev = _NumericEvaluator()
        with pytest.raises(ExpressionError, match="b"):
            ev.evaluate("a + b", variables={"a": 1.0})
