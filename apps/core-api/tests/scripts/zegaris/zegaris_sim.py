"""Test-only mini engine for the Zegaris conditions.

Mirrors the turn engine's rules for the operators this scenario uses: conditions
run in order, each sees the mutations of those before it, and mutations are
literal sets. Not the production evaluator.
"""

import copy
import operator

from app.models.condition import ConditionCreate
from scripts.zegaris.builder import build
from scripts.zegaris.ids import entity_ref

OPS = {"==": operator.eq, "!=": operator.ne}
State = dict[str, object]


def initial_state(location_slug: str = "owls_respite") -> State:
    return {
        "current_location_id": entity_ref(location_slug),
        "world": {"tithe": "offered", "access": "none"},
        "intent": {"tithe_step": "", "access_step": ""},
        "quests": {"retrieval": {"stage": "offered"}},
    }


def get(state: State, path: str) -> object:
    node: object = state
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node


def evaluate(expression: dict[str, object], state: State) -> bool:
    result = bool(
        OPS[str(expression.get("op", "=="))](
            get(state, str(expression["field"])), expression.get("value")
        )
    )
    if "AND" in expression:
        return result and evaluate(expression["AND"], state)  # type: ignore[arg-type]
    return result


def put(state: State, path: str, value: object) -> State:
    new = copy.deepcopy(state)
    *parents, leaf = path.split(".")
    node = new
    for key in parents:
        node = node[key]  # type: ignore[assignment, index]
    node[leaf] = value  # type: ignore[index]
    return new


def run_turn(state: State) -> tuple[State, list[ConditionCreate]]:
    fired: list[ConditionCreate] = []
    for condition in build().conditions:
        if not evaluate(condition.condition_expression, state):
            continue
        fired.append(condition)
        for mutation in condition.state_mutations:
            state = put(state, mutation.path, mutation.value)
    return state, fired
