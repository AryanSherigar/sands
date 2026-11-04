"""Group W: a restless retainer first shows signs, then may leave.

Order inside a retainer's block matters: recovery and the two betrayals are
checked before the nudge and the warning, so a single turn never emits two of
them. A betrayal while Ars's Competence is very low is a coup, which ends the
run.
"""

from scripts.reincarnated_aristocrat import balance
from scripts.reincarnated_aristocrat.characters import CHARACTERS, CharacterSpec
from scripts.reincarnated_aristocrat.conditions.common import (
    attr,
    change,
    is_recruited,
    label,
)
from scripts.seeding.expr import SET, Cond, Expression, Mut, all_of, eq, gte, lt, lte

WARNING_TEXT = (
    "{name} is wavering. Show it in small ways this turn (evasive answers, "
    "private meetings, questions about who will really rule) without saying why. "
    "Do not state any numbers."
)
NUDGE_TEXT = (
    "{name} remains restless and distant. Let it colour any scene they appear in "
    "without spelling it out."
)
RECOVERY_TEXT = "{name} seems steadier again. Show a small sign of renewed loyalty."
COUP_TEXT = (
    "{name} turns on Ars this turn and, with the House already weak, the "
    "household does not hold. Narrate the betrayal as the end of Ars's rule."
)
BETRAYAL_TEXT = (
    "{name} leaves Ars's service this turn, taking some of the House's coin. "
    "Narrate the departure and its sting."
)
RECRUITABLE = [spec for spec in CHARACTERS if spec.is_recruitable]
BETRAYAL_STANDING_LOSS = 2


def _risk(slug: str, value: bool) -> Expression:
    return eq(attr(slug, "betrayal_risk"), value)


def _leave_mutations(spec: CharacterSpec) -> list[Mut]:
    mutations = [
        Mut(attr(spec.slug, "is_recruited"), SET, False),
        Mut(attr(spec.slug, "betrayal_risk"), SET, False),
        Mut(attr(spec.slug, "loyalty"), SET, 0),
        change("time.recruits", -1),
    ]
    if balance.ARMY_VALUE[spec.slug] > 0:
        mutations.append(change("army_strength", -balance.ARMY_VALUE[spec.slug]))
    return mutations


def _restless(spec: CharacterSpec) -> list[Expression]:
    return [
        is_recruited(spec.slug),
        _risk(spec.slug, True),
        lt(attr(spec.slug, "loyalty"), balance.BETRAYAL_LOYALTY),
    ]


def block(index: int, spec: CharacterSpec) -> list[Cond]:
    name, slug = spec.name, spec.slug
    return [
        Cond(
            label("W", index, f"{slug} recovers"),
            all_of(
                is_recruited(slug),
                _risk(slug, True),
                gte(attr(slug, "loyalty"), balance.RECOVERY_LOYALTY),
            ),
            (Mut(attr(slug, "betrayal_risk"), SET, False),),
            instruction=RECOVERY_TEXT.format(name=name),
        ),
        Cond(
            label("W", index + 1, f"{slug} coup"),
            all_of(*_restless(spec), lte("sheet.competence", balance.COUP_COMPETENCE)),
            (*_leave_mutations(spec), Mut("beats.coup", SET, True)),
            instruction=COUP_TEXT.format(name=name),
        ),
        Cond(
            label("W", index + 2, f"{slug} betrays"),
            all_of(*_restless(spec)),
            (
                *_leave_mutations(spec),
                change("funds", -balance.BETRAYAL_FUNDS_LOSS),
                change("standing", -BETRAYAL_STANDING_LOSS),
            ),
            instruction=BETRAYAL_TEXT.format(name=name),
        ),
        Cond(
            label("W", index + 3, f"{slug} restless"),
            all_of(is_recruited(slug), _risk(slug, True)),
            (),
            instruction=NUDGE_TEXT.format(name=name),
        ),
        Cond(
            label("W", index + 4, f"{slug} warning"),
            all_of(
                is_recruited(slug),
                _risk(slug, False),
                gte(attr(slug, "ambition"), balance.WARNING_AMBITION),
                lt(attr(slug, "loyalty"), balance.WARNING_LOYALTY),
            ),
            (Mut(attr(slug, "betrayal_risk"), SET, True),),
            instruction=WARNING_TEXT.format(name=name),
        ),
    ]


def betrayal_conditions() -> list[Cond]:
    conditions: list[Cond] = []
    for spec in RECRUITABLE:
        conditions += block(len(conditions) + 1, spec)
    return conditions
