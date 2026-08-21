"""Builtin ``calculator`` tool — safe arithmetic expressions (E7-S07)."""

from __future__ import annotations

import ast
import operator
from typing import Any

from haystack import component
from haystack.tools import ComponentTool

MAX_EXPRESSION_CHARS = 256
_MAX_ABS_POW_EXPONENT = 12
_MAX_ABS_POW_BASE = 1_000_000

_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class CalculatorError(ValueError):
    """Raised when an arithmetic expression cannot be evaluated safely."""


def evaluate_expression(expression: str) -> int | float:
    """Evaluate a numeric expression using a restricted AST (no names or calls)."""
    text = expression.strip()
    if not text:
        raise CalculatorError("calculator requires a non-empty arithmetic expression")
    if len(text) > MAX_EXPRESSION_CHARS:
        raise CalculatorError(
            f"calculator expression exceeds {MAX_EXPRESSION_CHARS} character limit"
        )
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError(f"invalid arithmetic expression: {expression!r}") from exc
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculatorError("calculator supports numeric literals only")
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > _MAX_ABS_POW_EXPONENT or abs(left) > _MAX_ABS_POW_BASE:
                raise CalculatorError("calculator power operand is too large")
        try:
            return _BIN_OPS[type(node.op)](left, right)
        except ZeroDivisionError as exc:
            raise CalculatorError("calculator division by zero") from exc
        except OverflowError as exc:
            raise CalculatorError("calculator result overflow") from exc
    raise CalculatorError(
        "calculator supports arithmetic operators only "
        "(+ - * / // % ** and parentheses)"
    )


def _format_result(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@component
class Calculator:
    """Haystack component that evaluates a safe arithmetic expression."""

    @component.output_types(result=str)
    def run(self, expression: str) -> dict[str, str]:
        return {"result": _format_result(evaluate_expression(expression))}


def calculator_tool() -> ComponentTool:
    """Return a Haystack ``ComponentTool`` for the builtin ``calculator`` id."""
    return ComponentTool(
        component=Calculator(),
        name="calculator",
        description=(
            "Evaluate a numeric arithmetic expression and return the result. "
            "Supports + - * / // % ** and parentheses. No variables or function calls."
        ),
    )


def build_calculator_tool(**kwargs: Any) -> ComponentTool:
    """Catalog factory entry for ``calculator``."""
    del kwargs
    return calculator_tool()
