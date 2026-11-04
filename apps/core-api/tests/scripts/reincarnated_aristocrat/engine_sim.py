"""Test-only simulation of the turn engine's condition rules.

Mirrors what apps/turn-resolution-service does with conditions (verified by
reading condition_evaluator.py, expression_evaluator.py and state_paths.py):
conditions run in order, each sees the mutations of those before it, mutations
are literal set/increment/decrement, a mutation that leaves a field's range is
rejected and the state is unchanged, and a one-shot is spent unless every one of
its mutations was rejected. It does not model the skip-unless-changed
optimisation, which only avoids work.
"""

import copy
import operator
import uuid
from dataclasses import dataclass, field

from app.models.condition import ConditionCreate
from scripts.reincarnated_aristocrat import builder
from scripts.reincarnated_aristocrat.builder import AppraisalScenario
from scripts.reincarnated_aristocrat.ids import entity_id
from scripts.seeding.fields import FieldDef, flatten_schema

OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}
State = dict[str, object]


def get(state: State, path: str) -> object:
    root, *rest = path.split(".")
    entities: dict[str, object] = state["entities"]  # type: ignore[assignment]
    node: object = entities.get(root, {}) if _is_uuid(root) else state.get(root)
    for key in rest:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _is_uuid(segment: str) -> bool:
    try:
        uuid.UUID(segment)
    except ValueError:
        return False
    return True


def _leaf(expression: dict[str, object], state: State) -> bool:
    actual = get(state, str(expression["field"]))
    if "ref" in expression:
        expected = get(state, str(expression["ref"]))
    else:
        expected = expression.get("value")
    try:
        return bool(OPS[str(expression.get("op", "=="))](actual, expected))
    except TypeError:
        return False


def evaluate(expression: dict[str, object], state: State) -> bool:
    result = _leaf(expression, state) if "field" in expression else None
    for connective in ("AND", "OR", "NOT"):
        if connective not in expression:
            continue
        sub = evaluate(expression[connective], state)  # type: ignore[arg-type]
        if connective == "NOT":
            sub = not sub
        if result is None:
            return sub
        return (result and sub) if connective != "OR" else (result or sub)
    return bool(result)


def _set(state: State, path: str, value: object) -> State:
    root, *rest = path.split(".")
    new = copy.deepcopy(state)
    node = new["entities"].setdefault(root, {}) if _is_uuid(root) else new  # type: ignore[index, union-attr]
    keys = rest if _is_uuid(root) else [root, *rest]
    for key in keys[:-1]:
        node = node.setdefault(key, {})  # type: ignore[union-attr]
    node[keys[-1]] = value  # type: ignore[index]
    return new


def apply(state: State, path: str, op: str, value: object) -> State:
    if op == "set":
        return _set(state, path, value)
    current = get(state, path) or 0
    delta = value if op == "increment" else -value  # type: ignore[operator]
    return _set(state, path, current + delta)  # type: ignore[operator]


@dataclass
class Engine:
    conditions: list[ConditionCreate]
    fields: dict[str, FieldDef]
    state: State
    fired: set[str] = field(default_factory=set)
    rejected: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)

    def _is_in_range(self, path: str, value: object) -> bool:
        definition = self.fields.get(path)
        if definition is None or definition.get("type") != "number":
            return True
        low, high = definition.get("min"), definition.get("max")
        too_low = low is not None and value < low  # type: ignore[operator]
        too_high = high is not None and value > high  # type: ignore[operator]
        return not (too_low or too_high)

    def _mutate(self, condition: ConditionCreate) -> int:
        applied = 0
        for mutation in condition.state_mutations:
            candidate = apply(self.state, mutation.path, mutation.op, mutation.value)
            if self._is_in_range(mutation.path, get(candidate, mutation.path)):
                self.state = candidate
                applied += 1
            else:
                self.rejected.append(f"{condition.label}: {mutation.path}")
        return applied

    def turn(self) -> list[str]:
        self.instructions = []
        for condition in self.conditions:
            if condition.is_one_shot and condition.label in self.fired:
                continue
            if not evaluate(condition.condition_expression, self.state):
                continue
            if condition.narrator_instruction:
                self.instructions.append(condition.narrator_instruction)
            applied = self._mutate(condition)
            if condition.is_one_shot and (applied or not condition.state_mutations):
                self.fired.add(condition.label)
        return self.instructions

    def run(self, turns: int) -> None:
        for _ in range(turns):
            self.turn()


def initial_state(built: AppraisalScenario) -> State:
    schema = built.scenario["state_schema"]
    state: State = {"entities": {}}
    for path, definition in flatten_schema(schema).items():  # type: ignore[arg-type]
        _put(state, path, definition.get("initial"))
    for seed in built.entities:
        state["entities"][str(entity_id(seed.slug))] = {  # type: ignore[index]
            name: attribute.initial
            for name, attribute in seed.payload.attributes_schema.items()
        }
    return state


def _put(state: State, path: str, value: object) -> None:
    keys = path.split(".")
    node = state
    for key in keys[:-1]:
        node = node.setdefault(key, {})  # type: ignore[assignment]
    node[keys[-1]] = value


def field_index(built: AppraisalScenario) -> dict[str, FieldDef]:
    fields = dict(flatten_schema(built.scenario["state_schema"]))  # type: ignore[arg-type]
    for seed in built.entities:
        for name, attribute in seed.payload.attributes_schema.items():
            fields[f"{entity_id(seed.slug)}.{name}"] = attribute.model_dump()
    return fields


def new_engine(built: AppraisalScenario | None = None) -> Engine:
    scenario = built or builder.build()
    return Engine(
        list(scenario.conditions), field_index(scenario), initial_state(scenario)
    )
