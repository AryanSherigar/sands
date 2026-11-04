"""Builders for the condition-expression grammar and the condition payloads.

Grammar (apps/turn-resolution-service/app/turn/expression_evaluator.py): a node
is one leaf {field, op, value} that may carry at most ONE connective (AND, OR,
NOT) whose value is another node. Longer expressions are therefore right-nested
chains: `a AND b AND c` is {a, AND: {b, AND: c}}.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.models.condition import ConditionCreate, StateMutation

Expression = dict[str, object]

FACTS_PLACEMENT = "facts"
AND = "AND"
OR = "OR"

SET = "set"
INCREMENT = "increment"
DECREMENT = "decrement"


def leaf(field: str, op: str, value: object) -> Expression:
    return {"field": field, "op": op, "value": value}


def eq(field: str, value: object) -> Expression:
    return leaf(field, "==", value)


def ne(field: str, value: object) -> Expression:
    return leaf(field, "!=", value)


def gte(field: str, value: int) -> Expression:
    return leaf(field, ">=", value)


def lt(field: str, value: int) -> Expression:
    return leaf(field, "<", value)


def gt(field: str, value: int) -> Expression:
    return leaf(field, ">", value)


def lte(field: str, value: int) -> Expression:
    return leaf(field, "<=", value)


def ref_gte(field: str, other_field: str) -> Expression:
    """`field >= other_field`, comparing two state paths."""
    return {"field": field, "op": ">=", "ref": other_field}


def is_in(field: str, values: Sequence[str]) -> Expression:
    return leaf(field, "in", list(values))


def window(field: str, low: int, high: int) -> tuple[Expression, Expression]:
    """`low <= field < high` as two leaves for all_of to chain."""
    return gte(field, low), lt(field, high)


def either(first: Expression, second: Expression) -> Expression:
    """`first OR second` as a single node, usable as the tail of an AND chain."""
    return {**first, OR: second}


def all_of(*parts: Expression | tuple[Expression, ...]) -> Expression:
    """Chain every part with AND. Tuples (e.g. windows) are flattened."""
    nodes: list[Expression] = []
    for part in parts:
        nodes.extend(part if isinstance(part, tuple) else (part,))
    chain = nodes[-1]
    for node in reversed(nodes[:-1]):
        chain = {**node, AND: chain}
    return chain


@dataclass(frozen=True)
class Mut:
    path: str
    op: str
    value: object


@dataclass(frozen=True)
class Cue:
    name: str
    cut_ambient: bool = False
    silence_ms: int = 0


@dataclass(frozen=True)
class Cond:
    """One authored condition. `mutations` apply in order against running state,
    so a later mutation may rely on an earlier one."""

    label: str
    when: Expression
    mutations: tuple[Mut, ...] = ()
    instruction: str = ""
    cue: Cue | None = None
    is_one_shot: bool = False
    is_fact: bool = False
    effect: dict[str, object] | None = None
    image_url: str | None = None


def to_state_mutations(mutations: Sequence[Mut]) -> list[StateMutation]:
    return [StateMutation(path=m.path, op=m.op, value=m.value) for m in mutations]


def _metadata(cond: Cond) -> dict[str, object]:
    metadata: dict[str, object] = {"placement": FACTS_PLACEMENT} if cond.is_fact else {}
    if cond.effect is not None:
        metadata["client_effect"] = cond.effect
    if cond.image_url is not None:
        metadata["authored_image_url"] = cond.image_url
    return metadata


def to_condition(cond: Cond) -> ConditionCreate:
    fields: dict[str, object] = {}
    if cond.cue is not None:
        fields = {
            "sensory_cue": cond.cue.name,
            "cut_ambient": cond.cue.cut_ambient,
            "silence_duration_ms": cond.cue.silence_ms,
        }
    return ConditionCreate(
        label=cond.label,
        condition_expression=cond.when,
        narrator_instruction=cond.instruction,
        state_mutations=to_state_mutations(cond.mutations),
        is_one_shot=cond.is_one_shot,
        metadata=_metadata(cond),
        **fields,
    )
