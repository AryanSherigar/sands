"""Pure logic deciding which of a story's endings a player has found."""

import uuid

from app.models.endings import EndingSlot, ScenarioEndings
from app.repositories.endings_repo import EndedRunRow, SnapshotEndingsRow

LOCKED_SLOT = EndingSlot(is_found=False)


def _parse_id(value: object) -> uuid.UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _found_slot(title: object, tag: object) -> EndingSlot:
    return EndingSlot(
        is_found=True,
        title=str(title),
        outcome_tag=str(tag) if tag is not None else None,
    )


def _sorted_conditions(conditions: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        conditions,
        key=lambda c: (int(c.get("priority") or 0), str(c.get("outcome_title"))),
    )


def _match_condition(
    condition: dict[str, object],
    unmatched_ids: dict[uuid.UUID, EndedRunRow],
    unmatched_titles: dict[str, EndedRunRow],
) -> EndingSlot | None:
    condition_id = _parse_id(condition.get("end_condition_id"))
    by_id = unmatched_ids.pop(condition_id, None) if condition_id else None
    by_title = unmatched_titles.pop(str(condition.get("outcome_title")), None)
    matched = by_id or by_title
    if matched is not None:
        return _found_slot(matched.outcome_title, matched.outcome_tag)
    if condition.get("is_secret"):
        return None
    return LOCKED_SLOT


def build_scenario_endings(
    snapshot: SnapshotEndingsRow, ended_runs: list[EndedRunRow]
) -> ScenarioEndings | None:
    unmatched_ids = {run.outcome_id: run for run in ended_runs if run.outcome_id}
    unmatched_titles = {
        run.outcome_title: run for run in ended_runs if run.outcome_id is None
    }
    slots: list[EndingSlot] = []
    for condition in _sorted_conditions(snapshot.end_conditions):
        slot = _match_condition(condition, unmatched_ids, unmatched_titles)
        if slot is not None:
            slots.append(slot)
    leftovers = [*unmatched_ids.values(), *unmatched_titles.values()]
    slots.extend(_found_slot(run.outcome_title, run.outcome_tag) for run in leftovers)
    if not slots:
        return None
    return ScenarioEndings(
        scenario_id=snapshot.scenario_id,
        scenario_title=snapshot.scenario_title,
        found_count=sum(1 for slot in slots if slot.is_found),
        total_count=len(slots),
        slots=slots,
    )
