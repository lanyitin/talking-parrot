from __future__ import annotations

import ast

from talking_parrot.expression.base import SafeExpressionEvaluator


class ConditionEvaluator(SafeExpressionEvaluator):
    """Evaluates boolean conditions from YAML transcribing[].condition.

    Allows comparison and boolean operators with numeric literals.
    Concrete stage integration is handled in downstream changes.
    """

    @property
    def allowed_operators(self) -> set[type]:
        return {
            ast.And,
            ast.Or,
            ast.Not,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.Add,
            ast.Sub,
        }

    @property
    def allowed_literal_types(self) -> set[type]:
        return {int, float, bool}
