"""Evaluates master-mode active conditions before context retrieval/AI orchestration.

Runs after state_loader, before context_retrieval (master mode only) — the
only place besides state_writer that mutates state (Effect C), and it does
so strictly before any Gemini call so the AI narrates against the
post-mutation state (see "The Cairn Presses In" in
docs/specs/master-mode-demo-scenario.md §8).

Every condition whose expression is true this turn contributes its
narrator_instruction (that is what narrator_instruction is for, per the
ScenarioCondition design — always passed to the orchestrator while active);
conditions that also carry a state_mutation (Effect C) additionally apply
and validate it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog
from app.config import settings
from app.models.client_effect import FiredEffect
from app.models.sensory_cue import DEFAULT_SILENCE_DURATION_MS, FiredCue
from app.models.turn import LoadedState
from app.turn import state_paths
from app.turn.expression_evaluator import evaluate, extract_field_paths
from app.turn.facts_block import is_fact_condition
from app.turn.mutation_lists import mutations_from
from app.turn.state_visibility import is_hidden_path
from app.turn.steps import state_validator
from app.turn.tools import is_enabled

logger = structlog.get_logger()

EVENT_TURN_STEP_COMPLETED = "turn_step_completed"
EVENT_EFFECT_C_INVARIANT_VIOLATION = "effect_c_invariant_violation"
EVENT_SENSORY_CUE_DROPPED = "sensory_cue_dropped"
ATMOSPHERE_TOOL_KEY = "atmosphere"
STEP_NAME = "condition_evaluator"
FIRED_CONDITIONS_KEY = "_fired_conditions"
METADATA_CLIENT_EFFECT = "client_effect"
METADATA_AUTHORED_IMAGE_URL = "authored_image_url"


class ConditionEvaluationResult:
    """Updated state, narrator instructions to inject, and which field paths
    changed (feeds next turn's field-relevance scoping, via state_writer)."""

    def __init__(
        self,
        state: dict[str, object],
        active_instructions: list[str],
        mutated_paths: set[str],
        fired_cues: list[FiredCue] | None = None,
        fired_condition_ids: list[str] | None = None,
        duration_ms: float = 0.0,
        fired_effects: list[FiredEffect] | None = None,
        authored_image_url: str | None = None,
    ) -> None:
        self.state = state
        self.active_instructions = active_instructions
        self.mutated_paths = mutated_paths
        self.fired_cues = fired_cues or []
        self.fired_condition_ids = fired_condition_ids or []
        self.duration_ms = duration_ms
        self.fired_effects = fired_effects or []
        self.authored_image_url = authored_image_url


def evaluate_conditions(loaded_state: LoadedState) -> ConditionEvaluationResult:
    """Evaluate this scenario's active conditions against the loaded state."""
    conditions = loaded_state.scenario_snapshot.get("scenario_conditions", []) or []
    last_changed = set(loaded_state.state.get("_last_changed_fields", []) or [])
    prev_active = set(loaded_state.state.get("_active_conditions", []) or [])
    fired_ids = _fired_condition_ids(loaded_state.state)
    evaluate_all = _narrative_turn_count(loaded_state) == 0 or not last_changed

    start = time.monotonic()
    state = dict(loaded_state.state)
    instructions: list[str] = []
    mutated_paths: set[str] = set()
    currently_active: list[str] = []
    firings = _RisingEdgeFirings()
    has_atmosphere = is_enabled(loaded_state.scenario_snapshot, ATMOSPHERE_TOOL_KEY)

    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        cond_id = _condition_id(condition)
        if condition.get("is_one_shot") and cond_id in fired_ids:
            continue
        if _should_skip(
            condition,
            last_changed | mutated_paths,
            evaluate_all,
            cond_id in prev_active,
        ):
            continue
        if not evaluate(condition.get("condition_expression"), state):
            continue

        _record_active(condition, cond_id, currently_active, instructions)
        if cond_id not in prev_active:
            _collect_rising_edge(condition, has_atmosphere, firings)
        state, mutated_paths, applied_count = _apply_condition_mutations(
            state, condition, loaded_state, mutated_paths
        )
        if condition.get("is_one_shot") and _has_taken_effect(condition, applied_count):
            state, mutated_paths = _mark_fired(state, cond_id, mutated_paths)

    state["_active_conditions"] = currently_active
    duration_ms = _log_step_completed(start, evaluate_all, len(instructions))
    return ConditionEvaluationResult(
        state,
        instructions,
        mutated_paths,
        firings.cues,
        fired_condition_ids=currently_active,
        duration_ms=duration_ms,
        fired_effects=firings.effects,
        authored_image_url=firings.images[-1] if firings.images else None,
    )


@dataclass
class _RisingEdgeFirings:
    cues: list[FiredCue] = field(default_factory=list)
    effects: list[FiredEffect] = field(default_factory=list)
    images: list[str] = field(default_factory=list)


def _narrative_turn_count(loaded_state: LoadedState) -> int:
    if loaded_state.narrative_turn_count is None:
        return loaded_state.turn_count
    return loaded_state.narrative_turn_count


def _collect_rising_edge(
    condition: dict[str, object], has_atmosphere: bool, firings: _RisingEdgeFirings
) -> None:
    if has_atmosphere:
        _collect_cue(condition, firings.cues)
    metadata = condition.get("metadata")
    if not isinstance(metadata, dict):
        return
    effect = metadata.get(METADATA_CLIENT_EFFECT)
    if isinstance(effect, dict) and isinstance(effect.get("params"), dict):
        firings.effects.append(
            FiredEffect(kind=str(effect.get("kind")), params=effect["params"])
        )
    image_url = metadata.get(METADATA_AUTHORED_IMAGE_URL)
    if isinstance(image_url, str) and image_url:
        firings.images.append(image_url)


def _collect_cue(condition: dict[str, object], fired_cues: list[FiredCue]) -> None:
    cue = condition.get("sensory_cue")
    if not isinstance(cue, str) or not cue:
        return
    if len(fired_cues) >= settings.sensory_cue_max_per_turn:
        logger.warning(EVENT_SENSORY_CUE_DROPPED, cue=cue)
        return
    silence_ms = condition.get("silence_duration_ms")
    fired_cues.append(
        FiredCue(
            cue=cue,
            cut_ambient=condition.get("cut_ambient") is not False,
            silence_duration_ms=silence_ms
            if isinstance(silence_ms, int)
            else DEFAULT_SILENCE_DURATION_MS,
        )
    )


def _condition_id(condition: dict[str, object]) -> str:
    return str(condition.get("condition_id") or condition.get("label") or "")


def _record_active(
    condition: dict[str, object],
    cond_id: str,
    active_ids: list[str],
    instructions: list[str],
) -> None:
    if cond_id:
        active_ids.append(cond_id)
    instruction = condition.get("narrator_instruction")
    if instruction and not is_fact_condition(condition):
        instructions.append(str(instruction))


def effective_mutations(condition: dict[str, object]) -> list[dict[str, object]]:
    return mutations_from(
        condition.get("state_mutations"), condition.get("state_mutation")
    )


def _fired_condition_ids(state: dict[str, object]) -> set[str]:
    fired = state.get(FIRED_CONDITIONS_KEY)
    return {str(item) for item in fired} if isinstance(fired, list) else set()


def _mark_fired(
    state: dict[str, object], cond_id: str, mutated_paths: set[str]
) -> tuple[dict[str, object], set[str]]:
    fired = [*(state.get(FIRED_CONDITIONS_KEY) or []), cond_id]  # type: ignore[union-attr]
    return {**state, FIRED_CONDITIONS_KEY: fired}, mutated_paths | {
        FIRED_CONDITIONS_KEY
    }


def _apply_condition_mutations(
    state: dict[str, object],
    condition: dict[str, object],
    loaded_state: LoadedState,
    mutated_paths: set[str],
) -> tuple[dict[str, object], set[str], int]:
    applied_count = 0
    for mutation in effective_mutations(condition):
        state, path = _apply_and_validate_effect_c(
            state, mutation, loaded_state, condition
        )
        if path:
            mutated_paths = mutated_paths | {path}
            applied_count += 1
    return state, mutated_paths, applied_count


def _has_taken_effect(condition: dict[str, object], applied_count: int) -> bool:
    """A one-shot is spent unless it had mutations and every one was rejected
    (by the schema or an invariant), so it can fire again once they would apply."""
    return applied_count > 0 or not effective_mutations(condition)


def _log_step_completed(start: float, evaluate_all: bool, count: int) -> float:
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        EVENT_TURN_STEP_COMPLETED,
        step_name=STEP_NAME,
        duration_ms=duration_ms,
        evaluated_all=evaluate_all,
        active_instruction_count=count,
    )
    return duration_ms


def list_active_condition_labels(
    scenario_conditions: list[object],
    state: dict[str, object],
    state_schema: dict[str, object] | None = None,
) -> list[str]:
    """Every scenario_condition currently true, for the play screen's status-
    badge row. Unlike evaluate_conditions, this checks ALL conditions (not
    just ones whose fields changed this turn) against final post-write state,
    and never applies a state_mutation — read-only. With a schema, a condition
    that reads a hidden field is left out: its label would tell the player what
    the hidden field holds."""
    labels: list[str] = []
    fired_ids = _fired_condition_ids(state)
    for condition in scenario_conditions:
        if not isinstance(condition, dict):
            continue
        if condition.get("is_one_shot") and _condition_id(condition) in fired_ids:
            continue
        if not evaluate(condition.get("condition_expression"), state):
            continue
        if _reads_hidden_field(condition, state_schema):
            continue
        label = condition.get("label")
        if label:
            labels.append(str(label))
    return labels


def _reads_hidden_field(
    condition: dict[str, object], state_schema: dict[str, object] | None
) -> bool:
    if not state_schema:
        return False
    expression = condition.get("condition_expression")
    paths = extract_field_paths(expression if isinstance(expression, dict) else None)
    return any(is_hidden_path(state_schema, path) for path in paths)


def _should_skip(
    condition: dict[str, object],
    last_changed: set[str],
    evaluate_all: bool,
    was_active: bool,
) -> bool:
    if evaluate_all or was_active:
        return False
    referenced = extract_field_paths(condition.get("condition_expression"))
    return not (referenced & last_changed)


def _apply_and_validate_effect_c(
    state: dict[str, object],
    mutation: dict[str, object],
    loaded_state: LoadedState,
    condition: dict[str, object],
) -> tuple[dict[str, object], str | None]:
    path = str(mutation.get("path") or "")
    if not path:
        return state, None

    candidate_state = state_paths.apply_mutation(
        state, path, str(mutation.get("op", "set")), mutation.get("value")
    )
    result = state_validator.validate_applied_change(
        path, candidate_state, loaded_state.scenario_snapshot, original_state=state
    )
    if not result.is_valid:
        logger.warning(
            EVENT_EFFECT_C_INVARIANT_VIOLATION,
            condition_label=condition.get("label"),
            error=result.error_message,
        )
        return state, None
    return result.updated_state or state, path
