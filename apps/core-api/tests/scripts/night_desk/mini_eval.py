"""Minimal evaluator for the expression subset the Night Desk endings and tiers use.

Test-only. The production evaluator lives in the Turn Resolution Service and is
exercised there; this exists so the Core API tests can check the generated
expressions against concrete states without importing another service.
"""

import operator

OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def get(state: dict[str, object], path: str) -> object:
    node: object = state
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _compare(expression: dict[str, object], state: dict[str, object]) -> bool:
    """A missing field makes a comparison false, as in the production evaluator."""
    actual = get(state, str(expression["field"]))
    try:
        return OPS[str(expression["op"])](actual, expression["value"])
    except TypeError:
        return False


def evaluate(expression: dict[str, object], state: dict[str, object]) -> bool:
    result = None
    if "field" in expression:
        result = _compare(expression, state)
    for connective in ("AND", "OR"):
        if connective in expression:
            sub = evaluate(expression[connective], state)  # type: ignore[arg-type]
            if result is None:
                return sub
            return (result and sub) if connective == "AND" else (result or sub)
    return bool(result)
