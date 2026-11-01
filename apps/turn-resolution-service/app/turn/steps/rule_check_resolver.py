"""Judges and resolves a player's rule-check report.

Two pieces, mirroring check_result_resolver.py:

- ensure_report_persisted runs BEFORE ai_orchestrator and commits directly, so a
  dropped connection cannot change the answer on retry. The server alone judges
  lateness; the client only says which option it chose or that its timer ran out.
  The stored judgment carries the chosen option id, never the result string
  (the result may belong to a hidden state field and `_pending_check` reaches
  the client).
- resolve_report is pure: it turns the stored judgment into the result write,
  the option's mutations and the narrator instruction.
"""

import re
import uuid
from dataclasses import dataclass, field

import structlog
from app.exceptions.turn_exceptions import (
    CheckNotArmedError,
    CheckReportInvalidError,
    CheckResolutionMismatchError,
)
from app.models.check_event import CheckReportInput
from app.models.turn_metrics import (
    CHECK_RESULT_FAILED,
    CHECK_RESULT_HIDDEN,
    CHECK_RESULT_PASSED,
    CHECK_RESULT_TIMEOUT,
    CheckOutcome,
)
from app.repositories.playthrough_repo import PlaythroughRepo
from app.turn import rule_check_payload, state_paths, time_entry
from app.turn.rule_check_report import choice_labels, is_armed, is_late
from app.turn.steps import state_validator

logger = structlog.get_logger()

EVENT_RULE_CHECK_REPORT_PERSISTED = "rule_check_report_persisted"
EVENT_RULE_CHECK_MUTATION_INVALID = "rule_check_mutation_invalid"
EVENT_RULE_CHECK_DEFINITION_MISSING = "rule_check_definition_missing"
STATE_KEY_PENDING_CHECK = "_pending_check"
STATE_KEY_CHECK_QUEUE = "_check_queue"
STATE_KEY_CHECK_REOPENS = "_check_reopens"
KIND_TIMED_CHOICE = "timed_choice"
DEFAULT_MAX_REOPENS = 3
DEFAULT_INSTRUCTION = (
    "The clerk's response to '{label}' was '{result}'; narrate what follows, "
    "without commenting on whether it was right."
)


_STATE_TOKEN = re.compile(r"\{state:([a-zA-Z0-9_.]+)\}")


@dataclass(frozen=True)
class RuleCheckJudgment:
    option_id: str | None
    is_timeout: bool
    is_hidden: bool = False
    entry_text: str | None = None


@dataclass
class RuleCheckResolution:
    state: dict[str, object]
    instruction: str
    mutated_paths: set[str] = field(default_factory=set)


def judge_report(
    pending: dict[str, object], report: CheckReportInput, *, now_ms: int
) -> RuleCheckJudgment:
    if is_late(pending, report, now_ms):
        return RuleCheckJudgment(option_id=None, is_timeout=True)
    is_hidden = _is_hidden_report(pending, report)
    if report.timed_out:
        return RuleCheckJudgment(option_id=None, is_timeout=True, is_hidden=is_hidden)
    if report.choice_id is None or report.choice_id not in choice_labels(pending):
        raise CheckReportInvalidError()
    entry_text = _entry_text_of(pending, report)
    return RuleCheckJudgment(
        option_id=report.choice_id,
        is_timeout=False,
        is_hidden=is_hidden,
        entry_text=entry_text,
    )


def _entry_text_of(pending: dict[str, object], report: CheckReportInput) -> str | None:
    is_time_entry = pending.get("kind") == rule_check_payload.KIND_TIME_ENTRY
    if not is_time_entry or report.choice_id != rule_check_payload.ENTRY_OPTION_ID:
        return None
    entry_text = (report.entry_text or "").strip()
    if not entry_text:
        raise CheckReportInvalidError()
    return entry_text


def _is_hidden_report(pending: dict[str, object], report: CheckReportInput) -> bool:
    return (
        pending.get("kind") == KIND_TIMED_CHOICE
        and report.was_hidden
        and not report.is_untimed
    )


async def ensure_report_persisted(
    playthrough_id: uuid.UUID,
    state: dict[str, object],
    report: CheckReportInput,
    *,
    now_ms: int,
    playthrough_repo: PlaythroughRepo,
    expected_turn_count: int,
) -> dict[str, object]:
    """Judge and durably stamp the answer into `_pending_check.resolved`;
    idempotent. Never advances turn_count (only the turn commit does).

    Runs under a row lock on the playthrough, so two concurrent reports
    serialise: the loser re-reads the winner's stamp and replays it."""
    state = await _locked_state(playthrough_repo, playthrough_id, state)
    pending = state.get(STATE_KEY_PENDING_CHECK)
    if not isinstance(pending, dict) or pending.get("check_id") != report.check_id:
        raise CheckResolutionMismatchError()
    if pending.get("resolved") is not None:
        return state
    if not is_armed(pending):
        raise CheckNotArmedError()
    judgment = judge_report(pending, report, now_ms=now_ms)
    stamped = {
        **state,
        STATE_KEY_PENDING_CHECK: {**pending, "resolved": _stored_form(judgment)},
    }
    await playthrough_repo.update_state(
        playthrough_id,
        stamped,
        new_turn_count=expected_turn_count,
        expected_turn_count=expected_turn_count,
    )
    await playthrough_repo.session.commit()
    logger.info(
        EVENT_RULE_CHECK_REPORT_PERSISTED,
        check_id=pending.get("check_id"),
        is_timeout=judgment.is_timeout,
        is_hidden=judgment.is_hidden,
    )
    return stamped


async def _locked_state(
    playthrough_repo: PlaythroughRepo,
    playthrough_id: uuid.UUID,
    fallback: dict[str, object],
) -> dict[str, object]:
    locked = await playthrough_repo.get_by_id_for_update(playthrough_id)
    locked_state = getattr(locked, "state", None)
    return locked_state if isinstance(locked_state, dict) else fallback


def _stored_form(judgment: RuleCheckJudgment) -> dict[str, object]:
    stored: dict[str, object] = {
        "option_id": judgment.option_id,
        "is_timeout": judgment.is_timeout,
        "is_hidden": judgment.is_hidden,
    }
    if judgment.entry_text is not None:
        stored["entry_text"] = judgment.entry_text
    return stored


def resolve_report(
    state: dict[str, object], scenario_snapshot: dict[str, object]
) -> RuleCheckResolution:
    pending = state.get(STATE_KEY_PENDING_CHECK)
    pending = pending if isinstance(pending, dict) else {}
    resolved_state = {k: v for k, v in state.items() if k != STATE_KEY_PENDING_CHECK}
    definition = _find_definition(scenario_snapshot, pending.get("check_def_id"))
    if definition is None:
        logger.warning(
            EVENT_RULE_CHECK_DEFINITION_MISSING,
            check_def_id=pending.get("check_def_id"),
        )
        return RuleCheckResolution(
            resolved_state, "A prompt concluded.", {STATE_KEY_PENDING_CHECK}
        )
    judgment = _stored_judgment(pending)
    outcome = _outcome_of(definition, judgment, pending)
    result, mutations = outcome.result, outcome.mutations
    paths = {STATE_KEY_PENDING_CHECK}
    result_path = str(definition.get("result_path"))
    writes = [{"path": result_path, "op": "set", "value": result}, *mutations]
    for write in writes:
        resolved_state, applied_path = _apply_write(
            resolved_state, write, scenario_snapshot
        )
        if applied_path:
            paths.add(applied_path)
    if _should_reopen(outcome, pending, definition):
        resolved_state = _queue_reopen(resolved_state, definition, pending)
        paths |= {STATE_KEY_CHECK_QUEUE, STATE_KEY_CHECK_REOPENS}
    instruction = _instruction_for(definition, result, resolved_state)
    return RuleCheckResolution(resolved_state, instruction, paths)


def summarize_outcome(
    pending: dict[str, object], scenario_snapshot: dict[str, object], *, now_ms: int
) -> CheckOutcome:
    """The stamped judgment as a metrics row. Only recall checks have a right
    answer; for the other kinds "passed" means the player answered in time."""
    judgment = _stored_judgment(pending)
    definition = _find_definition(scenario_snapshot, pending.get("check_def_id"))
    return CheckOutcome(
        check_id=str(pending.get("check_id", "")),
        kind=str(pending.get("kind", "")),
        result=_metrics_result(definition, judgment),
        answer_ms=_answer_ms(pending, now_ms),
    )


def _metrics_result(
    definition: dict[str, object] | None, judgment: RuleCheckJudgment
) -> str:
    if judgment.is_hidden:
        return CHECK_RESULT_HIDDEN
    if judgment.is_timeout:
        return CHECK_RESULT_TIMEOUT
    params = definition.get("params") if definition else None
    is_recall = definition is not None and (
        definition.get("kind") == rule_check_payload.KIND_RECALL
    )
    if is_recall and isinstance(params, dict):
        is_correct = _is_recall_correct(params, judgment)
        return CHECK_RESULT_PASSED if is_correct else CHECK_RESULT_FAILED
    return CHECK_RESULT_PASSED


def _answer_ms(pending: dict[str, object], now_ms: int) -> int | None:
    issued_at = pending.get("issued_at")
    return max(0, now_ms - issued_at) if isinstance(issued_at, int) else None


def _find_definition(
    scenario_snapshot: dict[str, object], check_def_id: object
) -> dict[str, object] | None:
    listed = scenario_snapshot.get("rule_checks")
    for definition in listed if isinstance(listed, list) else []:
        if isinstance(definition, dict) and str(definition.get("check_id")) == str(
            check_def_id
        ):
            return definition
    return None


def _stored_judgment(pending: dict[str, object]) -> RuleCheckJudgment:
    resolved = pending.get("resolved")
    if not isinstance(resolved, dict):
        return RuleCheckJudgment(option_id=None, is_timeout=True)
    option_id = resolved.get("option_id")
    entry_text = resolved.get("entry_text")
    return RuleCheckJudgment(
        option_id=str(option_id) if option_id is not None else None,
        is_timeout=bool(resolved.get("is_timeout")),
        is_hidden=bool(resolved.get("is_hidden")),
        entry_text=entry_text if isinstance(entry_text, str) else None,
    )


@dataclass(frozen=True)
class _Outcome:
    result: str
    mutations: list[dict[str, object]] = field(default_factory=list)
    reopens: bool = False


def _outcome_of(
    definition: dict[str, object],
    judgment: RuleCheckJudgment,
    pending: dict[str, object],
) -> _Outcome:
    params = definition.get("params")
    params = params if isinstance(params, dict) else {}
    if definition.get("kind") == rule_check_payload.KIND_RECALL:
        return _recall_outcome(params, judgment)
    if definition.get("kind") == rule_check_payload.KIND_TIME_ENTRY:
        return _time_entry_outcome(params, judgment, pending)
    if judgment.is_hidden and params.get("hidden_result"):
        return _Outcome(str(params["hidden_result"]))
    if not judgment.is_timeout:
        option = _chosen_option(params, judgment.option_id)
        if option is not None:
            return _outcome_for_option(option)
    return _Outcome(str(params.get("timeout_result")))


def _chosen_option(
    params: dict[str, object], option_id: str | None
) -> dict[str, object] | None:
    for option in params.get("options") or []:  # type: ignore[union-attr]
        if isinstance(option, dict) and option.get("id") == option_id:
            return option
    return None


def _outcome_for_option(option: dict[str, object]) -> _Outcome:
    mutations = option.get("mutations")
    listed = mutations if isinstance(mutations, list) else []
    return _Outcome(
        str(option.get("result")),
        [m for m in listed if isinstance(m, dict)],
        reopens=option.get("reopens") is True,
    )


def _time_entry_outcome(
    params: dict[str, object], judgment: RuleCheckJudgment, pending: dict[str, object]
) -> _Outcome:
    if judgment.is_timeout or judgment.option_id is None:
        return _Outcome(str(params.get("timeout_result")))
    if judgment.option_id == rule_check_payload.REJECT_OPTION_ID:
        return _outcome_block(params, "reject")
    wall_minute = pending.get("wall_minute_of_day")
    told_minute = params.get("told_minute_of_day")
    key = time_entry.classify_entry(
        judgment.entry_text or "",
        told_minute if isinstance(told_minute, int) else -1,
        wall_minute if isinstance(wall_minute, int) else None,
    )
    return _outcome_block(params, key)


def _outcome_block(params: dict[str, object], key: str) -> _Outcome:
    block = params.get(key)
    block = block if isinstance(block, dict) else {}
    mutations = block.get("mutations")
    listed = mutations if isinstance(mutations, list) else []
    return _Outcome(
        str(block.get("result")), [m for m in listed if isinstance(m, dict)]
    )


def _recall_outcome(params: dict[str, object], judgment: RuleCheckJudgment) -> _Outcome:
    if judgment.is_timeout or judgment.option_id is None:
        return _Outcome(str(params.get("result_timeout")))
    if _is_recall_correct(params, judgment):
        return _Outcome(str(params.get("result_correct")))
    return _Outcome(str(params.get("result_wrong")))


def _is_recall_correct(params: dict[str, object], judgment: RuleCheckJudgment) -> bool:
    if judgment.option_id is None:
        return False
    chosen = rule_check_payload.parse_variant_index(judgment.option_id)
    return chosen is not None and chosen == params.get("correct_index")


def _should_reopen(
    outcome: _Outcome, pending: dict[str, object], definition: dict[str, object]
) -> bool:
    if not outcome.reopens:
        return False
    params = definition.get("params")
    max_reopens = params.get("max_reopens") if isinstance(params, dict) else None
    limit = max_reopens if isinstance(max_reopens, int) else DEFAULT_MAX_REOPENS
    return _reopen_count_of(pending) < limit


def _reopen_count_of(pending: dict[str, object]) -> int:
    count = pending.get("reopen_count")
    return count if isinstance(count, int) else 0


def _queue_reopen(
    state: dict[str, object],
    definition: dict[str, object],
    pending: dict[str, object],
) -> dict[str, object]:
    definition_id = str(definition.get("check_id"))
    queue = state.get(STATE_KEY_CHECK_QUEUE)
    waiting = [str(item) for item in queue] if isinstance(queue, list) else []
    reopens = state.get(STATE_KEY_CHECK_REOPENS)
    counts = dict(reopens) if isinstance(reopens, dict) else {}
    counts[definition_id] = _reopen_count_of(pending) + 1
    return {
        **state,
        STATE_KEY_CHECK_QUEUE: [definition_id, *waiting],
        STATE_KEY_CHECK_REOPENS: counts,
    }


def _apply_write(
    state: dict[str, object],
    write: dict[str, object],
    scenario_snapshot: dict[str, object],
) -> tuple[dict[str, object], str | None]:
    path = str(write.get("path") or "")
    if not path:
        return state, None
    candidate = state_paths.apply_mutation(
        state, path, str(write.get("op", "set")), write.get("value")
    )
    outcome = state_validator.validate_applied_change(
        path, candidate, scenario_snapshot, original_state=state
    )
    if not outcome.is_valid:
        logger.warning(EVENT_RULE_CHECK_MUTATION_INVALID, error=outcome.error_message)
        return state, None
    return outcome.updated_state or state, path


def _instruction_for(
    definition: dict[str, object], result: str, state: dict[str, object]
) -> str:
    template = definition.get("narrator_instruction_template") or DEFAULT_INSTRUCTION
    filled = (
        str(template)
        .replace("{label}", str(definition.get("label", "")))
        .replace("{result}", result)
    )
    return _fill_state_tokens(filled, state)


def _fill_state_tokens(template: str, state: dict[str, object]) -> str:
    def _value(match: re.Match[str]) -> str:
        value = state_paths.get_field_value(state, match.group(1))
        return "" if value is None else str(value)

    return _STATE_TOKEN.sub(_value, template)
