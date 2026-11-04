"""End conditions (data doc §10). First match wins by ascending priority."""

from app.models.end_condition import EndConditionCreate
from scripts.night_desk import balance, prose, timeline
from scripts.night_desk.expr import Expression, all_of, eq, gte, leaf

SHIFT = "shift_minutes"


def _dawn() -> Expression:
    return gte(SHIFT, timeline.SHIFT_END)


def _expressions() -> dict[str, Expression]:
    return {
        "counted": leaf("sanity", "<=", 0),
        "mr_orr_is_in": all_of(_dawn(), eq("flags.cabin_entered", True)),
        "visitor": all_of(
            _dawn(), gte("count.unsigned", balance.UNSIGNED_FOR_VISITOR_ENDING)
        ),
        "dont_be_late": _dawn(),
    }


def end_conditions() -> list[EndConditionCreate]:
    endings: list[EndConditionCreate] = []
    for priority, (key, expression) in enumerate(_expressions().items()):
        ending = prose.ENDINGS[key]
        endings.append(
            EndConditionCreate(
                condition_expression=expression,
                outcome_tag=ending.tag,
                outcome_title=ending.title,
                outcome_text=ending.text,
                is_secret=ending.is_secret,
                priority=priority,
            )
        )
    return endings
