from __future__ import annotations

import ast

from talking_parrot.expression.base import SafeExpressionEvaluator


class FormulaEvaluator(SafeExpressionEvaluator):
    """Evaluates numeric formulas from YAML config (e.g., vad.formula).

    Allows arithmetic operators and numeric literals.
    Concrete stage integration is handled in downstream changes.
    """

    @property
    def allowed_operators(self) -> set[type]:
        return {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd, ast.Mod}

    @property
    def allowed_literal_types(self) -> set[type]:
        return {int, float}
