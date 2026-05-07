from __future__ import annotations

import abc
import ast
from typing import Any


class ExpressionError(Exception):
    pass


class ConditionError(ExpressionError):
    pass


class FormulaError(ExpressionError):
    pass


class SafeExpressionEvaluator(abc.ABC):
    """AST-whitelist evaluator — default-deny, no eval/exec."""

    @property
    @abc.abstractmethod
    def allowed_operators(self) -> set[type]:
        """Set of ast operator node types the subclass permits."""

    @property
    @abc.abstractmethod
    def allowed_literal_types(self) -> set[type]:
        """Set of Python literal types (int, float, …) the subclass permits."""

    def evaluate(self, expression: str, variables: dict[str, Any]) -> Any:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ExpressionError(f"Syntax error in expression: {exc}") from exc
        return self._visit(tree.body, variables)

    def _visit(self, node: ast.AST, variables: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, tuple(self.allowed_literal_types)):
                raise ExpressionError(
                    f"Literal type {type(node.value).__name__!r} is not allowed"
                )
            return node.value

        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ExpressionError(f"Undefined identifier: '{node.id}'")
            return variables[node.id]

        if isinstance(node, ast.BinOp):
            if type(node.op) not in self.allowed_operators:
                raise ExpressionError(
                    f"Operator {type(node.op).__name__!r} is not allowed"
                )
            left = self._visit(node.left, variables)
            right = self._visit(node.right, variables)
            return self._apply_binop(node.op, left, right)

        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in self.allowed_operators:
                raise ExpressionError(
                    f"Unary operator {type(node.op).__name__!r} is not allowed"
                )
            operand = self._visit(node.operand, variables)
            return self._apply_unaryop(node.op, operand)

        if isinstance(node, ast.BoolOp):
            if type(node.op) not in self.allowed_operators:
                raise ExpressionError(
                    f"Bool operator {type(node.op).__name__!r} is not allowed"
                )
            values = [self._visit(v, variables) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            return any(values)

        if isinstance(node, ast.Compare):
            left = self._visit(node.left, variables)
            for op, comparator in zip(node.ops, node.comparators):
                if type(op) not in self.allowed_operators:
                    raise ExpressionError(
                        f"Compare operator {type(op).__name__!r} is not allowed"
                    )
                right = self._visit(comparator, variables)
                if not self._apply_compare(op, left, right):
                    return False
                left = right
            return True

        raise ExpressionError(f"AST node type {type(node).__name__!r} is not allowed")

    @staticmethod
    def _apply_binop(op: ast.operator, left: Any, right: Any) -> Any:
        ops = {
            ast.Add: lambda a, b: a + b,
            ast.Sub: lambda a, b: a - b,
            ast.Mult: lambda a, b: a * b,
            ast.Div: lambda a, b: a / b,
            ast.Mod: lambda a, b: a % b,
            ast.Pow: lambda a, b: a**b,
            ast.FloorDiv: lambda a, b: a // b,
        }
        fn = ops.get(type(op))
        if fn is None:
            raise ExpressionError(f"Unsupported binary operator: {type(op).__name__!r}")
        return fn(left, right)

    @staticmethod
    def _apply_unaryop(op: ast.unaryop, operand: Any) -> Any:
        if isinstance(op, ast.USub):
            return -operand
        if isinstance(op, ast.UAdd):
            return +operand
        if isinstance(op, ast.Not):
            return not operand
        raise ExpressionError(f"Unsupported unary operator: {type(op).__name__!r}")

    @staticmethod
    def _apply_compare(op: ast.cmpop, left: Any, right: Any) -> bool:
        ops = {
            ast.Eq: lambda a, b: a == b,
            ast.NotEq: lambda a, b: a != b,
            ast.Lt: lambda a, b: a < b,
            ast.LtE: lambda a, b: a <= b,
            ast.Gt: lambda a, b: a > b,
            ast.GtE: lambda a, b: a >= b,
        }
        fn = ops.get(type(op))
        if fn is None:
            raise ExpressionError(
                f"Unsupported compare operator: {type(op).__name__!r}"
            )
        return fn(left, right)
